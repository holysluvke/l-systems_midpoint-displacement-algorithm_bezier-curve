"""Лабораторная работа №5: L-системы, midpoint displacement, кривые Безье.

Запуск: python main.py
Каждое задание - отдельная вкладка. Реализованы задания 1 и 2,
вкладка 3 - заглушка.
"""

import tkinter as tk
from tkinter import ttk

from midpoint_app import MidpointFrame
from lsystem_app import LSystemFrame
from bezier_app import BezierFrame

def main():
    root = tk.Tk()
    root.title("Лабораторная работа 5 - L-системы, midpoint displacement, Безье")
    root.geometry("1200x760")
    root.minsize(900, 600)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    notebook.add(LSystemFrame(notebook), text="1. L-системы")
    notebook.add(MidpointFrame(notebook), text="2. Midpoint displacement")
    notebook.add(BezierFrame(notebook), text="3. Кривые Безье")

    root.mainloop()


if __name__ == "__main__":
    main()
