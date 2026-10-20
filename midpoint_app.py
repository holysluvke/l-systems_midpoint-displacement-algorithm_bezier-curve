import random
import tkinter as tk
from tkinter import ttk


def build_levels(y_left, y_right, amp, r, n_steps, seed, gauss):
    pts = [(0.0, y_left), (1.0, y_right)]
    levels = [pts]
    for step in range(1, n_steps + 1):
        rng = random.Random(seed * 7919 + step)
        scale = amp * (r ** (step - 1))
        new = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            mx = (a[0] + b[0]) / 2
            my = (a[1] + b[1]) / 2
            if gauss:
                d = rng.gauss(0, scale / 2)
            else:
                d = rng.uniform(-scale, scale)
            new.append((mx, my + d))
            new.append(b)
        pts = new
        levels.append(pts)
    return levels


class MidpointFrame(ttk.Frame):
    PAD = 30

    def __init__(self, master):
        super().__init__(master)

        # параметры
        self.v_n = tk.StringVar(value="7")
        self.v_left = tk.StringVar(value="0.4")
        self.v_right = tk.StringVar(value="0.3")
        self.v_amp = tk.StringVar(value="0.5")
        self.v_r = tk.DoubleVar(value=0.55)
        self.v_seed = tk.StringVar(value="1")
        self.v_gauss = tk.BooleanVar(value=False)
        self.v_all = tk.BooleanVar(value=True)
        self.v_fill = tk.BooleanVar(value=True)
        self.v_points = tk.BooleanVar(value=False)

        self.levels = []
        self.step = 0
        self.n_steps = 7

        self._build_ui()
        self.on_params()

    # ---------------------------------------------------------- интерфейс
    def _build_ui(self):
        panel = ttk.Frame(self, padding=8)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas = tk.Canvas(self, bg="#f4f7fb", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

        def spin(label, var, lo, hi, inc):
            row = ttk.Frame(panel)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=24).pack(side=tk.LEFT)
            sb = ttk.Spinbox(
                row,
                textvariable=var,
                from_=lo,
                to=hi,
                increment=inc,
                width=7,
                command=self.on_params,
            )
            sb.pack(side=tk.RIGHT)
            sb.bind("<Return>", lambda e: self.on_params())
            sb.bind("<FocusOut>", lambda e: self.on_params())

        ttk.Label(
            panel, text="Параметры построения", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 6))
        spin("Число шагов (1..12)", self.v_n, 1, 12, 1)
        spin("Высота слева (0..1)", self.v_left, 0, 1, 0.05)
        spin("Высота справа (0..1)", self.v_right, 0, 1, 0.05)
        spin("Начальная амплитуда", self.v_amp, 0, 2, 0.05)
        spin("Зерно (seed)", self.v_seed, 0, 999999, 1)

        ttk.Label(panel, text="Шероховатость r (затухание)").pack(
            anchor="w", pady=(8, 0)
        )
        ttk.Scale(
            panel,
            from_=0.2,
            to=1.0,
            variable=self.v_r,
            command=lambda v: self.on_params(),
        ).pack(fill=tk.X)
        self.lbl_r = ttk.Label(panel, text="")
        self.lbl_r.pack(anchor="w")

        ttk.Checkbutton(
            panel,
            text="Гауссово распределение смещения",
            variable=self.v_gauss,
            command=self.on_params,
        ).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(
            panel,
            text="Показывать предыдущие шаги",
            variable=self.v_all,
            command=self.redraw,
        ).pack(anchor="w")
        ttk.Checkbutton(
            panel, text="Заливка под ломаной", variable=self.v_fill, command=self.redraw
        ).pack(anchor="w")
        ttk.Checkbutton(
            panel,
            text="Показывать вершины",
            variable=self.v_points,
            command=self.redraw,
        ).pack(anchor="w")

        ttk.Separator(panel).pack(fill=tk.X, pady=10)
        ttk.Label(panel, text="Шаги алгоритма", font=("Segoe UI", 11, "bold")).pack(
            anchor="w"
        )
        self.lbl_step = ttk.Label(panel, text="")
        self.lbl_step.pack(anchor="w", pady=2)

        btns = ttk.Frame(panel)
        btns.pack(fill=tk.X, pady=2)
        ttk.Button(
            btns, text="< Назад", command=lambda: self.set_step(self.step - 1)
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(
            btns, text="Шаг >", command=lambda: self.set_step(self.step + 1)
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(
            panel,
            text="Построить до конца",
            command=lambda: self.set_step(self.n_steps),
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            panel, text="Сбросить (шаг 0)", command=lambda: self.set_step(0)
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            panel, text="Новый ландшафт (другой seed)", command=self.new_seed
        ).pack(fill=tk.X, pady=(10, 2))

        self.lbl_info = ttk.Label(panel, foreground="gray", justify=tk.LEFT)
        self.lbl_info.pack(anchor="w", pady=10)

    # ------------------------------------------------------------- логика
    @staticmethod
    def _num(var, cast, default, lo, hi):
        try:
            val = cast(var.get())
        except (ValueError, tk.TclError):
            return default
        return max(lo, min(hi, val))

    def on_params(self):
        n = self._num(self.v_n, int, 7, 1, 12)
        y0 = self._num(self.v_left, float, 0.4, 0.0, 1.0)
        y1 = self._num(self.v_right, float, 0.3, 0.0, 1.0)
        amp = self._num(self.v_amp, float, 0.5, 0.0, 2.0)
        seed = self._num(self.v_seed, int, 1, 0, 999999)
        r = self.v_r.get()

        self.n_steps = n
        self.levels = build_levels(y0, y1, amp, r, n, seed, self.v_gauss.get())
        self.step = min(self.step, n)
        self.lbl_r.config(text=f"r = {r:.2f}  (меньше - глаже, ближе к 1 - острее)")
        self.redraw()

    def set_step(self, k):
        self.step = max(0, min(self.n_steps, k))
        self.redraw()

    def new_seed(self):
        self.v_seed.set(str(random.randint(0, 999999)))
        self.on_params()

    # ---------------------------------------------------------- рисование
    def redraw(self):
        c = self.canvas
        c.delete("all")
        if not self.levels:
            return
        w, h = c.winfo_width(), c.winfo_height()
        if w < 50 or h < 50:
            return
        pad = self.PAD

        # масштаб подбираем по самой детальной ломаной - вид не прыгает по шагам
        ys = [p[1] for p in self.levels[-1]]
        ymin, ymax = min(ys), max(ys)
        span = (ymax - ymin) or 1.0

        def tr(p):
            x = pad + p[0] * (w - 2 * pad)
            y = h - pad - (p[1] - ymin) / span * (h - 2 * pad)
            return x, y

        base = h - pad / 2
        k = self.step

        # какие уровни рисуем
        if self.v_all.get():
            shown = list(range(0, k + 1))
        else:
            shown = [k]

        # заливка для текущего уровня
        if self.v_fill.get():
            poly = [tr(p) for p in self.levels[k]]
            flat = [v for xy in poly for v in xy]
            flat += [poly[-1][0], base, poly[0][0], base]
            c.create_polygon(*flat, fill="#cfdceb", outline="")

        # предыдущие шаги - от светлых к тёмным
        for i in shown:
            pts = [v for p in self.levels[i] for v in tr(p)]
            if i == k:
                c.create_line(*pts, fill="#1b3a5c", width=2.5, joinstyle=tk.ROUND)
            else:
                t = i / max(1, k)
                g = int(200 - 90 * t)
                c.create_line(
                    *pts, fill=f"#{g:02x}{g:02x}{min(255, g + 20):02x}", width=1
                )

        # вершины текущего шага; новые (середины) - красным
        if self.v_points.get():
            for idx, p in enumerate(self.levels[k]):
                x, y = tr(p)
                new = k > 0 and idx % 2 == 1
                col = "#d62828" if new else "#1b3a5c"
                c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=col, outline="")

        c.create_line(pad, base, w - pad, base, fill="#999")

        self.lbl_step.config(text=f"Шаг {k} из {self.n_steps}")
        self.lbl_info.config(
            text=f"Сегментов: {len(self.levels[k]) - 1}\n"
            f"Вершин: {len(self.levels[k])}"
        )
