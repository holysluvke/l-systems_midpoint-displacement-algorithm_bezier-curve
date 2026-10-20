"""Лабораторная работа №5: L-системы, midpoint displacement, кривые Безье.

Запуск: python main.py
Каждое задание - отдельная вкладка. Реализованы задания 1 и 2,
вкладка 3 - заглушка.
"""

import tkinter as tk
from tkinter import ttk

from midpoint_app import MidpointFrame

from lsystem_app import LSystemFrame


def stub(parent: ttk.Notebook, text: str) -> ttk.Frame:
    """Заглушка для ещё не реализованного задания."""
    frame = ttk.Frame(parent)
    ttk.Label(frame, text=text, foreground="gray", font=("Segoe UI", 12)).pack(
        expand=True
    )
    return frame


def main():
    root = tk.Tk()
    root.title("Лабораторная работа 5 - L-системы, midpoint displacement, Безье")
    root.geometry("1200x760")
    root.minsize(900, 600)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    notebook.add(LSystemFrame(notebook), text="1. L-системы")
    notebook.add(MidpointFrame(notebook), text="2. Midpoint displacement")
    notebook.add(
        stub(
            notebook,
            "Задание 3: составные кубические кривые Безье - ещё не реализовано",
        ),
        text="3. Кривые Безье",
    )

    root.mainloop()


if __name__ == "__main__":
    main()
