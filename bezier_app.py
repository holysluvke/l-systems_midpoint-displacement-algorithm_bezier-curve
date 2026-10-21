import math
import tkinter as tk
from tkinter import ttk

HIT_RADIUS = 5

def bezier_point(p0, p1, p2, p3, t):
    x = (1 - t)**3*p0[0] + 3*(1 - t)*(1 - t)*t*p1[0] + 3*(1 - t)*t**2*p2[0] + t**3*p3[0]
    y = (1 - t)**3*p0[1] + 3*(1 - t)*(1 - t)*t*p1[1] + 3*(1 - t)*t**2*p2[1] + t**3*p3[1]
    return (x, y)


def sample_curve(pts, samples=40):
    if len(pts) < 4:
        return []
    out = [pts[0]]
    for i in range(0, len(pts) - 3, 3):
        p0, p1, p2, p3 = pts[i:i + 4]
        for s in range(1, samples + 1):
            out.append(bezier_point(p0, p1, p2, p3, s / samples))
    return out

class BezierModel:
    def __init__(self):
        self.pts = []

    def add_segment(self, x, y):
        p = self.pts
        new = (float(x), float(y))
        if not p:
            p.append(new)
        elif len(p) == 1:
            a = p[0]
            dx, dy = new[0] - a[0], new[1] - a[1]
            p += [(a[0] + dx / 3, a[1] + dy / 3),
                  (a[0] + 2 * dx / 3, a[1] + 2 * dy / 3), new]
        else:
            last, prev = p[-1], p[-2]
            n1 = (2 * last[0] - prev[0], 2 * last[1] - prev[1])
            n2 = ((2 * new[0] + n1[0]) / 3, (2 * new[1] + n1[1]) / 3)
            p += [n1, n2, new]
        return len(p) - 1

    def move(self, j, x, y):
        p = self.pts
        if j % 3 == 0:
            dx, dy = x - p[j][0], y - p[j][1]
            for k in (j - 1, j, j + 1):
                if 0 <= k < len(p):
                    p[k] = (p[k][0] + dx, p[k][1] + dy)
        else:
            p[j] = (x, y)
            shared, opp = (j - 1, j - 2) if j % 3 == 1 else (j + 1, j + 2)
            if 0 <= opp < len(p):
                sx, sy = p[shared]
                vx, vy = x - sx, y - sy
                d = math.hypot(vx, vy)
                if d > 1e-9:
                    L = math.hypot(p[opp][0] - sx, p[opp][1] - sy)
                    p[opp] = (sx - vx / d * L, sy - vy / d * L)

    def delete(self, j):
        p = self.pts
        if j % 3 != 0:
            return
        if len(p) <= 4:
            self.pts = [q for k, q in enumerate(p) if k in (0, 3) and k != j]
        elif j == 0:
            del p[0:3]
        elif j == len(p) - 1:
            del p[-3:]
        else:
            del p[j - 1:j + 2]

    def hit(self, x, y):
        for i, (px, py) in enumerate(self.pts):
            if (px - x) ** 2 + (py - y) ** 2 <= HIT_RADIUS ** 2:
                return i
        return None


class BezierFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.model = BezierModel()
        self.drag = None

        top = ttk.Frame(self, padding=4)
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(top, text="Очистить", command=self.clear).pack(side=tk.LEFT)
        ttk.Label(top, foreground="gray",
                  text="ЛКМ по пустому месту - новый сегмент | ЛКМ по точке и тянуть - "
                       "переместить | ПКМ по квадрату - удалить").pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.canvas.bind("<ButtonPress-3>", self.on_delete)
        self.canvas.bind("<ButtonPress-2>", self.on_delete)

    def clear(self):
        self.model = BezierModel()
        self.drag = None
        self.redraw()

    def on_press(self, e):
        idx = self.model.hit(e.x, e.y)
        if idx is None:
            idx = self.model.add_segment(e.x, e.y)
        self.drag = idx
        self.redraw()

    def on_motion(self, e):
        if self.drag is not None:
            self.model.move(self.drag, e.x, e.y)
            self.redraw()

    def on_delete(self, e):
        idx = self.model.hit(e.x, e.y)
        if idx is not None:
            self.model.delete(idx)
            self.drag = None
            self.redraw()

    def redraw(self):
        c = self.canvas
        c.delete("all")
        pts = self.model.pts
        if len(pts) >= 2:
            c.create_line(*[v for p in pts for v in p], fill="lightgray", dash=(4, 3))
        line = sample_curve(pts)
        if line:
            c.create_line(*[v for p in line for v in p], fill="navy", width=2.5)
        for i, (x, y) in enumerate(pts):
            if i % 3 == 0:
                c.create_rectangle(x - 6, y - 6, x + 6, y + 6, fill="royalblue", outline="white")
            else:
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="pink", outline="white")
            c.create_text(x + 12, y - 11, text=f"V{i}", fill="gray30")