"""Задание 1 (1.а и 1.б): окно для построения фрактальных узоров L-системами.

Вся математика живёт в lsystem.py, здесь только tkinter: панель параметров
слева, холст справа.  Узор пересчитывается кнопкой «Построить», а при
изменении размера окна только заново масштабируется под холст.
"""

from __future__ import annotations

import os
import random
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from lsystem import (LSystem, LSystemError, TurtleParams, fit_segments,
                     interpret, merge_polylines, suggested_iterations)

FRACTALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fractals")
TREE_FILE = "14_tree.txt"

COLOR_BG = "white"
COLOR_LINE = "#1f4e8c"
COLOR_TRUNK = (101, 67, 33)     # коричневый
COLOR_LEAF = (46, 139, 46)      # зелёный
CANVAS_MARGIN = 25


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class LSystemFrame(ttk.Frame):
    """Вкладка задания 1. Встраивается в Notebook или прямо в окно."""

    def __init__(self, master):
        super().__init__(master)
        self.segments = []          # отрезки в мировых координатах
        self.max_depth = 0
        self.current_seed = None
        self._redraw_job = None

        # --- переменные панели 
        self.var_file = tk.StringVar()
        self.var_iters = tk.IntVar(value=4)
        self.var_random = tk.BooleanVar(value=False)
        self.var_angle_jit = tk.DoubleVar(value=15.0)     # проценты
        self.var_len_jit = tk.DoubleVar(value=10.0)       # проценты
        self.var_seed = tk.StringVar(value="")
        self.var_tree = tk.BooleanVar(value=False)
        self.var_trunk_w = tk.DoubleVar(value=14.0)
        self.var_width_ratio = tk.DoubleVar(value=0.65)
        self.var_len_ratio = tk.DoubleVar(value=0.85)
        self.var_tree_color = tk.BooleanVar(value=True)
        self.var_status = tk.StringVar(value="Выберите фрактал и нажмите «Построить».")

        self._build_ui()
        self._load_file_list()
        self.after(150, self.build)

  
    # Интерфейс


    def _build_ui(self):
        panel = ttk.Frame(self, padding=8)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        # Файл описания
        box = ttk.LabelFrame(panel, text="L-система", padding=6)
        box.pack(fill=tk.X, pady=(0, 6))
        self.combo = ttk.Combobox(box, textvariable=self.var_file, state="readonly", width=30)
        self.combo.pack(fill=tk.X)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._on_file_selected())
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(row, text="Открыть файл…", command=self._open_file).pack(side=tk.LEFT)
        ttk.Button(row, text="Сохранить…", command=self._save_file).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(box, text="Описание (можно править прямо здесь):").pack(anchor=tk.W, pady=(6, 0))
        self.text = tk.Text(box, width=36, height=7, font=("Consolas", 10), wrap=tk.NONE)
        self.text.pack(fill=tk.X)

        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(row, text="Итераций:").pack(side=tk.LEFT)
        ttk.Spinbox(row, from_=0, to=20, textvariable=self.var_iters, width=5).pack(side=tk.LEFT, padx=4)

        # Случайность
        box = ttk.LabelFrame(panel, text="Случайность", padding=6)
        box.pack(fill=tk.X, pady=(0, 6))
        ttk.Checkbutton(box, text="Включить случайные отклонения",
                        variable=self.var_random).pack(anchor=tk.W)
        self._scale_row(box, "Разброс угла, %", self.var_angle_jit, 0, 60, "{:.0f}")
        self._scale_row(box, "Разброс длины, %", self.var_len_jit, 0, 60, "{:.0f}")
        row = ttk.Frame(box)
        row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(row, text="Seed (пусто = случайный):").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.var_seed, width=10).pack(side=tk.LEFT, padx=4)
        ttk.Label(box, text="Стохастические правила (несколько строк для одного\n"
                            "символа) тоже используют этот seed.",
                  foreground="gray").pack(anchor=tk.W, pady=(4, 0))

        # Дерево (1.б)
        box = ttk.LabelFrame(panel, text="Дерево (задание 1.б)", padding=6)
        box.pack(fill=tk.X, pady=(0, 6))
        ttk.Checkbutton(box, text="Режим дерева: толщина и цвет по уровню ветвей",
                        variable=self.var_tree, command=self._schedule_redraw).pack(anchor=tk.W)
        self._scale_row(box, "Толщина ствола, px", self.var_trunk_w, 1, 40, "{:.0f}",
                        command=self._schedule_redraw)
        self._scale_row(box, "Утончение за уровень", self.var_width_ratio, 0.3, 0.95, "{:.2f}",
                        command=self._schedule_redraw)
        self._scale_row(box, "Укорочение за уровень", self.var_len_ratio, 0.5, 1.0, "{:.2f}")
        ttk.Checkbutton(box, text="Цвет: коричневый → зелёный",
                        variable=self.var_tree_color, command=self._schedule_redraw).pack(anchor=tk.W)
        ttk.Button(box, text="Пример дерева 1.б", command=self._tree_preset).pack(anchor=tk.W, pady=(4, 0))

        # Кнопки
        row = ttk.Frame(panel)
        row.pack(fill=tk.X, pady=(4, 6))
        ttk.Button(row, text="Построить", command=self.build).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Новый seed", command=self._reseed_and_build).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(panel, textvariable=self.var_status, wraplength=270,
                  foreground="#333").pack(anchor=tk.W)

        # Холст
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self._schedule_redraw())

    def _scale_row(self, parent, label, var, lo, hi, fmt, command=None):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=(2, 0))
        ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
        value = ttk.Label(row, width=5, anchor=tk.E)
        value.pack(side=tk.RIGHT)

        def on_change(*_):
            value.config(text=fmt.format(var.get()))
            if command:
                command()

        # trace, а не command у Scale: тогда подпись обновляется и при
        # программной установке значения (например, кнопкой пресета).
        var.trace_add("write", on_change)
        ttk.Scale(row, from_=lo, to=hi, variable=var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        value.config(text=fmt.format(var.get()))

  
    # Работа с файлами
  

    def _load_file_list(self):
        names = []
        if os.path.isdir(FRACTALS_DIR):
            names = sorted(n for n in os.listdir(FRACTALS_DIR) if n.lower().endswith(".txt"))
        self.combo["values"] = names
        if names:
            self.var_file.set(names[0])
            self._on_file_selected()

    def _on_file_selected(self):
        name = self.var_file.get()
        if name:
            self._load_text(os.path.join(FRACTALS_DIR, name))

    def _load_text(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")
            return
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)
        self.var_iters.set(suggested_iterations(text))

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Файл описания L-системы", initialdir=FRACTALS_DIR,
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")])
        if path:
            self.var_file.set(os.path.basename(path))
            self._load_text(path)
            self.build()

    def _save_file(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить описание", initialdir=FRACTALS_DIR, defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", tk.END).rstrip() + "\n")
            self._load_file_list()
            self.var_file.set(os.path.basename(path))

   
    # Построение
    
    def _tree_preset(self):
        """Готовый набор параметров для пункта 1.б."""
        if TREE_FILE in self.combo["values"]:
            self.var_file.set(TREE_FILE)
            self._on_file_selected()
        self.var_random.set(True)
        self.var_angle_jit.set(25.0)
        self.var_len_jit.set(15.0)
        self.var_tree.set(True)
        self.var_tree_color.set(True)
        self.var_trunk_w.set(14.0)
        self.var_width_ratio.set(0.65)
        self.var_len_ratio.set(0.9)
        self.build()

    def _reseed_and_build(self):
        self.var_seed.set(str(random.randrange(1_000_000)))
        self.build()

    def _turtle_params(self) -> TurtleParams:
        p = TurtleParams()
        if self.var_random.get():
            p.angle_jitter = self.var_angle_jit.get() / 100.0
            p.length_jitter = self.var_len_jit.get() / 100.0
        if self.var_tree.get():
            p.length_factor = self.var_len_ratio.get()
        return p

    def build(self):
        try:
            system = LSystem.from_text(self.text.get("1.0", tk.END))
        except LSystemError as e:
            messagebox.showerror("Ошибка в описании", str(e))
            return

        seed_text = self.var_seed.get().strip()
        seed = int(seed_text) if seed_text.lstrip("-").isdigit() else (
            seed_text if seed_text else random.randrange(1_000_000))
        rng = random.Random(seed)
        self.current_seed = seed

        try:
            iterations = int(self.var_iters.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Ошибка", "Число итераций должно быть целым.")
            return

        t0 = time.perf_counter()
        try:
            string = system.generate(iterations, rng)
        except LSystemError as e:
            messagebox.showerror("Слишком много", str(e))
            return
        segments = interpret(system, string, self._turtle_params(), rng)
        dt = time.perf_counter() - t0

        if not segments:
            self.segments = []
            self.canvas.delete("all")
            self.var_status.set("Ничего не нарисовано: в строке нет рисующих символов "
                                f"({system.draw_symbols}). Строка: {len(string)} символов.")
            return

        self.segments = segments
        self.max_depth = max(s[4] for s in segments)
        self.var_status.set(
            f"Символов в строке: {len(string):,}\nОтрезков: {len(segments):,}\n"
            f"Глубина ветвления: {self.max_depth}\nРасчёт: {dt * 1000:.0f} мс\n"
            f"Seed: {seed}" + ("  (стохастические правила)" if system.is_stochastic else ""))
        self.redraw()

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------

    def _schedule_redraw(self):
        """Перерисовка с задержкой: при растягивании окна Configure сыплется пачками."""
        if self._redraw_job is not None:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(40, self.redraw)

    def redraw(self):
        self._redraw_job = None
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 10 or h < 10 or not self.segments:
            return

        fitted = fit_segments(self.segments, w, h, CANVAS_MARGIN)
        polylines = merge_polylines(fitted)

        if not self.var_tree.get():
            for _, coords in polylines:
                c.create_line(*coords, fill=COLOR_LINE, width=1)
            return

        trunk = self.var_trunk_w.get()
        ratio = self.var_width_ratio.get()
        use_color = self.var_tree_color.get()
        max_depth = max(self.max_depth, 1)
        # Толстые уровни рисуем первыми, чтобы тонкие ветки ложились сверху.
        for depth, coords in sorted(polylines, key=lambda p: p[0]):
            width = max(1.0, trunk * ratio ** depth)
            color = lerp_color(COLOR_TRUNK, COLOR_LEAF, depth / max_depth) if use_color else COLOR_TRUNK
            c.create_line(*coords, fill=color, width=width,
                          capstyle=tk.ROUND, joinstyle=tk.ROUND)
