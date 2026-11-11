"""
Ordematrix  -  Magic Square Simulation and Algorithm Analysis
Data Structures and Algorithms | Fall 2026 | Assignments 1 & 2          Run:  python main.py

EVERYTHING IS IN THIS ONE FILE.  Use Ctrl+F for "SECTION" to jump around:

    SECTION 1  Theme & helpers         two colour themes (black & gold / light violet), fonts, sharp-text (HiDPI) fix
    SECTION 2  Constructive algorithms odd (Siamese), doubly even (complement), singly even (Strachey),
                                       pseudocode text, simulation steps, verification
    SECTION 3  Brute-force searches    naive permutations and backtracking with pruning (thread friendly)
    SECTION 4  Reports                 CSV / TXT / PDF writers (the PDF is written by hand - no extra packages)
    SECTION 5  Dialogs & windows       pop-up messages, export dialog, details, time comparison, benchmark
    SECTION 6  Main window             controls, grid drawing, simulation, verification, compare, export
    SECTION 7  Program entry point

Only the Python standard library is used (Tkinter ships with Python).  Tests: python test_algorithms.py
"""
from __future__ import annotations

import csv
import itertools
import math
import os
import queue
import sys
import textwrap
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass, field
from datetime import datetime
from tkinter import filedialog, ttk
from typing import Iterator, List, Optional, Tuple

if sys.version_info < (3, 10):
    sys.exit("This program needs Python 3.10 or newer.")


# ==========================================================================
#  SECTION 1 - THEME & HELPERS
# ==========================================================================

APP_NAME = "Ordematrix"
APP_TAGLINE = "Magic square simulator  ·  watch an algorithm build it, then see brute force struggle"


def enable_sharp_text():
    """Stop Windows from bitmap-stretching the window (this is what made everything look blurry)."""
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)      # system DPI aware
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


_SCALE = [1.0]           # screen scale factor (1.0 = 96 dpi); filled in once the window exists
FONT = ["Segoe UI"]      # UI font family  (replaced by an installed one if Segoe UI is missing)
MONO = ["Consolas"]      # monospace family


def px(v) -> int:
    """Scale a pixel size so spacing looks the same on normal and high-resolution screens."""
    return int(round(v * _SCALE[0]))


def font(size, weight="normal"):
    return (FONT[0], size, weight)


def mono(size, weight="normal"):
    return (MONO[0], size, weight)


# Every colour used anywhere is a token below.  Switching theme = swapping this dictionary.
THEMES = {
    "dark": dict(      # black & gold
        BG="#0C0C0E", CARD="#151518", PANEL="#202024", EDGE="#4B3E1B", HOT="#2E2B1F",
        INK="#F4EFE1", MUTE="#A8A08A", ACC="#E2B64D", ACC2="#F3D07E", ONACC="#14110A", TITLE="#E8BE55",
        HI="#F3D07E", HIOUT="#FFFFFF", MARK="#FFF4D6", GREEN="#72D393", RED="#F27A70", WARN="#F2B84B",
        EMPTY="#1C1C20", WHITE="#FFFFFF", RLO=(46, 40, 24), RHI=(232, 190, 92)),
    "light": dict(     # white & violet
        BG="#F2EFFB", CARD="#FFFFFF", PANEL="#EEE9FB", EDGE="#DAD3F1", HOT="#E3DBF8",
        INK="#27244A", MUTE="#6A658D", ACC="#7B3FF2", ACC2="#9461FF", ONACC="#FFFFFF", TITLE="#3F7AE0",
        HI="#FFC94A", HIOUT="#3B1C9E", MARK="#FFE7A0", GREEN="#118B4E", RED="#D23A3A", WARN="#D9820B",
        EMPTY="#F0ECFB", WHITE="#FFFFFF", RLO=(205, 222, 255), RHI=(110, 56, 230)),
}
THEMES["sage"] = dict(   # sage green - matches the CUOnline portal look (pale sage background, deep green accent)
    BG="#E6EBDA", CARD="#FAFBF5", PANEL="#EDF1E3", EDGE="#CBD4BC", HOT="#DCE5CF",
    INK="#1F2B22", MUTE="#66705F", ACC="#4A6D4E", ACC2="#5E8563", ONACC="#FFFFFF", TITLE="#4A7550",
    HI="#F2CF70", HIOUT="#2F4A33", MARK="#F8E6A8", GREEN="#2E7D4F", RED="#B94A3E", WARN="#B7791F",
    EMPTY="#EDF1E3", WHITE="#FFFFFF", RLO=(224, 234, 212), RHI=(58, 96, 64))
THEME_ORDER = ("dark", "light", "sage")                      # the Theme button cycles through these
THEME_LABELS = {"dark": "Black & Gold", "light": "Light Violet", "sage": "Sage Calm"}
PAL: dict = {}
DARK_TXT, LIGHT_TXT = "#14110A", "#FAF6EC"


def set_palette(name: str):
    PAL.clear()
    PAL.update(THEMES[name])
    PAL["name"] = name


def ramp_color(v, total):
    """Cell colour for value v of 1..total plus a readable text colour."""
    t = (v - 1) / (total - 1) if total > 1 else 0.0
    lo, hi = PAL["RLO"], PAL["RHI"]
    r, g, b = (int(lo[i] + (hi[i] - lo[i]) * t) for i in range(3))
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "#%02x%02x%02x" % (r, g, b), (DARK_TXT if lum > 150 else LIGHT_TXT)


def fmt_time(seconds):
    """Human readable duration (µs / ms / s)."""
    if seconds < 1e-3:
        return f"{seconds * 1e6:.1f} µs"
    if seconds < 1:
        return f"{seconds * 1e3:.3f} ms"
    return f"{seconds:.3f} s"


# (background, text, hover background, hover text, border) for every button style
KINDS = {
    "primary":  ("ACC", "ONACC", "ACC2", "ONACC", "ACC"),
    "plain":    ("PANEL", "INK", "HOT", "INK", "EDGE"),
    "danger":   ("PANEL", "RED", "HOT", "RED", "EDGE"),
    "win":      ("CARD", "MUTE", "PANEL", "INK", "CARD"),
    "winclose": ("CARD", "MUTE", "RED", "WHITE", "CARD"),
}


# ==========================================================================
#  SECTION 2 - CONSTRUCTIVE ALGORITHMS, SIMULATION STEPS AND VERIFICATION
#  No GUI code here.  Odd: Siamese | Doubly even: complement | Singly even: Strachey.  All O(n^2).
# ==========================================================================

Grid = List[List[int]]
Cell = Tuple[int, int]


def magic_constant(n: int) -> int:
    """M(n) = n (n^2 + 1) / 2  - the common sum of every row, column and diagonal."""
    return n * (n * n + 1) // 2


def classify(n: int) -> str:
    """Return 'odd', 'doubly_even' (n mod 4 = 0) or 'singly_even' (n mod 4 = 2)."""
    if n % 2 == 1:
        return "odd"
    return "doubly_even" if n % 4 == 0 else "singly_even"


CASE_TITLES = {
    "odd": "Odd order",
    "doubly_even": "Doubly even order (n = 4k)",
    "singly_even": "Singly even order (n = 4k + 2)",
}
CASE_METHODS = {
    "odd": "Siamese (de la Loubère) method",
    "doubly_even": "Diagonal / complement method",
    "singly_even": "Strachey's method",
}

# Pseudocode shown in the GUI.  The 'line' field of every Step points into these lists
# so the GUI can highlight the instruction that is currently being executed.
PSEUDOCODE = {
    "odd": [
        "row ← 0 ;  col ← n // 2                      # top row, middle column",
        "for k = 1 … n²:",
        "    grid[row][col] ← k",
        "    next ← ((row − 1) mod n, (col + 1) mod n)  # up and right, wrapping",
        "    if grid[next] is already filled:",
        "        next ← (row + 1, col)                 # step down instead",
        "    (row, col) ← next",
    ],
    "doubly_even": [
        "# Phase 1 – fill the numbers in reading order",
        "for i, j in row-major order:  grid[i][j] ← i·n + j + 1",
        "# Phase 2 – complement the diagonal cells of every 4×4 block",
        "for every cell (i, j):",
        "    if (i mod 4 = j mod 4) or (i mod 4 + j mod 4 = 3):",
        "        grid[i][j] ← n² + 1 − grid[i][j]",
    ],
    "singly_even": [
        "m ← n / 2 ;  k ← (m − 1) / 2",
        "A ← odd magic square of order m   (Siamese method)",
        "top-left  ← A",
        "bottom-right ← A + m² ;  top-right ← A + 2m² ;  bottom-left ← A + 3m²",
        "swap the first k columns of top-left with bottom-left",
        "    (in the middle row start one column to the right)",
        "swap the last k − 1 columns of top-right with bottom-right",
    ],
    "naive": [
        "for each permutation P of 1 … n²:",
        "    nodes ← nodes + 1",
        "    if the first row of P does not add up to M(n): continue",
        "    fill the grid row by row with P",
        "    if every row, column and both diagonals equal M(n): return grid",
        "stop when found, when the time limit is reached, or on Stop",
    ],
    "backtracking": [
        "place(pos):                       # pos = 0 … n²−1, row by row",
        "    if pos = n²: return success",
        "    for each unused number v (ascending):",
        "        reject v if a row, column or diagonal would exceed M(n)",
        "        reject v if a completed row, column or diagonal ≠ M(n)",
        "        reject v if the free numbers cannot complete the row/column to M(n)",
        "        write v ; if place(pos + 1): return success ; erase v (backtrack)",
    ],
}


# ----------------------------------------------------------------------------
# Pure constructions (used for timing: no GUI bookkeeping inside)
# ----------------------------------------------------------------------------
def _siamese(n: int) -> Grid:
    """Odd order: start at the top-middle, move up-right, drop down when blocked."""
    g = [[0] * n for _ in range(n)]
    r, c = 0, n // 2
    for k in range(1, n * n + 1):
        g[r][c] = k
        nr, nc = (r - 1) % n, (c + 1) % n
        if g[nr][nc]:
            nr, nc = (r + 1) % n, c
        r, c = nr, nc
    return g


def _is_marked(i: int, j: int) -> bool:
    """Cells on the diagonals of the 4x4 blocks (they get complemented)."""
    a, b = i % 4, j % 4
    return a == b or a + b == 3


def _doubly_even(n: int) -> Grid:
    total = n * n
    g = [[i * n + j + 1 for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(n):
            if _is_marked(i, j):
                g[i][j] = total + 1 - g[i][j]
    return g


def _strachey_swaps(n: int) -> Iterator[Cell]:
    """Cells (i, j) of the top half whose value is swapped with the cell m rows below."""
    m = n // 2
    k = (m - 1) // 2
    for i in range(m):
        for j in range(n):
            swap = j < k
            if i == m // 2:          # middle row: shifted one column to the right
                swap = 1 <= j <= k
            if j > n - k:            # last k-1 columns
                swap = True
            if swap:
                yield i, j


def _singly_even(n: int) -> Grid:
    m = n // 2
    q = m * m
    a = _siamese(m)
    g = [[0] * n for _ in range(n)]
    for i in range(m):
        for j in range(m):
            g[i][j] = a[i][j]                 # top-left
            g[i + m][j + m] = a[i][j] + q     # bottom-right
            g[i][j + m] = a[i][j] + 2 * q     # top-right
            g[i + m][j] = a[i][j] + 3 * q     # bottom-left
    for i, j in _strachey_swaps(n):
        g[i][j], g[i + m][j] = g[i + m][j], g[i][j]
    return g


def construct(n: int) -> Grid:
    """Build a magic square of order n with the appropriate algorithm (n = 1 or n >= 3)."""
    if n < 1 or n == 2:
        raise ValueError("No magic square exists for this order.")
    case = classify(n)
    if case == "odd":
        return _siamese(n)
    if case == "doubly_even":
        return _doubly_even(n)
    return _singly_even(n)


# ----------------------------------------------------------------------------
# Step generators for the simulation
# ----------------------------------------------------------------------------
@dataclass
class Step:
    changes: List[Tuple[int, int, int]]          # (row, col, new value) written in this step
    focus: List[Cell]                            # cells highlighted while the step is shown
    text: str                                    # human readable explanation
    line: int                                    # index into PSEUDOCODE[case]


def _odd_steps(n: int, prefix: str = "", fixed_line=None) -> Tuple[Grid, List[Step]]:
    g = [[0] * n for _ in range(n)]
    steps: List[Step] = []
    r, c = 0, n // 2
    note, line = "Start: 1 goes in the top row, middle column.", 2
    for k in range(1, n * n + 1):
        g[r][c] = k
        steps.append(Step([(r, c, k)], [(r, c)], f"{prefix}{k} → row {r + 1}, col {c + 1}.  {note}",
                          line if fixed_line is None else fixed_line))
        nr, nc = (r - 1) % n, (c + 1) % n
        wrapped = (r == 0 or c == n - 1)
        if g[nr][nc]:
            nr, nc = (r + 1) % n, c
            note, line = "The up-right cell is occupied, so move one cell down.", 5
        else:
            note = "Move up-right" + (" (wrapped around the edge)." if wrapped else ".")
            line = 3
        r, c = nr, nc
    return g, steps


def _doubly_even_steps(n: int) -> Tuple[Grid, List[Step]]:
    total = n * n
    g = [[0] * n for _ in range(n)]
    steps: List[Step] = []
    for i in range(n):                      # phase 1: reading order
        for j in range(n):
            v = i * n + j + 1
            g[i][j] = v
            steps.append(Step([(i, j, v)], [(i, j)], f"Phase 1 – write {v} in row {i + 1}, col {j + 1}.", 1))
    for i in range(n):                      # phase 2: complement the marked cells
        for j in range(n):
            if _is_marked(i, j):
                old = g[i][j]
                new = total + 1 - old
                g[i][j] = new
                steps.append(Step([(i, j, new)], [(i, j)],
                                  f"Phase 2 – cell ({i + 1},{j + 1}) is on a 4×4 block diagonal: "
                                  f"{old} → {total}+1−{old} = {new}.", 5))
    return g, steps


def _singly_even_steps(n: int) -> Tuple[Grid, List[Step]]:
    m = n // 2
    q = m * m
    a, a_steps = _odd_steps(m, prefix="Quadrant A (Siamese) – ", fixed_line=1)
    steps: List[Step] = list(a_steps)       # A is built in the top-left quadrant
    g = [[0] * n for _ in range(n)]
    for i in range(m):
        for j in range(m):
            g[i][j] = a[i][j]
    cells = sorted(((a[i][j], i, j) for i in range(m) for j in range(m)))
    for v, i, j in cells:                   # copy each value into the other three quadrants
        g[i + m][j + m] = v + q
        g[i][j + m] = v + 2 * q
        g[i + m][j] = v + 3 * q
        steps.append(Step([(i + m, j + m, v + q), (i, j + m, v + 2 * q), (i + m, j, v + 3 * q)],
                          [(i, j), (i + m, j + m), (i, j + m), (i + m, j)],
                          f"Copy A={v}:  bottom-right = {v}+{q} = {v + q},  top-right = {v}+{2 * q} = {v + 2 * q},  "
                          f"bottom-left = {v}+{3 * q} = {v + 3 * q}.", 3))
    for i, j in _strachey_swaps(n):         # swap columns between top and bottom halves
        top, bottom = g[i][j], g[i + m][j]
        g[i][j], g[i + m][j] = bottom, top
        steps.append(Step([(i, j, bottom), (i + m, j, top)], [(i, j), (i + m, j)],
                          f"Swap ({i + 1},{j + 1}) ↔ ({i + m + 1},{j + 1}):  {top} ↔ {bottom}.",
                          4 if j < m else 6))
    return g, steps


def construct_with_steps(n: int) -> Tuple[Grid, List[Step]]:
    """Same result as construct(n) but also returns the list of simulation steps."""
    if n < 1 or n == 2:
        raise ValueError("No magic square exists for this order.")
    case = classify(n)
    if case == "odd":
        return _odd_steps(n)
    if case == "doubly_even":
        return _doubly_even_steps(n)
    return _singly_even_steps(n)


def replay_steps(grid: Grid, strategy: str) -> List[Step]:
    """Row-by-row replay of a square found by brute force (so it can also be animated)."""
    n = len(grid)
    line = 3 if strategy == "naive" else 6
    return [Step([(i, j, grid[i][j])], [(i, j)],
                 f"Found by search – place {grid[i][j]} in row {i + 1}, col {j + 1}.", line)
            for i in range(n) for j in range(n)]


# ----------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------
@dataclass
class LineCheck:
    name: str
    cells: List[Cell]
    values: List[int]
    total: int
    ok: bool


@dataclass
class Verification:
    n: int
    magic: int
    lines: List[LineCheck] = field(default_factory=list)
    distinct: bool = True            # each of 1..n^2 appears exactly once
    valid: bool = False


def verify(grid: Grid) -> Verification:
    """Add up every row, every column and both main diagonals and compare with M(n)."""
    n = len(grid)
    m = magic_constant(n)
    lines: List[LineCheck] = []

    def add(name: str, cells: List[Cell]) -> None:
        vals = [grid[r][c] for r, c in cells]
        total = sum(vals)
        lines.append(LineCheck(name, cells, vals, total, total == m))

    for i in range(n):
        add(f"Row {i + 1}", [(i, j) for j in range(n)])
    for j in range(n):
        add(f"Column {j + 1}", [(i, j) for i in range(n)])
    add("Main diagonal", [(i, i) for i in range(n)])
    add("Anti-diagonal", [(i, n - 1 - i) for i in range(n)])
    distinct = sorted(v for row in grid for v in row) == list(range(1, n * n + 1))
    return Verification(n, m, lines, distinct, distinct and all(l.ok for l in lines))


# ==========================================================================
#  SECTION 3 - BRUTE-FORCE SEARCHES (run in a worker thread, with time limit + cancel)
# ==========================================================================

class SearchControl:
    """Shared between the GUI thread and the search thread."""

    def __init__(self, time_limit: float):
        self.time_limit = time_limit          # seconds
        self.cancel = threading.Event()       # set by the Stop button
        self.nodes = 0                        # live counter read by the GUI
        self.start = time.perf_counter()


@dataclass
class SearchResult:
    grid: Optional[Grid]
    status: str              # 'found' | 'timeout' | 'cancelled' | 'error'
    nodes: int               # arrangements / nodes examined
    elapsed: float           # seconds (time.perf_counter)


def _is_magic(grid: Grid, m: int) -> bool:
    n = len(grid)
    if any(sum(row) != m for row in grid):
        return False
    if any(sum(grid[i][j] for i in range(n)) != m for j in range(n)):
        return False
    return sum(grid[i][i] for i in range(n)) == m and sum(grid[i][n - 1 - i] for i in range(n)) == m


def naive_search(n: int, ctl: SearchControl) -> SearchResult:
    """Test permutations of 1..n^2 until one is magic (only n = 3 finishes quickly: 9! = 362,880)."""
    ctl.start = t0 = time.perf_counter()
    m = magic_constant(n)
    nodes = 0
    for perm in itertools.permutations(range(1, n * n + 1)):
        nodes += 1
        if not nodes & 0x3FF:                              # every 1024 permutations
            ctl.nodes = nodes
            if ctl.cancel.is_set():
                return SearchResult(None, "cancelled", nodes, time.perf_counter() - t0)
            if time.perf_counter() - t0 > ctl.time_limit:
                return SearchResult(None, "timeout", nodes, time.perf_counter() - t0)
        if sum(perm[:n]) != m:                             # cheap early rejection of the first row
            continue
        grid = [list(perm[i * n:(i + 1) * n]) for i in range(n)]
        if _is_magic(grid, m):
            ctl.nodes = nodes
            return SearchResult(grid, "found", nodes, time.perf_counter() - t0)
    ctl.nodes = nodes
    return SearchResult(None, "error", nodes, time.perf_counter() - t0)


def backtracking_search(n: int, ctl: SearchControl) -> SearchResult:
    """
    Fill the grid cell by cell (row-major) and abandon a partial grid as soon as it cannot
    be completed.  Pruning rules:
      * a row / column / diagonal sum may never exceed M(n);
      * the last cell of a row / column / diagonal must make the sum exactly M(n);
      * bound test: the k cells still empty in a row (or column) must be able to reach M(n)
        with the numbers that are still free  ->  sum + (k smallest free) <= M <= sum + (k largest free).
    """
    ctl.start = t0 = time.perf_counter()
    total_cells = n * n
    m = magic_constant(n)
    grid = [[0] * n for _ in range(n)]
    rows, cols = [0] * n, [0] * n
    diag = [0, 0]                       # main diagonal, anti-diagonal
    free: List[int] = list(range(1, total_cells + 1))   # always sorted
    state = {"nodes": 0, "stop": ""}

    def bounds(idx: int, k: int):
        """Smallest and largest possible sum of k free numbers, excluding free[idx]."""
        size = len(free)
        if idx < k + 1:
            lo = sum(free[:k + 1]) - free[idx]
        else:
            lo = sum(free[:k])
        if idx >= size - k - 1:
            hi = sum(free[size - k - 1:]) - free[idx]
        else:
            hi = sum(free[size - k:])
        return lo, hi

    def place(pos: int) -> bool:
        if pos == total_cells:
            return True
        r, c = divmod(pos, n)
        rem_row, rem_col = n - 1 - c, n - 1 - r
        on_main, on_anti = (r == c), (r + c == n - 1)
        for idx in range(len(free)):
            v = free[idx]
            state["nodes"] += 1
            if not state["nodes"] & 0x3FF:
                ctl.nodes = state["nodes"]
                if ctl.cancel.is_set():
                    state["stop"] = "cancelled"
                    return False
                if time.perf_counter() - t0 > ctl.time_limit:
                    state["stop"] = "timeout"
                    return False
            rs, cs = rows[r] + v, cols[c] + v
            if rs > m or cs > m:
                break                                   # free is ascending: larger v only gets worse
            if rem_row == 0:
                if rs != m:
                    continue
            else:
                lo, hi = bounds(idx, rem_row)
                if rs + lo > m or rs + hi < m:
                    continue
            if rem_col == 0:
                if cs != m:
                    continue
            else:
                lo, hi = bounds(idx, rem_col)
                if cs + lo > m or cs + hi < m:
                    continue
            nd = diag[0] + v if on_main else 0
            na = diag[1] + v if on_anti else 0
            if on_main and (nd > m or (r == n - 1 and nd != m)):
                continue
            if on_anti and (na > m or (r == n - 1 and na != m)):
                continue
            # --- place v ---
            free.pop(idx)
            grid[r][c] = v
            rows[r], cols[c] = rs, cs
            if on_main:
                diag[0] = nd
            if on_anti:
                diag[1] = na
            if place(pos + 1):
                return True
            if state["stop"]:
                return False
            # --- backtrack ---
            free.insert(idx, v)
            grid[r][c] = 0
            rows[r] -= v
            cols[c] -= v
            if on_main:
                diag[0] -= v
            if on_anti:
                diag[1] -= v
        return False

    try:
        found = place(0)
    except RecursionError:
        return SearchResult(None, "error", state["nodes"], time.perf_counter() - t0)
    ctl.nodes = state["nodes"]
    elapsed = time.perf_counter() - t0
    if found:
        return SearchResult([row[:] for row in grid], "found", state["nodes"], elapsed)
    return SearchResult(None, state["stop"] or "error", state["nodes"], elapsed)


STRATEGIES = {
    "Backtracking with pruning": ("backtracking", backtracking_search),
    "Naive permutations": ("naive", naive_search),
}

STATUS_TEXT = {"found": "Solved", "timeout": "Limit reached", "cancelled": "Stopped", "error": "No result",
               "notrun": "Not run yet"}
ROW_KEYS = ("construct", "backtracking", "naive")
ROW_NAMES = {"construct": "Constructive algorithm",
             "backtracking": "Brute force – backtracking with pruning",
             "naive": "Brute force – naive permutations"}


def blank_row(key: str) -> dict:
    """A comparison row for a method that has not been run yet."""
    return dict(key=key, name=ROW_NAMES[key], seconds=0.0, nodes=0, status="notrun", valid=False)


def time_text(r: dict) -> str:
    return "–" if r["status"] == "notrun" else fmt_time(r["seconds"])


def nodes_text(r: dict) -> str:
    return "–" if r["status"] == "notrun" else f"{r['nodes']:,}"


def factorial_text(k: int) -> str:
    if k <= 12:
        return f"{math.factorial(k):,}"
    return f"about 10^{math.lgamma(k + 1) / math.log(10):.0f}"


def run_comparison(n: int, limit: float, cancel: threading.Event, holder: dict, report=None) -> list:
    """Time the constructive algorithm and both brute-force searches on the same order n.

    Returns a list of dict rows: key, name, seconds, nodes, status, valid.
    `holder["ctl"]` always points at the search being run so a Stop button can cancel it.
    """
    rows = []
    if report:
        report("Timing the constructive algorithm…")
    reps = max(1, min(200, 200000 // (n * n)))
    t0 = time.perf_counter()
    for _ in range(reps):
        construct(n)
    dt = (time.perf_counter() - t0) / reps
    rows.append(dict(key="construct", name="Constructive algorithm", seconds=dt, nodes=n * n,
                     status="found", valid=verify(construct(n)).valid))
    for label, (key, func) in STRATEGIES.items():
        if cancel.is_set():
            break
        if report:
            report(f"Running brute force: {label.lower()} (limit {limit:g} s)…")
        ctl = SearchControl(limit)
        holder["ctl"] = ctl
        res = func(n, ctl)
        rows.append(dict(key=key, name=f"Brute force – {label.lower()}", seconds=res.elapsed, nodes=res.nodes,
                         status=res.status, valid=bool(res.grid and verify(res.grid).valid)))
    return rows


def ratio_text(row: dict, base: float) -> str:
    """How much slower than the constructive algorithm a row was."""
    if row["key"] == "construct":
        return "baseline"
    if row["status"] == "notrun":
        return "not run yet"
    if base <= 0:
        return "-"
    r = row["seconds"] / base
    num = f"{r:,.0f}" if r >= 10 else f"{r:.1f}"
    return f"{num}× slower" if row["status"] == "found" else f"> {num}× slower (not finished)"


# ==========================================================================
#  SECTION 4 - REPORTS: CSV, TXT and PDF (the PDF writer is a tiny built-in one)
# ==========================================================================

def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_square_info(n, mode, method, time_text, nodes_text) -> dict:
    return dict(n=n, case=CASE_TITLES[classify(n)], mode=mode, method=method,
                time=time_text, nodes=nodes_text, generated=now_text())


def kv_rows(info: dict, ver: Verification) -> list:
    n = info["n"]
    return [
        ("Application", APP_NAME),
        ("Generated", info["generated"]),
        ("Order entered (n)", n),
        ("Grid size", f"{n} x {n}"),
        ("Grid type", info["case"]),
        ("Mode", info["mode"]),
        ("Method", info["method"]),
        ("Magic constant M(n)", f"{n}({n}²+1)/2 = {ver.magic}"),
        ("Time taken", info["time"]),
        ("Nodes / arrangements", info["nodes"]),
        ("Numbers 1..n² each used once", "yes" if ver.distinct else "NO"),
        ("Result", "VALID magic square" if ver.valid else "NOT a valid magic square"),
    ]


def square_table(grid: Grid) -> list:
    """Grid as a table: header row, one row per grid row (+ row sum), final row of column sums."""
    n = len(grid)
    rows = [["Row \\ Col"] + [str(j + 1) for j in range(n)] + ["Row sum"]]
    for i in range(n):
        rows.append([f"Row {i + 1}"] + [str(v) for v in grid[i]] + [str(sum(grid[i]))])
    rows.append(["Col sum"] + [str(sum(grid[i][j] for i in range(n))) for j in range(n)] + [""])
    return rows


def line_rows(ver: Verification) -> list:
    return [[l.name, l.total, ver.magic, "OK" if l.ok else "FAIL"] for l in ver.lines]


def compare_rows(data: dict) -> list:
    base = data["rows"][0]["seconds"]
    return [[r["name"], time_text(r), "" if r["status"] == "notrun" else f"{r['seconds']:.9f}", nodes_text(r),
             STATUS_TEXT.get(r["status"], r["status"]), ratio_text(r, base)] for r in data["rows"]]


COMPARE_HEAD = ["Method", "Time taken", "Seconds", "Nodes / arrangements", "Status", "Compared with algorithm"]


def text_table(rows: list, header: Optional[list] = None, right_from: Optional[int] = None) -> str:
    """Plain-text table with aligned columns.  right_from = first column that is right-aligned."""
    allrows = ([list(map(str, header))] if header else []) + [list(map(str, r)) for r in rows]
    ncol = max(len(r) for r in allrows)
    allrows = [r + [""] * (ncol - len(r)) for r in allrows]
    widths = [max(len(r[i]) for r in allrows) for i in range(ncol)]

    def fmt(r):
        cells = [r[i].rjust(widths[i]) if right_from is not None and i >= right_from else r[i].ljust(widths[i])
                 for i in range(ncol)]
        return "| " + " | ".join(cells) + " |"

    rule = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    out = [rule]
    for idx, r in enumerate(allrows):
        out.append(fmt(r))
        if idx == 0 and header:
            out.append(rule)
    out.append(rule)
    return "\n".join(out)


def write_square_csv(path, info, grid, ver):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:      # BOM: Excel opens the symbols correctly
        w = csv.writer(fh)
        w.writerow([f"{APP_NAME.upper()} - MAGIC SQUARE REPORT"])
        for k, v in kv_rows(info, ver):
            w.writerow([k, v])
        w.writerow([])
        w.writerow(["MAGIC SQUARE"])
        w.writerows(square_table(grid))
        w.writerow([])
        w.writerow(["ROW / COLUMN / DIAGONAL SUMS"])
        w.writerow(["Line", "Sum", "M(n)", "Status"])
        w.writerows(line_rows(ver))


def write_square_txt(path, info, grid, ver):
    parts = [f"{APP_NAME.upper()} - MAGIC SQUARE REPORT", "=" * 60, "",
             text_table(kv_rows(info, ver)), "", "MAGIC SQUARE",
             text_table(square_table(grid)[1:-1], header=square_table(grid)[0], right_from=1), "",
             "ROW / COLUMN / DIAGONAL SUMS", text_table(line_rows(ver), header=["Line", "Sum", "M(n)", "Status"], right_from=1)]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts) + "\n")


def write_compare_csv(path, data):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow([f"{APP_NAME.upper()} - TIME COMPARISON REPORT"])
        for k, v in compare_info(data):
            w.writerow([k, v])
        w.writerow([])
        w.writerow(COMPARE_HEAD)
        w.writerows(compare_rows(data))


def write_compare_txt(path, data):
    parts = [f"{APP_NAME.upper()} - TIME COMPARISON REPORT", "=" * 60, "", text_table(compare_info(data)), "",
             text_table(compare_rows(data), header=COMPARE_HEAD), "", compare_summary(data)]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts) + "\n")


def compare_info(data: dict) -> list:
    n = data["n"]
    return [("Application", APP_NAME), ("Generated", data["generated"]), ("Order entered (n)", n),
            ("Grid size", f"{n} x {n}"), ("Grid type", CASE_TITLES[classify(n)]),
            ("Magic constant M(n)", magic_constant(n)), ("Search time limit", f"{data['limit']:g} s per method")]


def compare_summary(data: dict) -> str:
    rows, n = data["rows"], data["n"]
    base = rows[0]
    if base["status"] == "notrun":
        out = [f"The constructive algorithm has not been run for n = {n} yet (press Start)."]
    else:
        out = [f"The constructive algorithm built the {n}x{n} square in {fmt_time(base['seconds'])} "
               f"using {base['nodes']:,} cell writes."]
    for r in rows[1:]:
        what = r["name"].replace("Brute force – ", "")
        if r["status"] == "notrun":
            if r["key"] == "naive":
                out.append(f"Brute force ({what}) has not been run. It could need up to {factorial_text(n * n)} "
                           f"arrangements ({n * n}!), which is not feasible for n above 3.")
            else:
                out.append(f"Brute force ({what}) has not been run. It prunes most branches, but its worst case "
                           f"still grows exponentially.")
        elif r["status"] == "found":
            out.append(f"Brute force ({what}) needed {fmt_time(r['seconds'])} and {r['nodes']:,} nodes "
                       f"({ratio_text(r, base['seconds'])}).")
        elif r["status"] == "timeout":
            out.append(f"Brute force ({what}) was stopped by the time limit after {fmt_time(r['seconds'])} and "
                       f"{r['nodes']:,} nodes without finding a square.")
        else:
            out.append(f"Brute force ({what}) was {STATUS_TEXT.get(r['status'], r['status']).lower()} after "
                       f"{fmt_time(r['seconds'])}.")
    return "  ".join(out)


class MiniPDF:
    """Very small PDF writer (A4, built-in Helvetica / Courier fonts): text, rectangles, tables."""
    W, H, M = 595.28, 841.89, 40.0
    HEAD, ZEBRA, INK = (35, 38, 52), (240, 238, 250), (30, 30, 45)
    OKC, BADC = (16, 130, 78), (200, 50, 50)

    def __init__(self):
        self.pages: list = []
        self.ops: list = []
        self.y = 0.0
        self.new_page()

    @staticmethod
    def _s(text) -> str:
        text = str(text)
        for a, b in (("✓", "OK"), ("✗", "FAIL"), ("≥", ">="), ("≈", "~"), ("→", "->"), ("−", "-"), ("≠", "!="),
                     ("…", "..."), ("²", "^2"), ("µ", "u")):
            text = text.replace(a, b)
        text = text.encode("cp1252", "replace").decode("cp1252")
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    @staticmethod
    def _c(rgb) -> str:
        return "%.3f %.3f %.3f" % tuple(v / 255 for v in rgb)

    def new_page(self):
        self.ops = []
        self.pages.append(self.ops)
        self.y = self.H - self.M

    def text(self, x, y, s, size=10, font="F1", color=(0, 0, 0)):
        self.ops.append(f"BT /{font} {size:.2f} Tf {self._c(color)} rg {x:.2f} {y:.2f} Td ({self._s(s)}) Tj ET")

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=0.5):
        parts = [f"{lw} w"]
        if fill:
            parts.append(f"{self._c(fill)} rg")
        if stroke:
            parts.append(f"{self._c(stroke)} RG")
        op = "B" if fill and stroke else "f" if fill else "S"
        parts.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}")
        self.ops.append(" ".join(parts))

    def room(self, h) -> bool:
        return self.y - h >= self.M + 24

    def banner(self, title, subtitle):
        h = 68
        self.rect(0, self.H - h, self.W, h, fill=(20, 20, 24))
        self.rect(0, self.H - h - 3, self.W, 3, fill=(232, 190, 92))
        self.text(self.M, self.H - 32, title, 22, "F2", (232, 190, 92))
        self.text(self.M, self.H - 52, subtitle, 10, "F1", (235, 235, 235))
        self.y = self.H - h - 24

    def heading(self, s, size=13):
        if not self.room(40):
            self.new_page()
        self.y -= 6
        self.text(self.M, self.y - size, s, size, "F2", self.INK)
        self.y -= size + 8

    def paragraph(self, s, size=10, width=98):
        for line in textwrap.wrap(s, width):
            if not self.room(16):
                self.new_page()
            self.text(self.M, self.y - size, line, size, "F1", self.INK)
            self.y -= size + 4
        self.y -= 6

    def table(self, headers, rows, widths, size=9, row_h=17):
        x0, total_w = self.M, sum(widths)

        def head():
            self.rect(x0, self.y - row_h, total_w, row_h, fill=self.HEAD)
            x = x0
            for h, w in zip(headers, widths):
                self.text(x + 4, self.y - row_h + 5, h, size, "F2", (255, 255, 255))
                x += w
            self.y -= row_h

        if not self.room(row_h * 3):
            self.new_page()
        head()
        for i, r in enumerate(rows):
            if not self.room(row_h):
                self.new_page()
                head()
            if i % 2 == 0:
                self.rect(x0, self.y - row_h, total_w, row_h, fill=self.ZEBRA)
            x = x0
            for cell, w in zip(r, widths):
                s = str(cell)
                limit = max(3, int(w / (size * 0.52)))
                if len(s) > limit:
                    s = s[:limit - 2] + ".."
                color = self.OKC if s.startswith(("OK", "Solved", "VALID")) else \
                    self.BADC if s.startswith(("FAIL", "NOT", "NO")) else self.INK
                self.text(x + 4, self.y - row_h + 5, s, size, "F1", color)
                x += w
            self.y -= row_h
        self.y -= 8

    def grid(self, g):
        n = len(g)
        total = n * n
        cell = min(36.0, (self.W - 2 * self.M) / n)
        if not self.room(n * cell + 10) and self.y < self.H - 200:
            self.new_page()
        x0 = (self.W - n * cell) / 2
        digits = len(str(total))
        size = min(cell * 0.45, cell * 0.9 / (0.6 * digits))
        lo, hi = (205, 222, 255), (110, 56, 230)
        for i in range(n):
            for j in range(n):
                v = g[i][j]
                t = (v - 1) / (total - 1) if total > 1 else 0
                rgb = tuple(int(lo[k] + (hi[k] - lo[k]) * t) for k in range(3))
                lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
                x, y = x0 + j * cell, self.y - (i + 1) * cell
                self.rect(x, y, cell, cell, fill=rgb, stroke=(255, 255, 255), lw=0.4)
                s = str(v)
                self.text(x + cell / 2 - 0.3 * size * len(s), y + cell / 2 - 0.35 * size, s, size, "F3",
                          (20, 20, 30) if lum > 150 else (255, 255, 255))
        self.y -= n * cell + 14

    def bars(self, rows):
        """Horizontal bars on a log10 scale (used by the time comparison report)."""
        run = [math.log10(max(r["seconds"], 1e-7)) for r in rows if r["status"] != "notrun"]
        lo = math.floor(min(run)) - 1 if run else 0
        hi = max(math.ceil(max(run)) if run else 1, lo + 1)
        label_w, bar_w = 170, 250
        for r in rows:
            if not self.room(30):
                self.new_page()
            self.text(self.M, self.y - 12, r["name"].replace("Brute force – ", "Brute force: "), 9, "F1", self.INK)
            if r["status"] == "notrun":
                self.text(self.M + label_w, self.y - 12, "not run yet", 9, "F1", (110, 110, 130))
                self.y -= 26
                continue
            v = math.log10(max(r["seconds"], 1e-7))
            length = max(4.0, (v - lo) / (hi - lo) * bar_w)
            color = (110, 56, 230) if r["key"] == "construct" else (217, 130, 11) if r["status"] == "found" else (210, 58, 58)
            self.rect(self.M + label_w, self.y - 15, length, 14, fill=color)
            tail = fmt_time(r["seconds"]) + ("" if r["status"] == "found" else "  (limit reached)")
            self.text(self.M + label_w + length + 6, self.y - 12, tail, 9, "F2", self.INK)
            self.y -= 26
        self.text(self.M + label_w, self.y - 10, "log scale: every step to the right is about 10x longer", 8, "F1", (110, 110, 130))
        self.y -= 24

    def save(self, path):
        n_pages = len(self.pages)
        for i, ops in enumerate(self.pages):                      # footer on every page
            ops.append(f"BT /F1 8 Tf 0.45 0.45 0.5 rg {self.M:.2f} 22 Td ({self._s(APP_NAME)}  -  Data Structures and "
                       f"Algorithms, Fall 2026) Tj ET")
            ops.append(f"BT /F1 8 Tf 0.45 0.45 0.5 rg {self.W - self.M - 52:.2f} 22 Td (Page {i + 1} of {n_pages}) Tj ET")
        objs = [b"<< /Type /Catalog /Pages 2 0 R >>"]
        kids = " ".join(f"{6 + 2 * i} 0 R" for i in range(n_pages))
        objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
        for base in ("Helvetica", "Helvetica-Bold", "Courier-Bold"):
            objs.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>".encode())
        for i, ops in enumerate(self.pages):
            stream = "\n".join(ops).encode("cp1252", "replace")
            objs.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.W} {self.H}] /Resources << /Font << "
                         f"/F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents {7 + 2 * i} 0 R >>").encode())
            objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for num, body in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % num + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
        with open(path, "wb") as fh:
            fh.write(bytes(out))


def write_square_pdf(path, info, grid, ver):
    pdf = MiniPDF()
    pdf.banner(APP_NAME, f"Magic Square Report  -  order {info['n']}  -  {info['generated']}")
    pdf.heading("Run details")
    pdf.table(["Item", "Value"], [(k, v) for k, v in kv_rows(info, ver)], [190, 325])
    pdf.heading(f"The {info['n']} x {info['n']} magic square")
    pdf.grid(grid)
    pdf.heading("Row, column and diagonal sums  (every line must equal M(n) = %d)" % ver.magic, 12)
    rows = line_rows(ver)
    per = math.ceil(len(rows) / 3)
    trio = []
    for i in range(per):
        line = []
        for c in range(3):
            if i + c * per < len(rows):
                r = rows[i + c * per]
                line += [r[0], r[1], r[3]]
            else:
                line += ["", "", ""]
        trio.append(line)
    pdf.table(["Line", "Sum", "Result"] * 3, trio, [78, 42, 50] * 3, size=8.5, row_h=15)
    pdf.save(path)


def write_compare_pdf(path, data):
    pdf = MiniPDF()
    pdf.banner(APP_NAME, f"Time Comparison Report  -  brute force vs algorithm  -  {data['generated']}")
    pdf.heading("Run details")
    pdf.table(["Item", "Value"], compare_info(data), [190, 325])
    pdf.heading("Measured times")
    base = data["rows"][0]["seconds"]
    pdf.table(["Method", "Time taken", "Nodes", "Status", "vs algorithm"],
              [[r["name"], time_text(r), nodes_text(r), STATUS_TEXT.get(r["status"], r["status"]),
                ratio_text(r, base)] for r in data["rows"]], [165, 80, 85, 70, 115])
    pdf.heading("Time taken (log scale)")
    pdf.bars(data["rows"])
    pdf.heading("Conclusion")
    pdf.paragraph(compare_summary(data))
    pdf.paragraph("The constructive methods do a fixed amount of work per cell, so they take O(n²) time. Naive brute force "
                  "may examine up to (n²)! arrangements, and backtracking, although much faster thanks to pruning, "
                  "still grows exponentially in the worst case.")
    pdf.save(path)


# ==========================================================================
#  SECTION 5 - DIALOGS & WINDOWS (pop-ups, export, details, time comparison, benchmark)
# ==========================================================================

POPUP_KINDS = {"error": ("✕", "RED"), "warning": ("!", "WARN"), "info": ("i", "ACC"), "success": ("✓", "GREEN")}


class Popup(tk.Toplevel):
    """Small modal message window (replaces the grey system message box so it follows the theme)."""

    def __init__(self, app, title, message, kind="error"):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.resizable(False, False)
        self.transient(app)
        app.reg(self, bg="CARD")
        sym, tok = POPUP_KINDS[kind]
        app.reg(tk.Frame(self, height=px(5)), bg=tok).pack(fill="x")
        row = app.frm(self, "CARD")
        row.pack(fill="x", padx=px(28), pady=(px(24), px(10)))
        icon = tk.Canvas(row, width=px(54), height=px(54), highlightthickness=0)
        app.reg(icon, bg="CARD")
        icon.create_oval(px(2), px(2), px(52), px(52), fill=PAL[tok], outline=PAL[tok])
        icon.create_text(px(27), px(27), text=sym, fill="#FFFFFF", font=font(20, "bold"))
        icon.pack(side="left", anchor="n")
        txt = app.frm(row, "CARD")
        txt.pack(side="left", padx=(px(18), 0))
        app.lbl(txt, title, size=13, weight="bold", anchor="w", justify="left").pack(anchor="w")
        app.lbl(txt, message, fg="MUTE", size=10, anchor="w", justify="left", wraplength=px(400)).pack(anchor="w", pady=(px(6), 0))
        foot = app.frm(self, "CARD")
        foot.pack(fill="x", padx=px(28), pady=(px(10), px(22)))
        self.ok = app.button(foot, "OK", self.close, "primary", width=10)
        self.ok.pack(side="right")
        self.bind("<Return>", lambda e: self.close())
        self.bind("<Escape>", lambda e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)
        place_over(self, app)
        self.grab_set()
        self.ok.focus_set()

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


def place_over(win, app):
    """Centre a window over the main window."""
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    x = app.winfo_rootx() + (app.winfo_width() - w) // 2
    y = app.winfo_rooty() + (app.winfo_height() - h) // 3
    win.geometry(f"+{max(0, x)}+{max(0, y)}")


class Tip:
    """Small hover hint ("tooltip") shown under a widget after half a second."""

    def __init__(self, app, widget, text):
        self.w, self.text, self.win, self.job = widget, text, None, None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def schedule(self, _e=None):
        self.hide()
        self.job = self.w.after(450, self.show)

    def show(self):
        self.job = None
        try:
            x, y = self.w.winfo_rootx() + px(8), self.w.winfo_rooty() + self.w.winfo_height() + px(4)
            self.win = tk.Toplevel(self.w)
            self.win.wm_overrideredirect(True)
            self.win.wm_geometry(f"+{x}+{y}")
            tk.Label(self.win, text=self.text, bg=PAL["INK"], fg=PAL["CARD"], font=font(9), padx=px(8), pady=px(4),
                     justify="left").pack()
        except tk.TclError:
            self.win = None

    def hide(self, _e=None):
        if self.job:
            self.w.after_cancel(self.job)
            self.job = None
        if self.win:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None


class ExportDialog(tk.Toplevel):
    """Choose the download format: CSV, PDF or TXT."""

    FORMATS = (("csv", "CSV", "Spreadsheet table\n(opens in Excel)"),
               ("pdf", "PDF", "Formatted report\n(print or share)"),
               ("txt", "TXT", "Plain text table\n(any editor)"))

    def __init__(self, app, title, subtitle, callback):
        super().__init__(app)
        self.app, self.callback = app, callback
        self.title("Export")
        self.resizable(False, False)
        self.transient(app)
        app.reg(self, bg="CARD")
        app.reg(tk.Frame(self, height=px(5)), bg="ACC").pack(fill="x")
        app.lbl(self, title, size=14, weight="bold").pack(anchor="w", padx=px(28), pady=(px(22), 0))
        app.lbl(self, subtitle, fg="MUTE", size=10).pack(anchor="w", padx=px(28), pady=(px(4), px(16)))
        row = app.frm(self, "CARD")
        row.pack(fill="x", padx=px(28))
        for i, (key, name, desc) in enumerate(self.FORMATS):
            b = app.button(row, f"{name}\n\n{desc}", lambda k=key: self.choose(k), "plain", width=16,
                           pady=px(16), font=font(10, "bold"))
            b.grid(row=0, column=i, padx=(0 if i == 0 else px(12), 0))
        foot = app.frm(self, "CARD")
        foot.pack(fill="x", padx=px(28), pady=(px(18), px(22)))
        app.button(foot, "Cancel", self.destroy, "plain", width=10).pack(side="right")
        self.bind("<Escape>", lambda e: self.destroy())
        place_over(self, app)
        self.grab_set()

    def choose(self, key):
        self.grab_release()
        self.destroy()
        self.callback(key)


class DetailsWindow(tk.Toplevel):
    """Every row / column / diagonal addition the computer made."""

    def __init__(self, app, ver):
        super().__init__(app)
        self.app, self.ver = app, ver
        self.title(f"Validation details – {ver.n} × {ver.n} magic square")
        app.reg(self, bg="BG")
        self.geometry(f"{px(1000)}x{px(680)}+{px(80)}+{px(50)}")
        self.minsize(px(760), px(500))
        self.protocol("WM_DELETE_WINDOW", self.close)
        pad = px(20)

        good = sum(1 for l in ver.lines if l.ok)
        head = app.frm(self, "PANEL")
        head.pack(fill="x")
        app.lbl(head, f"Order n = {ver.n}      Magic constant M(n) = {ver.n}({ver.n}²+1)/2 = {ver.magic}",
                fg="TITLE", bg="PANEL", size=13, weight="bold").pack(anchor="w", padx=pad, pady=(px(14), px(2)))
        verdict = "VALID MAGIC SQUARE ✓" if ver.valid else "NOT A VALID MAGIC SQUARE ✗"
        app.lbl(head, f"{good} of {len(ver.lines)} lines add up to {ver.magic}   ·   numbers 1…{ver.n ** 2} each used once: "
                      f"{'yes' if ver.distinct else 'NO'}   ·   {verdict}",
                fg="GREEN" if ver.valid else "RED", bg="PANEL", size=10, weight="bold").pack(anchor="w", padx=pad, pady=(0, px(14)))
        app.reg(tk.Frame(self, height=px(2)), bg="ACC").pack(fill="x")

        app.lbl(self, "Click a line to highlight its cells on the grid. Use the filter to focus on one group.",
                fg="MUTE", bg="BG", size=10).pack(anchor="w", padx=pad, pady=(px(14), px(6)))
        bar = app.frm(self, "BG")
        bar.pack(fill="x", padx=pad, pady=(0, px(8)))
        self.filter = tk.StringVar(value="All")
        self.fbtns = {}
        for name in ("All", "Rows", "Columns", "Diagonals"):
            b = app.button(bar, name, lambda n=name: self.set_filter(n), "plain", width=11)
            b.pack(side="left", padx=(0, px(8)))
            self.fbtns[name] = b

        mid = app.frm(self, "BG")
        mid.pack(fill="both", expand=True, padx=pad, pady=(0, px(8)))
        cols = ("line", "calc", "sum", "target", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
        for c, text, w, anchor in (("line", "Line", 130, "w"), ("calc", "Computer’s addition", 520, "w"),
                                   ("sum", "Sum", 80, "e"), ("target", "M(n)", 80, "e"), ("status", "Result", 90, "center")):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=px(w), anchor=anchor, stretch=(c == "calc"))
        vs = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(mid, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="we")
        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.detail = app.make(tk.Text, self, dict(bg="CARD", fg="INK", highlightbackground="EDGE", highlightcolor="EDGE"),
                               height=5, relief="flat", font=mono(11), wrap="word", padx=px(12), pady=px(8),
                               state="disabled", highlightthickness=1)
        self.detail.pack(fill="x", padx=pad, pady=(px(4), px(8)))
        foot = app.frm(self, "BG")
        foot.pack(fill="x", padx=pad, pady=(0, px(16)))
        app.button(foot, "Close", self.close, "primary", width=10).pack(side="right")
        app.hooks.append(self.retag)
        self.retag()
        self.set_filter("All")

    def retag(self):
        P = PAL
        self.tree.tag_configure("ok", foreground=P["GREEN"])
        self.tree.tag_configure("bad", foreground=P["RED"])
        self.detail.tag_configure("ok", foreground=P["GREEN"])
        self.detail.tag_configure("bad", foreground=P["RED"])
        self.detail.tag_configure("head", foreground=P["ACC"], font=mono(11, "bold"))

    def set_filter(self, name):
        self.filter.set(name)
        for n, b in self.fbtns.items():
            b._kind = "primary" if n == name else "plain"
            self.app.restyle_button(b)
        self.fill()

    def fill(self):
        self.tree.delete(*self.tree.get_children())
        f = self.filter.get()
        self.items = {}
        for idx, l in enumerate(self.ver.lines):
            grp = "Rows" if l.name.startswith("Row") else "Columns" if l.name.startswith("Column") else "Diagonals"
            if f != "All" and f != grp:
                continue
            calc = " + ".join(map(str, l.values))
            iid = self.tree.insert("", "end", values=(l.name, calc, l.total, self.ver.magic, "✓ OK" if l.ok else "✗ FAIL"),
                                   tags=("ok" if l.ok else "bad",))
            self.items[iid] = idx

    def on_select(self, _e):
        sel = self.tree.selection()
        if not sel:
            return
        l = self.ver.lines[self.items[sel[0]]]
        self.app.mark_cells(l.cells)
        running, parts = 0, []
        for v in l.values:
            running += v
            parts.append(f"{running}")
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("end", f"{l.name}\n", "head")
        self.detail.insert("end", " + ".join(map(str, l.values)) + f" = {l.total}\n")
        self.detail.insert("end", "running total: " + " → ".join(parts) + "\n")
        verdict = f"{l.total} = M({self.ver.n}) = {self.ver.magic}  ✓" if l.ok else f"{l.total} ≠ {self.ver.magic}  ✗"
        self.detail.insert("end", verdict, "ok" if l.ok else "bad")
        self.detail.configure(state="disabled")

    def close(self):
        self.app.mark_cells([])
        self.destroy()


class BenchmarkWindow(tk.Toplevel):
    """Time vs n for every method: table, log graph and CSV export (data for the report)."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Benchmark – time taken vs order n")
        app.reg(self, bg="BG")
        self.geometry(f"{px(1180)}x{px(780)}+{px(60)}+{px(40)}")
        self.minsize(px(900), px(600))
        self.q = queue.Queue()
        self.stop = threading.Event()
        self.current = None
        self.rows = []
        self.rate = None                       # naive permutations per second (measured at n = 3)
        self.protocol("WM_DELETE_WINDOW", self.close)
        pad = px(20)

        bar = app.frm(self, "CARD", edge=True)
        bar.pack(fill="x", padx=pad, pady=(pad, px(10)))
        inner = app.frm(bar, "CARD")
        inner.pack(fill="x", padx=px(16), pady=px(14))
        self.max_n, self.brute_n, self.limit = tk.StringVar(value="12"), tk.StringVar(value="5"), tk.StringVar(value="5")
        for text, var, hi in (("Largest n (constructive)", self.max_n, 60), ("Brute force up to n", self.brute_n, 8),
                              ("Limit per search (s)", self.limit, 120)):
            app.lbl(inner, text, fg="MUTE").pack(side="left", padx=(0, px(6)))
            app.spin(inner, var, 3, hi, width=5).pack(side="left", padx=(0, px(22)))
        self.run_btn = app.button(inner, "▶  Run benchmark", self.start, "primary")
        self.run_btn.pack(side="left", padx=(0, px(8)))
        app.button(inner, "■  Stop", self.on_stop, "danger").pack(side="left")
        app.button(inner, "Export CSV", self.export, "plain").pack(side="right")
        self.status = tk.StringVar(value="Choose the range and press Run. Brute-force rows that hit the limit are marked “timeout”.")
        app.lbl(self, "", fg="ACC", bg="BG", size=10, weight="bold", textvariable=self.status, anchor="w").pack(fill="x", padx=pad + px(2))

        cols = ("n", "case", "construct", "bt", "bt_nodes", "naive", "est")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=9)
        for c, text, w in (("n", "n", 50), ("case", "Case", 110), ("construct", "Constructive", 120), ("bt", "Backtracking", 150),
                           ("bt_nodes", "BT nodes", 110), ("naive", "Naive (measured)", 150),
                           ("est", "Naive estimate: (n²)! / rate", 330)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=px(w), anchor="center" if c in ("n", "case") else "w")
        self.tree.pack(fill="x", padx=pad, pady=px(10))
        self.canvas = app.make(tk.Canvas, self, dict(bg="CARD", highlightbackground="EDGE"), highlightthickness=1)
        self.canvas.pack(fill="both", expand=True, padx=pad, pady=(0, pad))
        self.canvas.bind("<Configure>", lambda e: self.draw())
        app.hooks.append(self.draw)

    # ---------------------------------------------------------------- running
    def start(self):
        try:
            max_n, brute_n, limit = int(self.max_n.get()), int(self.brute_n.get()), float(self.limit.get())
            if max_n < 3 or brute_n < 3 or limit <= 0:
                raise ValueError
        except ValueError:
            self.app.popup("Invalid benchmark settings", "Please enter whole numbers of 3 or more for the two orders, "
                           "and a positive number of seconds for the limit.")
            return
        self.stop.clear()
        self.rows, self.rate = [], None
        self.tree.delete(*self.tree.get_children())
        self.run_btn.configure(state="disabled")
        self.app.restyle_button(self.run_btn)
        self.status.set("Running… (brute-force rows can take up to the limit each)")
        threading.Thread(target=self.work, args=(max_n, brute_n, limit), daemon=True).start()
        self.after(150, self.poll)

    def work(self, max_n, brute_n, limit):
        for n in range(3, max_n + 1):
            if self.stop.is_set():
                break
            reps = max(1, min(500, 500000 // (n * n)))
            t0 = time.perf_counter()
            for _ in range(reps):
                construct(n)
            row = {"n": n, "case": {"odd": "odd", "doubly_even": "doubly even", "singly_even": "singly even"}[classify(n)],
                   "construct": (time.perf_counter() - t0) / reps,
                   "bt": None, "bt_status": "", "bt_nodes": None, "naive": None, "naive_status": "", "naive_nodes": None}
            if n <= brute_n:
                for key, func in (("bt", backtracking_search), ("naive", naive_search)):
                    if self.stop.is_set():
                        break
                    self.current = SearchControl(limit)
                    res = func(n, self.current)
                    row[key], row[key + "_status"], row[key + "_nodes"] = res.elapsed, res.status, res.nodes
                    if key == "naive" and res.status == "found" and res.elapsed > 0:
                        row["rate"] = res.nodes / res.elapsed
            self.q.put(("row", row))
        self.q.put(("done", None))

    def on_stop(self):
        self.stop.set()
        if self.current:
            self.current.cancel.set()

    def poll(self):
        try:
            while True:
                kind, row = self.q.get_nowait()
                if kind == "row":
                    self.add_row(row)
                else:
                    self.run_btn.configure(state="normal")
                    self.app.restyle_button(self.run_btn)
                    self.status.set("Finished. The graph uses a log scale; dashed line = naive estimate from the measured rate.")
                    self.draw()
                    return
        except queue.Empty:
            pass
        self.after(150, self.poll)

    # ---------------------------------------------------------------- table / estimate
    def estimate(self, n):
        """log10 of the worst-case seconds for naive search: (n^2)! / (permutations per second)."""
        if not self.rate:
            return None
        return math.lgamma(n * n + 1) / math.log(10) - math.log10(self.rate)

    @staticmethod
    def fmt(row, key):
        t, st = row[key], row[key + "_status"]
        if t is None:
            return "–"
        return fmt_time(t) if st == "found" else f"{st} ({fmt_time(t)})"

    def add_row(self, row):
        if row.get("rate") and not self.rate:
            self.rate = row["rate"]
        self.rows.append(row)
        self.tree.delete(*self.tree.get_children())
        for r in self.rows:
            e = self.estimate(r["n"])
            if e is None:
                est = "(needs a finished n = 3 naive run)"
            elif e < 7:
                est = f"≈ {10 ** e:,.1f} s"
            else:
                est = f"≈ 10^{e:.1f} s  ≈ 10^{e - math.log10(3.156e7):.1f} years"
            self.tree.insert("", "end", values=(r["n"], r["case"], fmt_time(r["construct"]), self.fmt(r, "bt"),
                                                f"{r['bt_nodes']:,}" if r["bt_nodes"] else "–", self.fmt(r, "naive"), est))
        self.draw()

    # ---------------------------------------------------------------- graph (log10 seconds vs n)
    def draw(self):
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 400), max(c.winfo_height(), 200)
        l, r, t, b = px(80), w - px(30), px(48), h - px(52)
        c.create_text(l, px(18), anchor="w", fill=PAL["ACC"], font=font(11, "bold"), text="Time taken vs order n  (log10 of seconds)")
        if not self.rows:
            c.create_text(w / 2, h / 2, fill=PAL["MUTE"], font=font(12), text="Run the benchmark to draw the graph")
            return
        pts = {"Constructive O(n²)": [], "Backtracking (measured)": [], "Naive (measured)": [], "Naive estimate (n²)!": []}
        for rw in self.rows:
            n = rw["n"]
            pts["Constructive O(n²)"].append((n, math.log10(rw["construct"]), True))
            if rw["bt"] is not None:
                pts["Backtracking (measured)"].append((n, math.log10(max(rw["bt"], 1e-7)), rw["bt_status"] == "found"))
            if rw["naive"] is not None:
                pts["Naive (measured)"].append((n, math.log10(max(rw["naive"], 1e-7)), rw["naive_status"] == "found"))
            e = self.estimate(n)
            if e is not None:
                pts["Naive estimate (n²)!"].append((n, e, True))
        ys = [p[1] for series in pts.values() for p in series]
        y0, y1 = math.floor(min(ys)) - 1, math.ceil(max(ys)) + 1
        ns = [rw["n"] for rw in self.rows]
        x0, x1 = min(ns), max(max(ns), min(ns) + 1)

        def X(n): return l + (n - x0) / (x1 - x0) * (r - l)
        def Y(v): return b - (v - y0) / (y1 - y0) * (b - t)

        step = max(1, (y1 - y0) // 8)
        for v in range(y0, y1 + 1, step):
            c.create_line(l, Y(v), r, Y(v), fill=PAL["EDGE"])
            c.create_text(l - px(8), Y(v), anchor="e", fill=PAL["MUTE"], font=font(9), text=f"10^{v}")
        for n in range(x0, x1 + 1):
            c.create_text(X(n), b + px(14), fill=PAL["MUTE"], font=font(9), text=str(n))
        c.create_text((l + r) / 2, h - px(12), fill=PAL["INK"], font=font(10), text="order n")
        colors = {"Constructive O(n²)": PAL["GREEN"], "Backtracking (measured)": PAL["ACC"], "Naive (measured)": PAL["RED"],
                  "Naive estimate (n²)!": "#B58CD9"}
        lx = l + px(10)
        for name, series in pts.items():
            col = colors[name]
            c.create_rectangle(lx, px(34), lx + px(12), px(44), fill=col, outline=col)
            c.create_text(lx + px(18), px(39), anchor="w", fill=PAL["INK"], font=font(9), text=name)
            lx += px(40) + px(7) * len(name)
            dash = (4, 3) if "estimate" in name else None
            if len(series) > 1:
                c.create_line(*[v for p in series for v in (X(p[0]), Y(p[1]))], fill=col, width=2, dash=dash)
            for n, y, ok in series:
                c.create_oval(X(n) - 4, Y(y) - 4, X(n) + 4, Y(y) + 4, fill=col if ok else PAL["CARD"], outline=col, width=2)
        c.create_text(r, t - px(10), anchor="e", fill=PAL["MUTE"], font=font(9), text="hollow dot = limit reached (no solution found)")

    def export(self):
        if not self.rows:
            self.app.popup("Nothing to export", "Run the benchmark first, then export the table.", "warning")
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="benchmark_results.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["n", "case", "constructive_s", "backtracking_s", "backtracking_status", "backtracking_nodes",
                        "naive_s", "naive_status", "naive_nodes", "naive_estimate_log10_s"])
            for r in self.rows:
                e = self.estimate(r["n"])
                w.writerow([r["n"], r["case"], r["construct"], r["bt"], r["bt_status"], r["bt_nodes"], r["naive"],
                            r["naive_status"], r["naive_nodes"], "" if e is None else round(e, 3)])
        self.status.set(f"Saved {path}")

    def close(self):
        self.on_stop()
        self.destroy()


# ==========================================================================
#  SECTION 6 - MAIN WINDOW (controls, grid, simulation, verification, compare, export)
# ==========================================================================

MAX_N = 99
IDLE_VER = ("⏳  Pending…\n\nEvery row, column and both diagonals will be added up\n"
            "and checked against M(n) as soon as the square is complete.")


class MagicSquareApp(tk.Tk):
    def __init__(self):
        super().__init__()
        _SCALE[0] = max(1.0, self.winfo_fpixels("1i") / 96.0)
        fams = set(tkfont.families(self))
        FONT[0] = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "Noto Sans", "DejaVu Sans", "Arial")
                        if f in fams), "TkDefaultFont")
        MONO[0] = next((f for f in ("Consolas", "Menlo", "DejaVu Sans Mono", "Liberation Mono", "Courier New")
                        if f in fams), "Courier")
        set_palette("dark")
        self.title(f"{APP_NAME}  –  Magic Square Simulation  |  DSA Fall 2026  |  Assignments 1 & 2")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(px(1520), sw - 40), min(px(960), sh - 80)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 20)}")
        self.minsize(min(px(1200), sw - 40), min(px(760), sh - 80))

        # ---- theme registry ----
        self._reg: list = []          # (widget, {option: colour token})
        self.buttons: list = []
        self.hooks: list = []         # callables run after a theme change
        self.style = ttk.Style(self)
        self.reg(self, bg="BG")

        # ---- simulation state ----
        self.n = 0
        self.board: list = []
        self.final = None
        self.steps: list = []
        self.step_i = 0
        self.case_key = ""
        self.running = False
        self.after_id = None
        self.prepared_key = None
        self.focus_cells: set = set()
        self.marks: set = set()
        self.rects: list = []
        self.texts: list = []
        self.cell_font = None
        self.layout_job = None
        self.last_size = (0, 0)
        self.sweep_job = None
        self.ver: Optional[Verification] = None
        self.sq_mode = "normal"       # normal | min | max | closed
        self.zoom = 1.0               # magic-square zoom (1.0 = default size; in maximised view 1.0 = whole square fits)
        self.zoom_var = tk.StringVar(value="100%")
        self.show_text = True         # numbers are hidden when the cells are too small to read
        self.thin = False             # very small cells are drawn without borders
        self.slide_job = None         # running "slide to section" animation of the left column
        self.msg_tok, self.result_tok = "ACC", "MUTE"
        self.algo_title_text = "ALGORITHM"
        self.run_info = dict(mode="-", method="-", time="-", nodes="-")
        # ---- brute-force / compare state ----
        self.searching = False
        self.comparing = False
        self.ctl = None
        self.result_q: queue.Queue = queue.Queue()
        self.cmp_q: queue.Queue = queue.Queue()
        self.cmp_cancel = threading.Event()
        self.cmp_holder: dict = {"ctl": None}
        self.compare_data: Optional[dict] = None
        self.strategy_key = "backtracking"
        self.details_win = None
        self.popup_win = None

        # ---- tk variables ----
        self.n_var = tk.StringVar(value="5")
        self.limit_var = tk.StringVar(value="10")
        self.mode_var = tk.StringVar(value="construct")
        self.strategy_var = tk.StringVar(value=list(STRATEGIES)[0])
        self.msg_var = tk.StringVar(value="Enter the order n (3 or more) and press Start.")
        self.size_var, self.m_var = tk.StringVar(value="–"), tk.StringVar(value="–")
        self.type_var, self.method_var = tk.StringVar(value="–"), tk.StringVar(value="–")
        self.time_var, self.nodes_var = tk.StringVar(value="–"), tk.StringVar(value="–")
        self.result_var = tk.StringVar(value="Ready")
        self.step_var = tk.StringVar(value="–")

        self.apply_styles()
        self.build_ui()
        self.paint_mode()
        self.retag()
        self.refresh_buttons()
        self.n_var.trace_add("write", lambda *a: self.on_n_typed())
        self.bind("<Return>", lambda e: self.on_start())
        self.after(150, self.layout_grid)

    # ------------------------------------------------------------------ theme machinery
    def reg(self, w, **tok):
        """Create-and-remember: colours are given as token names so the theme can be switched later."""
        self._reg.append((w, tok))
        self._paint(w, tok)
        return w

    @staticmethod
    def _paint(w, tok) -> bool:
        try:
            w.configure(**{k: PAL[v] for k, v in tok.items()})
            return True
        except tk.TclError:
            return False

    def make(self, cls, parent, tok, **kw):
        return self.reg(cls(parent, **kw), **tok)

    def frm(self, parent, bg="CARD", edge=False, **kw):
        f = tk.Frame(parent, **kw)
        tok = {"bg": bg}
        if edge:
            f.configure(highlightthickness=1)
            tok.update(highlightbackground="EDGE", highlightcolor="EDGE")
        return self.reg(f, **tok)

    def lbl(self, parent, text="", fg="INK", bg="CARD", size=10, weight="normal", **kw):
        return self.reg(tk.Label(parent, text=text, font=font(size, weight), **kw), fg=fg, bg=bg)

    def button(self, parent, text, command, kind="plain", **kw):
        opts = dict(text=text, command=command, relief="flat", bd=0, padx=px(10), pady=px(5), font=font(9, "bold"),
                    cursor="hand2", highlightthickness=1, takefocus=0)
        opts.update(kw)
        b = tk.Button(parent, **opts)
        b._kind = kind
        b.bind("<Enter>", lambda e, b=b: self.restyle_button(b, True))
        b.bind("<Leave>", lambda e, b=b: self.restyle_button(b))
        self.buttons.append(b)
        self.restyle_button(b)
        return b

    def restyle_button(self, b, hover=False):
        bg, fg, hot, hotfg, edge = KINDS[b._kind]
        try:
            if str(b.cget("state")) == "disabled":
                b.configure(bg=PAL["PANEL"], fg=PAL["MUTE"], activebackground=PAL["PANEL"], activeforeground=PAL["MUTE"],
                            highlightbackground=PAL["EDGE"], disabledforeground=PAL["MUTE"], cursor="arrow")
            elif hover:
                b.configure(bg=PAL[hot], fg=PAL[hotfg], activebackground=PAL[hot], activeforeground=PAL[hotfg],
                            highlightbackground=PAL[edge], cursor="hand2")
            else:
                b.configure(bg=PAL[bg], fg=PAL[fg], activebackground=PAL[hot], activeforeground=PAL[hotfg],
                            highlightbackground=PAL[edge], disabledforeground=PAL["MUTE"], cursor="hand2")
        except tk.TclError:
            pass

    def enable(self, b, on: bool):
        b.configure(state="normal" if on else "disabled")
        self.restyle_button(b)

    def spin(self, parent, var, lo, hi, width=5, size=11):
        """Number box with ▲ ▼ buttons; the user can also just type."""
        return ttk.Spinbox(parent, from_=lo, to=hi, increment=1, width=width, textvariable=var, justify="center",
                           font=font(size, "bold"), style="App.TSpinbox")

    def apply_styles(self):
        P, st = PAL, self.style
        st.theme_use("clam")
        st.configure("TCombobox", fieldbackground=P["PANEL"], background=P["PANEL"], foreground=P["INK"],
                     arrowcolor=P["ACC"], bordercolor=P["EDGE"], lightcolor=P["PANEL"], darkcolor=P["PANEL"],
                     selectbackground=P["PANEL"], selectforeground=P["INK"], padding=px(5))
        st.map("TCombobox", fieldbackground=[("readonly", P["PANEL"]), ("disabled", P["BG"])],
               foreground=[("readonly", P["INK"]), ("disabled", P["MUTE"])],
               background=[("active", P["HOT"])], arrowcolor=[("disabled", P["MUTE"])])
        self.option_add("*TCombobox*Listbox.background", P["PANEL"])
        self.option_add("*TCombobox*Listbox.foreground", P["INK"])
        self.option_add("*TCombobox*Listbox.selectBackground", P["ACC"])
        self.option_add("*TCombobox*Listbox.selectForeground", P["ONACC"])
        self.option_add("*TCombobox*Listbox.font", font(10))
        st.configure("App.TSpinbox", fieldbackground=P["PANEL"], background=P["PANEL"], foreground=P["INK"],
                     arrowcolor=P["ACC"], bordercolor=P["EDGE"], lightcolor=P["PANEL"], darkcolor=P["PANEL"],
                     insertcolor=P["INK"], arrowsize=px(15), padding=px(5), selectbackground=P["ACC"],
                     selectforeground=P["ONACC"])
        st.map("App.TSpinbox", fieldbackground=[("disabled", P["BG"])], foreground=[("disabled", P["MUTE"])],
               background=[("active", P["HOT"])], bordercolor=[("focus", P["ACC"])])
        st.configure("App.Horizontal.TProgressbar", troughcolor=P["PANEL"], background=P["ACC"], bordercolor=P["CARD"],
                     lightcolor=P["ACC"], darkcolor=P["ACC"], thickness=px(10))
        for orient in ("Vertical", "Horizontal"):
            st.configure(f"{orient}.TScrollbar", background=P["ACC"], troughcolor=P["PANEL"], arrowcolor=P["ONACC"],
                         bordercolor=P["PANEL"], lightcolor=P["ACC"], darkcolor=P["ACC"], gripcount=0)
            st.map(f"{orient}.TScrollbar", background=[("pressed", P["ACC2"]), ("active", P["ACC2"])],
                   lightcolor=[("pressed", P["ACC2"]), ("active", P["ACC2"])],
                   darkcolor=[("pressed", P["ACC2"]), ("active", P["ACC2"])])
        st.configure("App.Horizontal.TScale", background=P["ACC"], troughcolor=P["PANEL"], bordercolor=P["PANEL"],
                     lightcolor=P["ACC"], darkcolor=P["ACC"], sliderlength=px(22), sliderthickness=px(16))
        st.map("App.Horizontal.TScale", background=[("active", P["ACC2"])], lightcolor=[("active", P["ACC2"])],
               darkcolor=[("active", P["ACC2"])])
        st.configure("Treeview", background=P["CARD"], fieldbackground=P["CARD"], foreground=P["INK"],
                     rowheight=px(26), bordercolor=P["EDGE"], lightcolor=P["CARD"], darkcolor=P["CARD"], font=font(10))
        st.configure("Treeview.Heading", background=P["PANEL"], foreground=P["ACC"], font=font(10, "bold"),
                     relief="flat", padding=px(6))
        st.map("Treeview", background=[("selected", P["ACC"])], foreground=[("selected", P["ONACC"])])
        st.map("Treeview.Heading", background=[("active", P["HOT"])])

    def retag(self):
        P = PAL
        self.algo_text.tag_configure("hl", background=P["ACC"], foreground=P["ONACC"])
        self.algo_text.tag_configure("idx", foreground=P["MUTE"])
        self.ver_text.tag_configure("ok", foreground=P["GREEN"])
        self.ver_text.tag_configure("bad", foreground=P["RED"])
        self.ver_text.tag_configure("head", foreground=P["ACC"], font=mono(10, "bold"))

    def toggle_theme(self):
        set_palette(THEME_ORDER[(THEME_ORDER.index(PAL["name"]) + 1) % len(THEME_ORDER)])
        self.apply_styles()
        self._reg = [(w, t) for w, t in self._reg if self._paint(w, t)]
        self.buttons = [b for b in self.buttons if self._alive(b)]
        for b in self.buttons:
            self.restyle_button(b)
        self.paint_mode()
        self.retag()
        self.msg_label.configure(fg=PAL[self.msg_tok])
        self.result_label.configure(fg=PAL[self.result_tok])
        self.theme_btn.configure(text=self.theme_text())
        self.layout_grid()
        self.draw_compare()
        for h in list(self.hooks):
            try:
                h()
            except tk.TclError:
                self.hooks.remove(h)

    @staticmethod
    def _alive(w) -> bool:
        try:
            return bool(w.winfo_exists())
        except tk.TclError:
            return False

    # ------------------------------------------------------------------ layout
    def build_ui(self):
        # ---- title banner (hidden while the square is maximised) ----
        self.top_head = self.frm(self, "BG")
        self.top_head.pack(fill="x", pady=(px(8), px(6)))
        self.lbl(self.top_head, f"✦   {APP_NAME}   ✦", fg="TITLE", bg="BG", size=22, weight="bold").pack()
        self.lbl(self.top_head, APP_TAGLINE, fg="MUTE", bg="BG", size=10).pack(pady=(px(2), 0))
        self.top_line = self.reg(tk.Frame(self, height=px(2)), bg="ACC")
        self.top_line.pack(fill="x")

        # ---- two halves: LEFT = controls / tools / algorithm / verification (scrolls on its own)
        #                  RIGHT = the magic square, always full height ----
        self.split = self.frm(self, "BG")
        self.split.pack(fill="both", expand=True)
        self.split.grid_columnconfigure(0, weight=1, minsize=px(560))
        self.split.grid_columnconfigure(1, weight=1, minsize=px(520))
        self.split.grid_rowconfigure(0, weight=1)

        self.leftwrap = self.frm(self.split, "BG")
        self.leftwrap.grid(row=0, column=0, sticky="nsew", padx=(px(14), px(6)), pady=(px(10), px(12)))
        self.page = self.make(tk.Canvas, self.leftwrap, dict(bg="BG"), highlightthickness=0, bd=0, yscrollincrement=px(40))
        self.page_bar = ttk.Scrollbar(self.leftwrap, orient="vertical", command=self.page.yview)
        self.page.configure(yscrollcommand=self.page_bar.set)
        self.page_bar.pack(side="right", fill="y")
        self.page.pack(side="left", fill="both", expand=True)
        self.lc = self.frm(self.page, "BG")
        self.body = self.lc                                   # the scrolled content (kept under the old name too)
        self.page_win = self.page.create_window(0, 0, window=self.lc, anchor="nw")
        self.lc.grid_columnconfigure(0, weight=1)
        self.lc.grid_rowconfigure(1, weight=1)
        self.lc_rest = self.frm(self.lc, "BG")                # stats, tools, algorithm, step, verification, comparison
        self.lc_rest.grid(row=1, column=0, sticky="nsew")

        self.rc = self.frm(self.split, "BG")                  # the magic square card lives here
        self.rc.grid(row=0, column=1, sticky="nsew", padx=(px(6), px(14)), pady=(px(10), px(12)))
        self.rc.grid_columnconfigure(0, weight=1)
        self.rc.grid_rowconfigure(0, weight=1)

        self.build_left(self.lc)       # control panel (left, top) + the square card (right)
        self.build_right(self.lc_rest)
        self.page.bind("<Configure>", lambda e: self.fit_page())
        self.lc.bind("<Configure>", lambda e: self.fit_page())
        self.bind_all("<MouseWheel>", self.on_wheel)
        for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            self.bind(seq, lambda e: self.zoom_by(1.25))
        for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.bind(seq, lambda e: self.zoom_by(1 / 1.25))
        self.bind("<Control-Key-0>", lambda e: self.set_zoom(1.0))
        self.bind("<Escape>", lambda e: self.set_square_view("normal") if self.sq_mode == "max" else None)
        self.add_tips()

    def foldable(self, card, widgets, host=None, before=None):
        """Add a ▾ / ▸ button that folds the given widgets away (and back) so a panel can be collapsed."""
        st = {"open": True, "info": {}}
        btn = tk.Label(host or card, text="▾", font=font(11, "bold"), cursor="hand2", padx=px(4))
        self.reg(btn, fg="MUTE", bg="CARD")

        def toggle(_e=None):
            if st["open"]:
                for w in widgets:
                    mgr = w.winfo_manager()
                    if mgr == "pack":
                        st["info"][w] = ("pack", w.pack_info())
                        w.pack_forget()
                    elif mgr == "grid":
                        st["info"][w] = ("grid", None)
                        w.grid_remove()
                btn.configure(text="▸")
            else:
                for w, (mgr, info) in st["info"].items():
                    if mgr == "pack":
                        info = dict(info)
                        info.pop("in", None)
                        w.pack(**info)
                    else:
                        w.grid()
                st["info"].clear()
                btn.configure(text="▾")
            st["open"] = not st["open"]
            self.after(40, self.fit_page)

        btn.bind("<Button-1>", toggle)
        if host is None:
            btn.place(relx=1.0, x=-px(6), y=px(4), anchor="ne")
        else:
            btn.pack(side="left", before=before, padx=(0, px(6)))
        Tip(self, btn, "Click to fold / unfold this panel")
        return btn

    def add_tips(self):
        for w, text in (
                (self.n_spin, "Type the order of the square or use ▲ ▼  (3 to 99)"),
                (self.limit_spin, "Longest time a brute-force search may run (seconds)"),
                (self.strategy_box, "How brute force searches: backtracking prunes, naive tries every permutation"),
                (self.btn_start, "Build the square step by step (or press Enter)"),
                (self.btn_pause, "Pause the simulation"),
                (self.btn_step, "Advance the simulation by one step"),
                (self.btn_reset, "Clear the grid and start again"),
                (self.btn_stop, "Cancel a running brute-force search or comparison"),
                (self.mode_btns["construct"], "Use the Siamese / complement / Strachey algorithm for this n"),
                (self.mode_btns["brute"], "Search for a square by trial (slow – try n = 3 or 4)"),
                (self.btn_compare, "Time the algorithm against brute force and show both results"),
                (self.theme_btn, "Theme changer: click to switch Black & Gold → Light Violet → Sage Calm"),
                (self.btn_min, "Minimise / restore the magic square"),
                (self.btn_max, "Maximise the square to the whole window (Esc to restore)"),
                (self.btn_zin, "Zoom in  (Ctrl + wheel, Ctrl +)"),
                (self.btn_zout, "Zoom out  (Ctrl + wheel, Ctrl −)"),
                (self.btn_fit, "Back to 100 %  (double-click the square or Ctrl 0)")):
            Tip(self, w, text)
    def fit_page(self):
        """Left column: as tall as its content (scrolls when the window is shorter)."""
        cw, ch = self.page.winfo_width(), self.page.winfo_height()
        if cw < 10 or ch < 10:
            return
        h = max(ch, self.lc.winfo_reqheight())
        self.page.itemconfigure(self.page_win, width=cw, height=h)
        self.page.configure(scrollregion=(0, 0, cw, h))
        if h <= ch:
            self.page.yview_moveto(0)

    def page_scroll(self, e):
        self.page.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def on_wheel(self, e):
        """Wheel anywhere on the LEFT half scrolls the left column (text boxes and tables keep their own wheel)."""
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        if w is None or w.winfo_toplevel() is not self or w.winfo_class() in ("Text", "Treeview", "Listbox"):
            return
        if str(w).startswith(str(self.leftwrap)):
            self.page_scroll(e)

    def canvas_wheel(self, e):
        """Wheel over the square: Ctrl + wheel zooms, plain wheel scrolls the square when it is bigger than its box."""
        if e.state & 0x4:
            self.zoom_by(1.15 if e.delta > 0 else 1 / 1.15)
        else:
            lo, hi = self.canvas.yview()
            if not (lo <= 0.0 and hi >= 1.0):
                self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    # ---------------- zoom of the magic square
    ZOOM_MIN, ZOOM_MAX = 0.1, 8.0

    def set_zoom(self, z):
        self.zoom = min(self.ZOOM_MAX, max(self.ZOOM_MIN, z))
        self.zoom_var.set(f"{round(self.zoom * 100)}%")
        self.schedule_layout(40)

    def zoom_by(self, factor):
        self.set_zoom(self.zoom * factor)

    def schedule_layout(self, ms=60):
        if self.layout_job:
            self.after_cancel(self.layout_job)
        self.layout_job = self.after(ms, self.layout_grid)

    # ---------------- left column: control panel + magic square
    def theme_text(self):
        return f"◐   Theme:  {THEME_LABELS[PAL['name']]}"

    def build_left(self, lc):
        pad, gap = px(12), px(8)
        sm = dict(pady=px(3), padx=px(8))             # compact buttons
        lc.grid_columnconfigure(0, weight=1)

        cp = self.frm(lc, "CARD", edge=True)
        self.cp = cp
        cp.grid(row=0, column=0, sticky="we", pady=(0, gap))
        trow = self.frm(cp, "CARD")
        trow.pack(fill="x", padx=pad, pady=(px(8), px(4)))
        self.lbl(trow, "CONTROL PANEL", fg="MUTE", size=9, weight="bold").pack(side="left")
        self.theme_btn = self.button(trow, self.theme_text(), self.toggle_theme, "plain", pady=px(3), padx=px(10), font=font(10, "bold"))
        self.theme_btn.pack(side="right")

        # row A: the three inputs
        ra = self.frm(cp, "CARD")
        ra.pack(fill="x", padx=pad, pady=(0, px(6)))
        self.lbl(ra, "Enter n", size=11, weight="bold").pack(side="left")
        self.n_spin = self.spin(ra, self.n_var, 3, MAX_N, width=4, size=12)
        self.n_spin.pack(side="left", padx=(px(6), px(4)))
        self.lbl(ra, "(3 – 99)", fg="MUTE", size=9).pack(side="left", padx=(0, px(18)))
        self.lbl(ra, "Time limit (s)", fg="MUTE").pack(side="left")
        self.limit_spin = self.spin(ra, self.limit_var, 1, 3600, width=5, size=11)
        self.limit_spin.pack(side="left", padx=(px(6), 0))
        ra2 = self.frm(cp, "CARD")
        ra2.pack(fill="x", padx=pad, pady=(0, px(6)))
        self.lbl(ra2, "Search strategy", fg="MUTE").pack(side="left")
        self.strategy_box = ttk.Combobox(ra2, values=list(STRATEGIES), state="readonly", width=24,
                                         textvariable=self.strategy_var, font=font(10))
        self.strategy_box.pack(side="left", padx=(px(6), 0), fill="x", expand=True)

        # row B: run controls + colour theme
        rb = self.frm(cp, "CARD")
        rb.pack(fill="x", padx=pad, pady=(0, px(6)))
        self.btn_start = self.button(rb, "▶  Start", self.on_start, "primary", width=8, **sm)
        self.btn_pause = self.button(rb, "⏸  Pause", self.on_pause, width=8, **sm)
        self.btn_step = self.button(rb, "⏭  Step", self.on_step, width=7, **sm)
        self.btn_reset = self.button(rb, "↺  Reset", self.on_reset, width=7, **sm)
        self.btn_stop = self.button(rb, "■  Stop search", self.on_stop, "danger", width=12, **sm)
        for b in (self.btn_start, self.btn_pause, self.btn_step, self.btn_reset, self.btn_stop):
            b.pack(side="left", padx=(0, px(5)))

        # row C: how to solve
        rc = self.frm(cp, "CARD")
        rc.pack(fill="x", padx=pad, pady=(0, px(6)))
        self.mode_btns = {
            "construct": self.button(rc, "Constructive algorithm", lambda: self.set_mode("construct"), width=18, **sm),
            "brute": self.button(rc, "Solve using brute force", lambda: self.set_mode("brute"), width=18, **sm),
        }
        for b in self.mode_btns.values():
            b.pack(side="left", padx=(0, px(5)))
        self.btn_compare = self.button(rc, "⚖  Compare both", self.on_compare, width=13, **sm)
        self.btn_compare.pack(side="left")

        self.reg(tk.Frame(cp, height=1), bg="EDGE").pack(fill="x", padx=pad)
        self.msg_label = self.lbl(cp, "", fg="ACC", size=10, weight="bold", textvariable=self.msg_var, anchor="w",
                                  justify="left", wraplength=px(700))
        self.msg_label.pack(fill="x", padx=pad, pady=(px(6), px(6)))
        cp.bind("<Configure>", lambda e: self.msg_label.configure(wraplength=max(200, e.width - 2 * pad)))

        # ---- magic square card ----
        gf = self.frm(self.rc, "CARD", edge=True)             # the square fills the whole right half, full height
        self.gf = gf
        gf.grid(row=0, column=0, sticky="nsew")
        gf.grid_columnconfigure(0, weight=1)
        gf.grid_rowconfigure(1, weight=1)
        hdr = self.frm(gf, "CARD")
        hdr.grid(row=0, column=0, sticky="we", padx=(pad, px(5)), pady=(px(5), px(3)))
        self.sq_caption = self.lbl(hdr, "MAGIC SQUARE", fg="MUTE", size=9, weight="bold")
        self.sq_caption.pack(side="left")
        wb = dict(width=4, pady=px(3), font=font(11, "bold"))
        self.button(hdr, "✕", lambda: self.set_square_view("closed"), "winclose", **wb).pack(side="right")
        self.btn_max = self.button(hdr, "□", lambda: self.set_square_view("normal" if self.sq_mode == "max" else "max"), "win", **wb)
        self.btn_max.pack(side="right", padx=px(2))
        self.btn_min = self.button(hdr, "—", lambda: self.set_square_view("normal" if self.sq_mode == "min" else "min"), "win", **wb)
        self.btn_min.pack(side="right")
        # zoom controls:  Fit  −  100%  +
        zb = dict(pady=px(3), padx=px(6), font=font(11, "bold"))
        self.btn_zin = self.button(hdr, "+", lambda: self.zoom_by(1.25), "win", width=3, **zb)
        self.btn_zin.pack(side="right", padx=(px(8), 0))
        self.lbl(hdr, "", fg="INK", size=9, weight="bold", textvariable=self.zoom_var, width=5).pack(side="right")
        self.btn_zout = self.button(hdr, "−", lambda: self.zoom_by(1 / 1.25), "win", width=3, **zb)
        self.btn_zout.pack(side="right")
        self.btn_fit = self.button(hdr, "Fit", lambda: self.set_zoom(1.0), "win", width=4, **zb)
        self.btn_fit.pack(side="right", padx=(0, px(6)))
        # info strip shown INSTEAD of the caption while the square is maximised: app name, grid size, magic sum, method
        self.maxinfo = self.frm(hdr, "CARD")
        self.lbl(self.maxinfo, APP_NAME, fg="TITLE", size=14, weight="bold").pack(side="left", padx=(0, px(18)))
        for cap, var in (("GRID SIZE", self.size_var), ("MAGIC SUM", self.m_var), ("METHOD", self.method_var)):
            self.lbl(self.maxinfo, cap, fg="MUTE", size=8, weight="bold").pack(side="left", padx=(0, px(5)))
            self.lbl(self.maxinfo, "", fg="INK", size=11, weight="bold", textvariable=var).pack(side="left", padx=(0, px(18)))

        self.sq_body = self.frm(gf, "CARD")
        self.sq_body.grid(row=1, column=0, sticky="nsew")
        sb = self.sq_body
        sb.grid_rowconfigure(0, weight=1)
        sb.grid_columnconfigure(0, weight=1)
        self.canvas = self.make(tk.Canvas, sb, dict(bg="CARD"), highlightthickness=0, height=px(430), width=px(360))
        self.vbar = ttk.Scrollbar(sb, orient="vertical", command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(sb, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="we")
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self.canvas_wheel)
        self.canvas.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(int(-e.delta / 120), "units"))
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.scan_mark(e.x, e.y))        # drag to pan
        self.canvas.bind("<B1-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<Double-Button-1>", lambda e: self.set_zoom(1.0))                  # double-click = fit
        self.progress = ttk.Progressbar(sb, style="App.Horizontal.TProgressbar", maximum=1, value=0)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="we", padx=pad, pady=(px(5), px(10)))

        # shown instead of the square after the ✕ button
        self.reopen = self.frm(self.rc, "CARD", edge=True)
        self.lbl(self.reopen, "The magic square window is closed.", fg="MUTE", size=11).pack(pady=(px(60), px(6)))
        self.button(self.reopen, "Reopen magic square", lambda: self.set_square_view("normal"), "primary").pack(pady=(0, px(60)))

    # ---------------- right column: stats, tools, algorithm, step, verification, time comparison
    def build_right(self, rc):
        pad, gap = px(12), px(8)
        rc.grid_columnconfigure(0, weight=1)

        st = self.frm(rc, "BG")
        self.stats_frame = st
        st.grid(row=0, column=0, sticky="we", pady=(0, px(4)))
        for i in range(3):
            st.grid_columnconfigure(i, weight=1, uniform="stat")
        self.stat(st, 0, 0, "GRID SIZE", self.size_var, size=12)
        self.stat(st, 0, 1, "MAGIC CONSTANT", self.m_var, size=12)
        self.stat(st, 0, 2, "ORDER TYPE", self.type_var, size=12, wrap=px(150))
        self.stat(st, 1, 0, "METHOD", self.method_var, span=2, size=12, wrap=px(330))
        self.result_label = self.stat(st, 1, 2, "RESULT", self.result_var, size=12, wrap=px(150))
        self.time_box = self.stat(st, 2, 0, "TIME TAKEN", self.time_var, size=12, readonly=True)
        self.stat(st, 2, 1, "NODES / ARRANGEMENTS", self.nodes_var, size=12, wrap=px(150))
        sp = self.stat(st, 2, 2, "SPEED", None, size=12)
        self.speed = ttk.Scale(sp, from_=1, to=100, orient="horizontal", length=px(100), style="App.Horizontal.TScale")
        self.speed.set(55)
        self.speed.pack(fill="x", padx=px(6), pady=(0, px(3)))

        tl = self.frm(self.rc, "CARD", edge=True)            # tools sit at the bottom of the magic square
        self.tools_card = tl
        tl.grid(row=1, column=0, sticky="we", pady=(px(8), 0))
        tr = self.frm(tl, "CARD")
        tr.pack(fill="x", padx=pad, pady=px(7))
        for i, (text, cmd, tip) in enumerate((
                ("Verification Details", self.on_details, "See every row, column and diagonal addition"),
                ("Export", self.on_export, "Save the square as CSV, PDF or TXT"),
                ("Benchmark", self.on_benchmark, "Time vs n table and graph for every method"),
                ("Time comparison", self.on_time_comparison, "Slide to the brute force vs algorithm section"))):
            b = self.button(tr, text, cmd, padx=px(4), pady=px(3))
            b.grid(row=0, column=i, sticky="we", padx=(0 if i == 0 else px(5), 0))
            Tip(self, b, tip)
            tr.grid_columnconfigure(i, weight=1, uniform="tool")

        # Left column, top to bottom:  CURRENT STEP, ALGORITHM, VERIFICATION, TIME COMPARISON (all listed, scrollable)
        sf = self.frm(rc, "CARD", edge=True)
        self.step_card = sf
        sf.grid(row=1, column=0, sticky="we", pady=(0, px(6)))
        self.lbl(sf, "CURRENT STEP", fg="MUTE", size=8, weight="bold").pack(anchor="w", padx=pad, pady=(px(5), 0))
        step_lbl = self.lbl(sf, "", fg="ACC", size=10, textvariable=self.step_var, anchor="w", justify="left",
                            wraplength=px(500), height=2)
        step_lbl.pack(fill="x", padx=pad, pady=(0, px(5)))
        sf.bind("<Configure>", lambda e: step_lbl.configure(wraplength=max(200, e.width - 2 * pad)))

        # small "jump to" buttons, pinned above the scrolling left column; a click slides the column to that section
        nav = self.frm(self.leftwrap, "BG")
        nav.pack(side="top", fill="x", before=self.page_bar, pady=(0, px(5)))
        self.lbl(nav, "JUMP TO", fg="MUTE", bg="BG", size=8, weight="bold").pack(side="left", padx=(2, px(8)))
        self.tab_btns = {}
        for key, text in (("algo", "Step · Algorithm"), ("verify", "Verification"), ("compare", "Time comparison")):
            b = self.button(nav, text, lambda k=key: self.select_tab(k), "plain", padx=px(8), pady=px(1), font=font(8, "bold"))
            b.pack(side="left", padx=(0, px(4)))
            self.tab_btns[key] = b

        af = self.frm(rc, "CARD", edge=True)
        self.algo_card = af
        af.grid(row=2, column=0, sticky="we", pady=(0, px(6)))
        self.algo_title = self.lbl(af, "ALGORITHM", fg="MUTE", size=9, weight="bold")
        self.algo_title.pack(anchor="w", padx=pad, pady=(px(8), px(4)))
        self.algo_text = self.make(tk.Text, af, dict(bg="CARD", fg="INK", insertbackground="CARD", selectbackground="PANEL"),
                                   relief="flat", wrap="word", font=mono(10), height=9, padx=px(4), pady=px(3),
                                   state="disabled", cursor="arrow", highlightthickness=0, bd=0, spacing1=px(2), spacing3=px(2))
        self.algo_text.pack(fill="both", expand=True, padx=(px(8), px(8)), pady=(0, px(8)))

        vf = self.frm(rc, "CARD", edge=True)
        self.ver_card = vf
        vf.grid(row=3, column=0, sticky="we", pady=(0, px(6)))
        vf.grid_columnconfigure(0, weight=1)
        vf.grid_rowconfigure(1, weight=1)
        self.lbl(vf, "VERIFICATION", fg="MUTE", size=9, weight="bold").grid(row=0, column=0, sticky="w", padx=pad, pady=(px(8), px(4)))
        self.ver_text = self.make(tk.Text, vf, dict(bg="CARD", fg="INK", insertbackground="CARD", selectbackground="PANEL"),
                                  relief="flat", wrap="none", font=mono(10), height=9, padx=px(4), pady=px(3),
                                  state="disabled", cursor="arrow", highlightthickness=0, bd=0)
        vs = ttk.Scrollbar(vf, orient="vertical", command=self.ver_text.yview)
        self.ver_text.configure(yscrollcommand=vs.set)
        self.ver_text.grid(row=1, column=0, sticky="nsew", padx=(px(8), 0), pady=(0, px(8)))
        vs.grid(row=1, column=1, sticky="ns", padx=(0, px(5)), pady=(0, px(8)))
        self.set_text(self.algo_text, "The algorithm for the chosen order n appears here.\nIt is highlighted line by line while the simulation runs.")
        self.set_text(self.ver_text, IDLE_VER)
        self.build_compare(rc, pad, gap)

    # ---------------- time comparison panel (always visible; filled by "Compare both")
    CMP_NAMES = ("Constructive algorithm", "Backtracking with pruning", "Naive permutations")

    @staticmethod
    def short_name(row):
        return "Constructive algorithm" if row["key"] == "construct" else row["name"].split("– ", 1)[-1].capitalize()

    def build_compare(self, rc, pad, gap):
        cf = self.frm(rc, "CARD", edge=True)
        self.cmp_card = cf
        cf.grid(row=4, column=0, sticky="we")
        top = self.frm(cf, "CARD")
        top.pack(fill="x", padx=pad, pady=(px(8), px(5)))
        cmp_title = self.lbl(top, "TIME COMPARISON  ·  BRUTE FORCE VS ALGORITHM", fg="MUTE", size=9, weight="bold")
        cmp_title.pack(side="left")
        self.button(top, "Download report", self.on_download_compare, "plain", pady=px(3), padx=px(6)).pack(side="right")
        self.btn_compare2 = self.button(top, "⚖  Compare both", self.on_compare, "primary", pady=px(3), padx=px(6))
        self.btn_compare2.pack(side="right", padx=(0, px(5)))
        self.cmp_canvas = self.make(tk.Canvas, cf, dict(bg="CARD"), height=px(118), highlightthickness=0)
        self.cmp_canvas.pack(fill="x", padx=px(8))
        self.cmp_canvas.bind("<Configure>", lambda e: self.draw_compare())
        tf = self.frm(cf, "CARD")
        tf.pack(fill="x", padx=pad, pady=(px(4), 0))
        self.cmp_tree = ttk.Treeview(tf, columns=("method", "time", "nodes", "status", "vs"), show="headings", height=3)
        for c, text, w, anchor in (("method", "Method", 190, "w"), ("time", "Time taken", 90, "w"), ("nodes", "Nodes", 100, "e"),
                                   ("status", "Status", 100, "w"), ("vs", "Compared with algorithm", 150, "w")):
            self.cmp_tree.heading(c, text=text)
            self.cmp_tree.column(c, width=px(w), anchor=anchor, stretch=(c == "vs"))
        self.cmp_tree.pack(fill="x")
        self.cmp_summary = self.lbl(cf, "", fg="MUTE", size=10, anchor="w", justify="left", wraplength=px(520))
        self.cmp_summary.pack(fill="x", padx=pad, pady=(px(5), px(8)))
        cf.bind("<Configure>", lambda e: self.cmp_summary.configure(wraplength=max(200, e.width - 2 * pad)))
        self.fill_compare()

    def blank_rows(self):
        return [blank_row(k) for k in ROW_KEYS]

    def record_run(self, key, seconds, nodes, status):
        """Every normal run feeds the Time Comparison panel (algorithm time shows up without pressing Compare)."""
        d = self.compare_data
        if not d or d["n"] != self.n:
            d = self.compare_data = dict(n=self.n, limit=10.0, rows=self.blank_rows(), generated=now_text())
        try:
            d["limit"] = float(self.limit_var.get())
        except ValueError:
            pass
        d["rows"][ROW_KEYS.index(key)] = dict(key=key, name=ROW_NAMES[key], seconds=seconds, nodes=nodes,
                                              status=status, valid=(status == "found"))
        d["generated"] = now_text()
        self.fill_compare()
        self.draw_compare()

    def fill_compare(self):
        t = self.cmp_tree
        t.delete(*t.get_children())
        data = self.compare_data
        rows = data["rows"] if data else self.blank_rows()
        base = rows[0]["seconds"]
        for r in rows:
            t.insert("", "end", values=(self.short_name(r), time_text(r), nodes_text(r),
                                        STATUS_TEXT.get(r["status"], r["status"]), ratio_text(r, base)))
        if data:
            self.cmp_summary.configure(text=f"Results for n = {data['n']}.  " + compare_summary(data))
        else:
            self.cmp_summary.configure(text="Nothing has run yet. Press Start – the algorithm's time appears here at once – "
                                            "or press “Compare both” to time it against brute force.")

    def draw_compare(self):
        c = self.cmp_canvas
        c.delete("all")
        rows = self.compare_data["rows"] if self.compare_data else self.blank_rows()
        w = max(c.winfo_width(), px(420))
        left, right = px(190), w - px(150)
        vals = {r["key"]: math.log10(max(r["seconds"], 1e-7)) for r in rows if r["status"] != "notrun"}
        lo = math.floor(min(vals.values())) - 1 if vals else 0
        hi = max(math.ceil(max(vals.values())) if vals else 1, lo + 1)
        for i, r in enumerate(rows):
            y = px(18) + i * px(30)
            c.create_text(px(4), y, anchor="w", fill=PAL["INK"], font=font(10, "bold"), text=self.short_name(r))
            c.create_rectangle(left, y - px(6), right, y + px(6), fill=PAL["PANEL"], outline=PAL["PANEL"])
            if r["status"] == "notrun":
                c.create_text(left + px(6), y, anchor="w", fill=PAL["MUTE"], font=font(9), text="not run yet")
                continue
            ok = r["status"] == "found"
            color = PAL["ACC"] if r["key"] == "construct" else PAL["WARN"] if ok else PAL["RED"]
            length = max(px(5), (vals[r["key"]] - lo) / (hi - lo) * (right - left))
            c.create_rectangle(left, y - px(6), left + length, y + px(6), fill=color, outline=color)
            tail = fmt_time(r["seconds"]) + ("" if ok else "  (limit)")
            c.create_text(left + length + px(5), y, anchor="w", fill=PAL["INK"], font=font(9, "bold"), text=tail)
        c.create_text(px(4), px(106), anchor="w", fill=PAL["MUTE"], font=font(8),
                      text="log scale: every step to the right is about 10× longer")

    def show_compare(self, data):
        self.compare_data = data
        self.fill_compare()
        self.draw_compare()
        self.scroll_to_compare()

    def select_tab(self, key):
        """Slide the left column to a section: algo (current step + algorithm) | verify | compare."""
        card = {"algo": self.step_card, "verify": self.ver_card, "compare": self.cmp_card}[key]
        for k, b in self.tab_btns.items():
            b._kind = "primary" if k == key else "plain"
            self.restyle_button(b)
        if self.sq_mode == "max":
            return
        self.update_idletasks()
        total = max(1, self.lc.winfo_height())
        y = card.winfo_rooty() - self.lc.winfo_rooty() - px(4)
        self.slide_to(max(0.0, y / total))
        if key == "compare":
            self.after(30, self.draw_compare)

    def slide_to(self, target):
        """Animate the left column's scroll position to `target` (0..1) with an ease-out curve."""
        if self.slide_job:
            self.after_cancel(self.slide_job)
            self.slide_job = None
        start, steps = self.page.yview()[0], 14

        def go(i):
            t = i / steps
            self.page.yview_moveto(start + (target - start) * (1 - (1 - t) ** 3))
            self.slide_job = self.after(14, lambda: go(i + 1)) if i < steps else None
        go(1)

    def scroll_to_compare(self):
        """Slides to the Time comparison section (and leaves the maximised view if needed)."""
        if self.sq_mode == "max":
            self.set_square_view("normal")
        self.select_tab("compare")

    def on_download_compare(self):
        if not self.compare_data:
            self.popup("Nothing to report yet", "Run the algorithm (Start) or press “Compare both” first, then download the report.", "warning")
            return
        self.export_compare(self.compare_data)

    def stat(self, parent, r, c, title, var, span=1, size=14, wrap=0, readonly=False):
        f = self.frm(parent, "CARD", edge=True)
        f.grid(row=r, column=c, columnspan=span, sticky="nsew", padx=px(3), pady=px(2))
        self.lbl(f, title, fg="MUTE", size=8, weight="bold").pack(anchor="w", padx=px(6), pady=(px(3), 0))
        if var is None:
            return f
        if readonly:     # the "time taken" box required by the assignment is a read-only Entry
            w = self.make(tk.Entry, f, dict(bg="CARD", fg="INK", readonlybackground="CARD", disabledbackground="CARD"),
                          textvariable=var, state="readonly", relief="flat", font=font(size, "bold"), bd=0, highlightthickness=0)
            w.pack(fill="x", padx=px(6), pady=(0, px(3)))
        else:
            w = self.lbl(f, "", size=size, weight="bold", textvariable=var, anchor="w", justify="left", wraplength=wrap or 0)
            w.pack(fill="x", padx=px(6), pady=(0, px(3)))
        return w

    # ------------------------------------------------------------------ square window buttons (— □ ✕)
    def set_square_view(self, mode):
        """normal | min | max | closed.  Max: the square takes the whole window (no banner, no left column);
        only the app name, grid size, magic sum and method stay visible, and the square can be zoomed."""
        was_max = self.sq_mode == "max"
        self.sq_mode = mode
        maxed = mode == "max"
        if mode == "closed":
            self.gf.grid_remove()
            self.reopen.grid(row=0, column=0, sticky="nsew")
        else:
            self.reopen.grid_remove()
            self.gf.grid(row=0, column=0, sticky="new" if mode == "min" else "nsew")
        if mode == "min":
            self.sq_body.grid_remove()
        else:
            self.sq_body.grid()
        if maxed:
            self.top_head.pack_forget()
            self.top_line.pack_forget()
            self.leftwrap.grid_remove()
            self.split.grid_columnconfigure(0, weight=0, minsize=0)
            self.split.grid_columnconfigure(1, weight=1, minsize=0)
            self.rc.grid_configure(padx=px(10), pady=px(10))
            self.tools_card.grid_remove()
            self.sq_caption.pack_forget()
            self.maxinfo.pack(side="left", padx=(0, px(10)))
        elif was_max:
            self.maxinfo.pack_forget()
            self.sq_caption.pack(side="left")
            self.top_head.pack(fill="x", pady=(px(8), px(6)), before=self.split)
            self.top_line.pack(fill="x", before=self.split)
            self.leftwrap.grid()
            self.split.grid_columnconfigure(0, weight=1, minsize=px(560))
            self.split.grid_columnconfigure(1, weight=1, minsize=px(520))
            self.rc.grid_configure(padx=(px(6), px(14)), pady=(px(10), px(12)))
            self.tools_card.grid()
        self.btn_min.configure(text="▭" if mode == "min" else "—")
        self.btn_max.configure(text="❐" if maxed else "□")
        if maxed or was_max:
            self.zoom = 1.0
            self.zoom_var.set("100%")
        self.after(40, self.fit_page)
        self.schedule_layout(80)

    # ------------------------------------------------------------------ small helpers
    def set_text(self, widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def set_msg(self, text, error=False):
        self.msg_var.set(text)
        self.msg_tok = "RED" if error else "ACC"
        self.msg_label.configure(fg=PAL[self.msg_tok])

    def set_result(self, text, tok):
        self.result_var.set(text)
        self.result_tok = tok
        self.result_label.configure(fg=PAL[tok])

    def popup(self, title, message, kind="error"):
        if self.popup_win is not None and self._alive(self.popup_win):
            self.popup_win.destroy()
        self.popup_win = Popup(self, title, message, kind)

    def bad(self, title, text):
        self.set_msg("⚠  " + text, error=True)
        self.set_result("Invalid input", "RED")
        self.popup(title, text, "error")
        return None

    def set_mode(self, mode):
        self.mode_var.set(mode)
        self.paint_mode()
        self.refresh_buttons()
        self.on_n_typed()

    def paint_mode(self):
        for key, b in self.mode_btns.items():
            b._kind = "primary" if self.mode_var.get() == key else "plain"
            self.restyle_button(b)

    def refresh_buttons(self):
        busy = self.searching or self.comparing
        self.strategy_box.configure(state="readonly" if self.mode_var.get() == "brute" and not busy else "disabled")
        self.n_spin.configure(state="disabled" if busy else "normal")
        self.limit_spin.configure(state="disabled" if busy else "normal")
        self.enable(self.btn_start, not busy)
        self.enable(self.btn_step, not busy)
        self.enable(self.btn_reset, True)
        self.enable(self.btn_pause, self.running)
        self.enable(self.btn_stop, busy)
        self.enable(self.btn_compare, not busy)
        self.enable(self.btn_compare2, not busy)
        for b in self.mode_btns.values():
            self.enable(b, not busy)

    def on_n_typed(self):
        """Show the case of the typed order immediately (before pressing Start)."""
        txt = self.n_var.get().strip()
        if txt.isdigit() and 3 <= int(txt) <= MAX_N and not self.running and not self.searching and not self.comparing:
            n = int(txt)
            case = classify(n)
            self.size_var.set(f"{n} × {n}")
            self.m_var.set(str(magic_constant(n)))
            self.type_var.set(CASE_TITLES[case].split(" (")[0])
            self.method_var.set(CASE_METHODS[case] if self.mode_var.get() == "construct" else "Brute-force search")

    # ------------------------------------------------------------------ input validation (pop-up messages)
    def read_n(self):
        raw = self.n_var.get().strip()
        if not raw:
            return self.bad("Order missing", "Please enter the order n first. It must be a whole number of 3 or more, "
                                             "for example 3, 4, 5 … 12.")
        try:
            n = int(raw)
        except ValueError:
            return self.bad("Not a whole number", f"“{raw}” is not a whole number. Please type digits only, for example 5.")
        if n == 2:
            return self.bad("No square of order 2", "No magic square of order 2 exists – the numbers 1 to 4 cannot give "
                                                    "equal row, column and diagonal sums. Please enter 3 or more.")
        if n == 1:
            return self.bad("Order too small", "Order 1 is the trivial square [1]. Please enter an order of 3 or more.")
        if n < 1:
            return self.bad("Order too small", f"The order must be a positive whole number. You entered {n}; please enter 3 or more.")
        if n > MAX_N:
            return self.bad("Order too large", f"The simulator supports orders up to {MAX_N}. Please enter a smaller n.")
        return n

    def read_limit(self):
        try:
            limit = float(self.limit_var.get())
            if limit <= 0:
                raise ValueError
            return limit
        except ValueError:
            return self.bad("Invalid time limit", "The time limit must be a positive number of seconds, for example 10.")

    # ------------------------------------------------------------------ grid drawing
    def on_canvas_resize(self, event):
        if (event.width, event.height) == self.last_size:
            return
        self.last_size = (event.width, event.height)
        self.schedule_layout(120)

    def layout_grid(self):
        """(Re)create the canvas items. Cells never get smaller than the size needed to show their numbers;
        if the window is too small the grid simply scrolls instead of dropping the digits."""
        self.layout_job = None
        c = self.canvas
        c.configure(bg=PAL["CARD"])
        keep = bool(self.rects)                       # keep the same centre of view when zooming
        try:
            mid = (sum(c.xview()) / 2, sum(c.yview()) / 2)
        except tk.TclError:
            mid = (0.5, 0.5)
        c.delete("all")
        self.rects, self.texts = [], []
        cw, ch = max(c.winfo_width(), px(200)), max(c.winfo_height(), px(200))
        n = self.n
        if not n:
            c.create_text(cw / 2, ch / 2, text="Enter an order n and press Start\nto watch the square being built",
                          fill=PAL["MUTE"], font=font(14), justify="center")
            c.configure(scrollregion=(0, 0, cw, ch))
            self.toggle_bars(False, False)
            return
        digits = len(str(n * n))
        fit = (min(cw, ch) - px(56)) // n
        if self.sq_mode == "max":
            base = max(3, min(fit, px(170)))          # 100 % = the whole square fits the screen, centred
        else:
            base = max(max(px(30), px(11) * digits + px(16)), min(fit, px(62)))
        cell = max(2, int(base * self.zoom))
        total, pad = cell * n, px(24)
        width, height = max(cw, total + 2 * pad), max(ch, total + 2 * pad)
        x0, y0 = (width - total) // 2, (height - total) // 2
        raw = min(int(cell * 0.40), int((cell - px(6)) / (0.66 * digits)))
        self.show_text = raw >= 6                     # too small to read -> numbers are hidden until you zoom in
        self.thin = cell < 9
        size = max(6, raw)
        self.cell_font = tkfont.Font(family=FONT[0], size=-size, weight="bold")
        c.create_rectangle(x0 - px(8), y0 - px(8), x0 + total + px(8), y0 + total + px(8), outline=PAL["ACC"],
                           width=px(2), fill=PAL["BG"])
        for r in range(n):
            rr, tt = [], []
            for col in range(n):
                xa, ya = x0 + col * cell, y0 + r * cell
                gap = 2 if cell >= 12 else 0
                rr.append(c.create_rectangle(xa + gap, ya + gap, xa + cell - gap, ya + cell - gap, fill=PAL["EMPTY"], outline=PAL["EDGE"]))
                tt.append(c.create_text(xa + cell / 2, ya + cell / 2, text="", font=self.cell_font, fill=PAL["INK"]))
            self.rects.append(rr)
            self.texts.append(tt)
        c.configure(scrollregion=(0, 0, width, height))
        self.toggle_bars(total + 2 * pad > cw, total + 2 * pad > ch)
        for r in range(n):
            for col in range(n):
                self.paint_cell(r, col)
        if keep:
            c.xview_moveto(max(0.0, mid[0] - min(1.0, cw / width) / 2))
            c.yview_moveto(max(0.0, mid[1] - min(1.0, ch / height) / 2))

    def toggle_bars(self, need_h, need_v):
        """Show the square's own scroll bars only when the grid really is bigger than its box."""
        if need_h:
            self.hbar.grid()
        else:
            self.hbar.grid_remove()
        if need_v:
            self.vbar.grid()
        else:
            self.vbar.grid_remove()

    def paint_cell(self, r, col):
        if r >= len(self.rects) or r >= len(self.board):
            return
        v = self.board[r][col]
        if v:
            fill, fg = ramp_color(v, self.n * self.n)
        else:
            fill, fg = PAL["EMPTY"], PAL["INK"]
        outline, width = PAL["EDGE"], 1
        if (r, col) in self.focus_cells:
            fill, fg, outline, width = PAL["HI"], DARK_TXT, PAL["HIOUT"], max(2, px(3))
        if (r, col) in self.marks:
            fill, fg, outline, width = PAL["MARK"], DARK_TXT, PAL["HIOUT"], max(2, px(3))
        if self.thin and (r, col) not in self.focus_cells and (r, col) not in self.marks:
            outline = fill                            # tiny cells: no border lines
        self.canvas.itemconfigure(self.rects[r][col], fill=fill, outline=outline, width=width)
        self.canvas.itemconfigure(self.texts[r][col], text=str(v) if v and self.show_text else "", fill=fg)

    def mark_cells(self, cells):
        """Outline a set of cells (used by the details window and the verification sweep)."""
        old, self.marks = self.marks, set(cells)
        for r, c in old | self.marks:
            self.paint_cell(r, c)

    # ------------------------------------------------------------------ algorithm panel
    def show_algorithm(self, key, title):
        self.case_key = key
        self.select_tab("algo")
        self.algo_title.configure(text="ALGORITHM  ·  " + title.upper())
        self.algo_text.configure(state="normal")
        self.algo_text.delete("1.0", "end")
        for i, line in enumerate(PSEUDOCODE[key]):
            self.algo_text.insert("end", f"{i + 1:>2}  ", "idx")
            self.algo_text.insert("end", line + "\n", f"l{i}")
        self.algo_text.configure(state="disabled")

    def highlight_line(self, line):
        self.algo_text.tag_remove("hl", "1.0", "end")
        if line is not None:
            self.algo_text.tag_add("hl", f"{line + 1}.4", f"{line + 1}.end")
            self.algo_text.see(f"{line + 1}.0")

    # ------------------------------------------------------------------ preparing a run
    def current_key(self):
        return (self.n_var.get().strip(), self.mode_var.get(), self.strategy_var.get())

    def new_square(self, n):
        self.cancel_animation()
        self.n = n
        self.board = [[0] * n for _ in range(n)]
        self.focus_cells, self.marks = set(), set()
        self.final, self.steps, self.step_i = None, [], 0
        self.progress.configure(value=0, maximum=1)
        case = classify(n)
        self.size_var.set(f"{n} × {n}")
        self.m_var.set(str(magic_constant(n)))
        self.type_var.set(CASE_TITLES[case].split(" (")[0])
        self.step_var.set("–")
        self.set_text(self.ver_text, IDLE_VER)
        self.time_var.set("–")
        self.nodes_var.set("–")
        self.set_result("Ready", "MUTE")
        self.layout_grid()

    def prepare(self, auto):
        n = self.read_n()
        if n is None:
            return
        if self.mode_var.get() == "brute" and self.read_limit() is None:
            return
        self.new_square(n)
        self.prepared_key = self.current_key()
        case = classify(n)
        if self.mode_var.get() == "construct":
            self.method_var.set(CASE_METHODS[case])
            self.show_algorithm(case, CASE_METHODS[case])
            reps = max(1, min(200, 200000 // (n * n)))            # average several runs: one run is only microseconds
            t0 = time.perf_counter()
            for _ in range(reps):
                construct(n)
            dt = (time.perf_counter() - t0) / reps
            self.time_var.set(f"{fmt_time(dt)}   (avg of {reps})")
            self.nodes_var.set(f"{n * n:,} cell writes")
            self.record_run("construct", dt, n * n, "found")
            self.run_info = dict(mode="Constructive algorithm", method=CASE_METHODS[case],
                                 time=f"{fmt_time(dt)} (average of {reps} runs)", nodes=f"{n * n:,} cell writes")
            self.final, self.steps = construct_with_steps(n)
            self.progress.configure(maximum=max(1, len(self.steps)), value=0)
            self.set_msg(f"{CASE_TITLES[case]}  →  {CASE_METHODS[case]}.  {len(self.steps)} simulation steps.")
            if auto:
                self.run()
        else:
            self.start_brute(n, auto)

    # ------------------------------------------------------------------ brute force (worker thread)
    def start_brute(self, n, auto):
        limit = self.read_limit()
        if limit is None:
            return
        label = self.strategy_var.get()
        self.strategy_key, func = STRATEGIES[label]
        self.method_var.set(f"Brute force – {label.lower()}")
        self.show_algorithm(self.strategy_key, label)
        self.ctl = SearchControl(limit)
        self.searching = True
        self.refresh_buttons()
        self.set_result("Searching…", "ACC")
        self.set_msg(f"Searching for a {n}×{n} magic square with “{label}” (limit {limit:g} s). "
                     f"The window stays responsive – press Stop to cancel.")
        ctl, q = self.ctl, self.result_q
        threading.Thread(target=lambda: q.put((func(n, ctl), auto)), daemon=True).start()
        self.after(100, self.poll_search)

    def poll_search(self):
        if not self.searching:
            return
        self.time_var.set(f"searching… {time.perf_counter() - self.ctl.start:.1f} s")
        self.nodes_var.set(f"{self.ctl.nodes:,}")
        try:
            res, auto = self.result_q.get_nowait()
        except queue.Empty:
            self.after(100, self.poll_search)
            return
        self.searching = False
        self.nodes_var.set(f"{res.nodes:,}")
        label = self.strategy_var.get()
        self.record_run(self.strategy_key, res.elapsed, res.nodes, res.status)
        if res.status == "found":
            self.time_var.set(fmt_time(res.elapsed))
            self.run_info = dict(mode="Brute force", method=label, time=fmt_time(res.elapsed), nodes=f"{res.nodes:,}")
            self.final = res.grid
            self.steps = replay_steps(res.grid, self.strategy_key)
            self.progress.configure(maximum=len(self.steps), value=0)
            self.set_msg(f"Found a magic square after examining {res.nodes:,} arrangements in {fmt_time(res.elapsed)}. Replaying it below.")
            self.refresh_buttons()
            if auto:
                self.run()
            return
        if res.status == "timeout":
            self.time_var.set(f"≥ {fmt_time(res.elapsed)}  (limit reached)")
            self.set_result("Limit reached", "ACC")
            msg = (f"Time limit reached after {res.nodes:,} arrangements – no square found yet. "
                   f"Try a smaller n, a longer limit, or the constructive algorithm.")
            self.set_msg(msg, error=True)
            self.popup("Time limit reached", msg, "warning")
        elif res.status == "cancelled":
            self.time_var.set(f"stopped at {fmt_time(res.elapsed)}")
            self.set_result("Stopped", "ACC")
            self.set_msg("Search stopped by the user.")
        else:
            self.set_result("Error", "RED")
            self.set_msg("The search ended without a result.", error=True)
        self.refresh_buttons()

    def on_stop(self):
        if self.searching and self.ctl:
            self.ctl.cancel.set()
        if self.comparing:
            self.cmp_cancel.set()
            if self.cmp_holder.get("ctl"):
                self.cmp_holder["ctl"].cancel.set()

    # ------------------------------------------------------------------ compare both (algorithm vs brute force)
    def on_compare(self):
        if self.searching or self.comparing:
            return
        n = self.read_n()
        if n is None:
            return
        limit = self.read_limit()
        if limit is None:
            return
        self.cancel_animation()
        self.comparing = True
        self.cmp_cancel.clear()
        self.cmp_holder = {"ctl": None}
        self.refresh_buttons()
        self.set_result("Comparing…", "ACC")
        self.time_var.set("comparing…")
        self.nodes_var.set("–")
        self.set_msg(f"Comparing the constructive algorithm with brute force for n = {n} (limit {limit:g} s per search)…")
        q, cancel, holder = self.cmp_q, self.cmp_cancel, self.cmp_holder

        def work():
            rows = run_comparison(n, limit, cancel, holder, report=lambda s: q.put(("stage", s)))
            q.put(("done", dict(n=n, limit=limit, rows=rows, generated=now_text(), cancelled=cancel.is_set())))

        threading.Thread(target=work, daemon=True).start()
        self.after(120, self.poll_compare)

    def poll_compare(self):
        if not self.comparing:
            return
        try:
            while True:
                kind, payload = self.cmp_q.get_nowait()
                if kind == "stage":
                    self.set_msg(payload)
                    continue
                self.comparing = False
                self.refresh_buttons()
                self.time_var.set("–")
                if payload["cancelled"] and len(payload["rows"]) < 3:
                    self.set_result("Stopped", "ACC")
                    self.set_msg("Comparison stopped by the user.")
                    return
                got = {r["key"]: r for r in payload["rows"]}
                payload["rows"] = [got.get(k) or blank_row(k) for k in ROW_KEYS]
                self.set_result("Compared ✓", "GREEN")
                self.time_var.set(fmt_time(payload["rows"][0]["seconds"]))
                self.nodes_var.set("see comparison")
                self.set_msg("Comparison finished – see the Time Comparison panel below. You can download the report there.")
                self.show_compare(payload)
                return
        except queue.Empty:
            pass
        self.after(120, self.poll_compare)

    def on_time_comparison(self):
        """Jump to the always-visible comparison panel."""
        self.scroll_to_compare()
        if not self.compare_data:
            self.set_msg("Nothing to compare yet – press Start, or “Compare both”.")

    # ------------------------------------------------------------------ simulation controls
    def on_start(self):
        if self.searching or self.comparing:
            return
        key = self.current_key()
        if self.prepared_key == key and self.steps:
            if self.step_i >= len(self.steps):                     # finished: replay from the start
                self.reset_display()
            self.run()
        else:
            self.prepare(auto=True)

    def on_pause(self):
        self.running = False
        self.cancel_animation(keep_state=True)
        self.refresh_buttons()
        self.set_msg("Paused. Press Start to continue or Step to advance one step.")

    def on_step(self):
        if self.searching or self.comparing:
            return
        key = self.current_key()
        if self.prepared_key != key or not self.steps:
            self.prepare(auto=False)
            if self.searching or not self.steps:
                return
        self.running = False
        self.cancel_animation(keep_state=True)
        if self.step_i >= len(self.steps):
            return
        self.apply_next()
        if self.step_i >= len(self.steps):
            self.finish_simulation()
        self.refresh_buttons()

    def on_reset(self):
        if self.searching or self.comparing:
            self.on_stop()
        self.cancel_animation()
        self.mark_cells([])
        if self.steps:
            self.reset_display()
            self.set_msg("Reset. Press Start to replay the simulation, or change n / the method.")
        else:
            if self.n:
                self.new_square(self.n)
            self.set_msg("Enter the order n (3 or more) and press Start.")
        self.refresh_buttons()

    def reset_display(self):
        self.cancel_animation()
        n = self.n
        self.board = [[0] * n for _ in range(n)]
        self.focus_cells, self.marks = set(), set()
        self.step_i = 0
        self.progress.configure(value=0)
        self.step_var.set("–")
        self.highlight_line(None)
        self.set_result("Ready", "MUTE")
        self.set_text(self.ver_text, IDLE_VER)
        for r in range(n):
            for c in range(n):
                self.paint_cell(r, c)

    def cancel_animation(self, keep_state=False):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.sweep_job:
            self.after_cancel(self.sweep_job)
            self.sweep_job = None
        if not keep_state:
            self.running = False

    def run(self):
        self.cancel_animation()
        self.running = True
        self.refresh_buttons()
        self.set_msg("Simulating… use Pause / Step / the speed slider to control it.")
        self.tick()

    def tick(self):
        if not self.running:
            return
        s = self.speed.get()
        batch = 1
        if s >= 90:
            batch = max(1, len(self.steps) // 250)
        for _ in range(batch):
            if self.step_i < len(self.steps):
                self.apply_next()
        if self.step_i >= len(self.steps):
            self.finish_simulation()
            return
        delay = int(900 * (1 - s / 100) ** 2) + 8
        self.after_id = self.after(delay, self.tick)

    def apply_next(self):
        step = self.steps[self.step_i]
        old_focus = self.focus_cells
        for r, c, v in step.changes:
            self.board[r][c] = v
        self.focus_cells = set(step.focus)
        for r, c in old_focus | self.focus_cells:
            self.paint_cell(r, c)
        self.step_i += 1
        self.progress.configure(value=self.step_i)
        self.step_var.set(f"Step {self.step_i} / {len(self.steps)}\n{step.text}")
        self.highlight_line(step.line)

    def finish_simulation(self):
        self.running = False
        old, self.focus_cells = self.focus_cells, set()
        for r, c in old:
            self.paint_cell(r, c)
        self.highlight_line(None)
        self.refresh_buttons()
        self.verify_and_show(animate=True)

    # ------------------------------------------------------------------ verification
    def verify_and_show(self, animate):
        self.ver = verify(self.board)
        v = self.ver
        self.set_msg("Square complete – checking every row, column and both diagonals…")
        self.set_result("Checking…", "ACC")
        self.set_text(self.ver_text, "")
        self.ver_line("head", f"M({v.n}) = {v.n}({v.n}²+1)/2 = {v.magic}\n\nChecking every row, column and both diagonals…\n")
        self.sweep(0, quick=(not animate or len(v.lines) > 40))

    def ver_line(self, tag, text):
        self.ver_text.configure(state="normal")
        self.ver_text.insert("end", text, tag)
        self.ver_text.configure(state="disabled")
        self.ver_text.see("end")

    def sweep(self, i, quick):
        v = self.ver
        if quick:                                   # large grids: skip the per-line animation
            i = len(v.lines)
        if i < len(v.lines):
            line = v.lines[i]
            self.mark_cells(line.cells)
            calc = " + ".join(map(str, line.values))
            shown = calc if len(calc) < 60 else calc[:57] + "…"
            self.step_var.set(f"{line.name}:  {shown} = {line.total}   {'✓' if line.ok else '✗  (should be ' + str(v.magic) + ')'}")
            delay = max(30, min(250, 3000 // len(v.lines)))
            self.sweep_job = self.after(delay, lambda: self.sweep(i + 1, False))
            return
        self.sweep_job = None
        self.mark_cells([])
        good = sum(1 for l in v.lines if l.ok)
        self.set_text(self.ver_text, "")
        self.ver_line("head", f"M({v.n}) = {v.n}({v.n}²+1)/2 = {v.magic}\n")
        if good == len(v.lines):
            self.ver_line("ok", f"✓ All {v.n} rows, {v.n} columns and both diagonals add up to {v.magic}.\n")
        else:
            self.ver_line("bad", f"✗ Only {good} of {len(v.lines)} lines add up to {v.magic}:\n")
            for l in [l for l in v.lines if not l.ok][:5]:
                self.ver_line("bad", f"    {l.name} = {l.total}\n")
        self.ver_line("ok" if v.distinct else "bad",
                      f"{'✓' if v.distinct else '✗'} Numbers 1…{v.n * v.n} each used exactly once.\n")
        self.ver_line("ok" if v.valid else "bad", "VALID MAGIC SQUARE ✓\n" if v.valid else "NOT a valid magic square ✗\n")
        self.ver_line("head", "To see every addition, press “Verification Details”.\n")
        if v.valid:
            self.set_result("Valid Magic Square ✓", "GREEN")
            self.set_msg(f"Valid magic square! All {len(v.lines)} lines add up to {v.magic}.")
        else:
            self.set_result("Validation Failed ✗", "RED")
            self.set_msg("Validation failed – at least one line does not add up to the magic constant.", error=True)
        self.step_var.set(f"Verification finished: {good}/{len(v.lines)} lines correct.")
        self.select_tab("verify")

    # ------------------------------------------------------------------ tools & reports
    def square_ready(self, what):
        """True when a finished square is on the board; otherwise explains why not with a pop-up."""
        if not self.n or not self.board or not any(any(r) for r in self.board):
            self.popup("Square not ready", f"Build a square first (press Start), then {what}.", "warning")
            return False
        if self.running or any(0 in row for row in self.board):
            self.popup("Square not finished", f"Wait until the square is complete (or press Step until it is), then {what}.", "warning")
            return False
        return True

    def on_details(self):
        if not self.square_ready("open the details"):
            return
        if self.details_win and self._alive(self.details_win):
            self.details_win.destroy()
        self.details_win = DetailsWindow(self, verify(self.board))

    def on_benchmark(self):
        BenchmarkWindow(self)

    def on_export(self):
        if not self.square_ready("export it"):
            return
        ExportDialog(self, "Export magic square", f"Choose a format for the {self.n} × {self.n} square and its sums.",
                     self.export_square)

    def ask_path(self, fmt, name):
        ext = "." + fmt
        return filedialog.asksaveasfilename(parent=self, defaultextension=ext, initialfile=name + ext,
                                            filetypes=[(fmt.upper() + " file", "*" + ext)])

    def export_square(self, fmt):
        path = self.ask_path(fmt, f"magic_square_{self.n}x{self.n}")
        if not path:
            return
        info = make_square_info(self.n, self.run_info["mode"], self.run_info["method"], self.run_info["time"], self.run_info["nodes"])
        writer = {"csv": write_square_csv, "txt": write_square_txt, "pdf": write_square_pdf}[fmt]
        try:
            writer(path, info, [row[:] for row in self.board], verify(self.board))
        except OSError as exc:
            self.popup("Could not save the file", f"{exc}", "error")
            return
        self.popup("Export complete", f"Saved {os.path.basename(path)}\n{path}", "success")

    def export_compare(self, data):
        def go(fmt):
            path = self.ask_path(fmt, f"time_comparison_n{data['n']}")
            if not path:
                return
            writer = {"csv": write_compare_csv, "txt": write_compare_txt, "pdf": write_compare_pdf}[fmt]
            try:
                writer(path, data)
            except OSError as exc:
                self.popup("Could not save the file", f"{exc}", "error")
                return
            self.popup("Report saved", f"Saved {os.path.basename(path)}\n{path}", "success")
        ExportDialog(self, "Download comparison report", f"Brute force vs algorithm for n = {data['n']}.", go)


# ==========================================================================
#  SECTION 7 - PROGRAM ENTRY POINT
# ==========================================================================

def main():
    enable_sharp_text()          # must run before the window is created
    MagicSquareApp().mainloop()


if __name__ == "__main__":
    main()









    