"""Задание 1.а / 1.б: ядро L-систем.

Здесь нет ничего про tkinter: только чтение описания из файла, порождение
строки, интерпретация её "черепашкой" в набор отрезков и масштабирование
этого набора под размер окна.

Формат файла описания:

    <атом> <угол поворота> <начальное направление>
    <правило №1>
    <правило №2>
    ...

Правило записывается как  X -> F+[[X]-X]-F[-FX]+X  (допустимы также
разделители "=" и просто пробел).  Если для одного символа задано
несколько правил, при каждой подстановке выбирается случайное из них -
так задаётся стохастическая L-система.  Строки, начинающиеся с "#",
считаются комментариями.  Необязательная строка "draw: FGA" задаёт,
какие символы рисуют отрезок (по умолчанию F и G).

Команды черепашки:
    F, G  - шаг вперёд с рисованием            f - шаг вперёд без рисования
    +     - поворот влево на угол              - - поворот вправо на угол
    |     - разворот на 180 градусов
    [     - запомнить состояние (ветвление)    ] - вернуться к запомненному
    остальные символы игнорируются (служат только для порождения строки).

Направление: 0 - вправо, 90 - вверх (ось Y направлена вверх,
переворот под экранные координаты делается в fit_segments).
"""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass

DRAW_DEFAULT = "FG"
MOVE_SYMBOL = "f"
MAX_STRING_LENGTH = 3_000_000


class LSystemError(ValueError):
    """Ошибка в описании L-системы или слишком большой результат."""



# Описание системы 


@dataclass
class LSystem:
    axiom: str
    angle: float                    # угол поворота, градусы
    direction: float                # начальное направление, градусы
    rules: dict[str, list[str]]     # символ -> варианты правой части
    draw_symbols: str = DRAW_DEFAULT
    name: str = ""

    #  разбор 

    @classmethod
    def from_file(cls, path: str) -> "LSystem":
        with open(path, encoding="utf-8") as f:
            text = f.read()
        return cls.from_text(text, name=path)

    @classmethod
    def from_text(cls, text: str, name: str = "") -> "LSystem":
        lines: list[str] = []
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if line:
                lines.append(line)
        if not lines:
            raise LSystemError("Описание пустое.")

        head = lines[0].split()
        if len(head) < 3:
            raise LSystemError(
                "Первая строка должна иметь вид:\n<атом> <угол поворота> <начальное направление>")
        axiom = head[0]
        try:
            angle = float(head[1].replace(",", "."))
            direction = float(head[2].replace(",", "."))
        except ValueError:
            raise LSystemError(f"Угол и направление должны быть числами: {lines[0]!r}") from None

        rules: dict[str, list[str]] = {}
        draw = DRAW_DEFAULT
        for line in lines[1:]:
            if line.lower().startswith("draw:"):
                draw = line.split(":", 1)[1].replace(" ", "")
                continue
            left, right = _parse_rule(line)
            rules.setdefault(left, []).append(right)

        return cls(axiom, angle, direction, rules, draw, name)

    @property
    def is_stochastic(self) -> bool:
        return any(len(v) > 1 for v in self.rules.values())

    #  порождение 

    def generate(self, iterations: int, rng: random.Random | None = None,
                 max_len: int = MAX_STRING_LENGTH) -> str:
        """Применяет правила `iterations` раз к аксиоме и возвращает строку."""
        if iterations < 0:
            raise LSystemError("Число итераций не может быть отрицательным.")
        rng = rng or random

        s = self.axiom
        if not self.is_stochastic:
            # Детерминированный случай: str.translate делает всю подстановку в C.
            table = {ord(k): v[0] for k, v in self.rules.items()}
            for _ in range(iterations):
                s = s.translate(table)
                _check_len(s, max_len)
            return s

        for _ in range(iterations):
            parts = []
            for ch in s:
                options = self.rules.get(ch)
                if options is None:
                    parts.append(ch)
                elif len(options) == 1:
                    parts.append(options[0])
                else:
                    parts.append(rng.choice(options))
            s = "".join(parts)
            _check_len(s, max_len)
        return s


def _parse_rule(line: str) -> tuple[str, str]:
    for sep in ("->", "=>", "="):
        if sep in line:
            left, right = line.split(sep, 1)
            break
    else:
        parts = line.split(None, 1)
        left, right = parts[0], (parts[1] if len(parts) > 1 else "")
    left = left.strip()
    right = "".join(right.split())      # пробелы внутри правой части не нужны
    if len(left) != 1:
        raise LSystemError(f"Левая часть правила должна быть одним символом: {line!r}")
    return left, right


def _check_len(s: str, max_len: int) -> None:
    if len(s) > max_len:
        raise LSystemError(
            f"Строка стала слишком длинной ({len(s):,} символов, предел {max_len:,}).\n"
            "Уменьшите число итераций.")


def suggested_iterations(text: str, default: int = 4) -> int:
    """Достаёт подсказку вида ``# ... iterations: 5`` из комментариев файла."""
    m = re.search(r"итерац\w*\s*[:=]\s*(\d+)|iterations?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if not m:
        return default
    return int(m.group(1) or m.group(2))



# Интерпретация черепашкой

# Отрезок: (x1, y1, x2, y2, depth), depth - глубина вложенности скобок.
Segment = tuple[float, float, float, float, int]


@dataclass
class TurtleParams:
    """Параметры случайности и формы при интерпретации строки."""
    angle_jitter: float = 0.0     # относительный разброс угла поворота (0.2 = +-20 %)
    length_jitter: float = 0.0    # относительный разброс длины шага
    length_factor: float = 1.0    # множитель длины шага за каждый уровень вложенности


def interpret(system: LSystem, string: str, params: TurtleParams | None = None,
              rng: random.Random | None = None) -> list[Segment]:
    """Проходит строку черепашкой и возвращает список отрезков."""
    params = params or TurtleParams()
    rng = rng or random

    draw = set(system.draw_symbols)
    base_angle = math.radians(system.angle)
    aj, lj, lf = params.angle_jitter, params.length_jitter, params.length_factor

    x = y = 0.0
    heading = math.radians(system.direction)
    depth = 0
    stack: list[tuple[float, float, float]] = []
    segments: list[Segment] = []
    cos, sin = math.cos, math.sin

    for ch in string:
        if ch in draw or ch == MOVE_SYMBOL:
            step = lf ** depth if lf != 1.0 else 1.0
            if lj:
                step *= 1.0 + rng.uniform(-lj, lj)
            nx = x + step * cos(heading)
            ny = y + step * sin(heading)
            if ch in draw:
                segments.append((x, y, nx, ny, depth))
            x, y = nx, ny
        elif ch == "+":
            heading += base_angle * (1.0 + rng.uniform(-aj, aj)) if aj else base_angle
        elif ch == "-":
            heading -= base_angle * (1.0 + rng.uniform(-aj, aj)) if aj else base_angle
        elif ch == "|":
            heading += math.pi
        elif ch == "[":
            stack.append((x, y, heading))
            depth += 1
        elif ch == "]":
            if stack:
                x, y, heading = stack.pop()
                depth -= 1
        # остальные символы - только для порождения, черепашка их пропускает
    return segments



# Масштабирование под окно


def bounding_box(segments: list[Segment]) -> tuple[float, float, float, float]:
    min_x = min(min(s[0], s[2]) for s in segments)
    max_x = max(max(s[0], s[2]) for s in segments)
    min_y = min(min(s[1], s[3]) for s in segments)
    max_y = max(max(s[1], s[3]) for s in segments)
    return min_x, min_y, max_x, max_y


def fit_segments(segments: list[Segment], width: float, height: float,
                 margin: float = 20.0) -> list[Segment]:
    """Переводит отрезки в экранные координаты так, чтобы узор целиком
    поместился в прямоугольник width x height с отступом margin.
    Пропорции сохраняются, ось Y переворачивается """
    if not segments:
        return []
    min_x, min_y, max_x, max_y = bounding_box(segments)
    bw = max(max_x - min_x, 1e-9)
    bh = max(max_y - min_y, 1e-9)
    scale = min((width - 2 * margin) / bw, (height - 2 * margin) / bh)
    if scale <= 0:
        scale = 1e-9
    off_x = (width - bw * scale) / 2 - min_x * scale
    off_y = (height - bh * scale) / 2 - min_y * scale
    return [
        (x1 * scale + off_x, height - (y1 * scale + off_y),
         x2 * scale + off_x, height - (y2 * scale + off_y), d)
        for x1, y1, x2, y2, d in segments
    ]


def merge_polylines(segments: list[Segment]) -> list[tuple[int, list[float]]]:
    """Склеивает подряд идущие отрезки одной глубины, у которых конец
    предыдущего совпадает с началом следующего, в ломаные.
    Нужно только для скорости отрисовки: одна create_line вместо тысяч."""
    result: list[tuple[int, list[float]]] = []
    cur_depth = None
    cur: list[float] = []
    for x1, y1, x2, y2, d in segments:
        if cur and d == cur_depth and cur[-2] == x1 and cur[-1] == y1:
            cur.append(x2)
            cur.append(y2)
        else:
            cur = [x1, y1, x2, y2]
            cur_depth = d
            result.append((d, cur))
    return result
