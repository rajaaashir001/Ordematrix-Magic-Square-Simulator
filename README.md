# Ordematrix – Magic Square Simulation and Algorithm Analysis

Data Structures and Algorithms (CSC-211) · Fall 2026 · Assignments 1 & 2
COMSATS University Islamabad – Instructor: Dr. Omer Ahmed
Prepared by: Raja Aashir Mehmood 

Ordematrix is a desktop application (Python + Tkinter) that builds magic squares of any order **n = 3 … 99**,
shows the algorithm filling the grid one number at a time, verifies the result, and compares the constructive
algorithms with two brute-force searches (naive permutations and backtracking with pruning).

## 1. Requirements

| Item | Needed |
|------|--------|
| Python | **3.10 or newer** |
| Tkinter | Included with the standard Python installer for Windows and macOS. On Debian/Ubuntu Linux: `sudo apt install python3-tk` |
| Third-party packages | **None** – only the standard library is used (`requirements.txt` is empty on purpose) |

## 2. Run

```bash
python main.py
```

(Use `py main.py` on Windows if `python` is not on your PATH.)  No installation step is needed.

Run the unit tests (no window opens):

```bash
python test_algorithms.py
```

## 3. Files

| File | Contents |
|------|----------|
| `main.py` | The Tkinter user interface only (themes, grid drawing, simulation controls, dialogs, benchmark window) |
| `algorithms.py` | Constructive algorithms (Siamese, diagonal/complement, Strachey), pseudocode text, simulation steps, verification |
| `brute_force.py` | Naive permutation search, backtracking with pruning, time-limit / cancel control, comparison helpers |
| `reports.py` | CSV, TXT and PDF writers (the PDF is written by a small built-in writer) |
| `common.py` | Application name and the time formatter |
| `test_algorithms.py` | Unit tests (55 tests) for the algorithms, searches, verification and reports |
| `requirements.txt` | Empty – no third-party packages |

## 4. How the program solves each case

| Case | Orders | Method | Time |
|------|--------|--------|------|
| Odd | 3, 5, 7, 9 … | Siamese (de la Loubère) | O(n²) |
| Doubly even (n mod 4 = 0) | 4, 8, 12 … | Diagonal / complement: fill 1…n² in reading order, replace *x* by n²+1−*x* on the diagonals of every 4×4 block | O(n²) |
| Singly even (n mod 4 = 2) | 6, 10, 14 … | Strachey: four odd squares of order n/2 with offsets 0, 2m², 3m², m² and column swaps | O(n²) |

Order 2 has no magic square and order 1 is trivial; invalid input (empty box, text, n < 1, n = 2, n > 99) shows a
pop-up message instead of crashing.

## 5. Using the application

1. Type the order **n** (or use the ▲ ▼ arrows). The grid size, magic constant, case and method appear at once.
2. Choose **Constructive algorithm** or **Solve using brute force** (then pick *Backtracking with pruning* or
   *Naive permutations* and set the **Time limit**).
3. Press **Start** (or Enter). **Pause**, **Step** and **Reset** control the simulation; the **Speed** slider changes
   how fast it runs. The cell being filled is highlighted and the matching pseudocode line is highlighted.
4. When the square is complete every row, column and both diagonals are added up and the result
   (**Valid Magic Square ✓**) is shown. The **Time taken** box (read-only, `time.perf_counter()`) and the number of
   nodes/arrangements are shown for every method.
5. Brute force runs in a worker thread, so the window stays responsive. **Stop search** cancels it, and the time
   limit ends it with the message *Limit reached*. Only n = 3 (naive) and n = 3, 4 (backtracking) finish quickly.

Other controls

* **Jump to** buttons (top of the left column): *Step · Algorithm*, *Verification*, *Time comparison* – the left
  column slides to that section. It also slides there automatically while a run progresses.
* **Compare both**: times the constructive algorithm, backtracking and naive search for the same n and fills the
  Time Comparison section (bars on a log scale + table + summary).
* Under the square: **Verification Details** (every addition), **Export** (CSV / PDF / TXT), **Benchmark**
  (time vs n table and graph, CSV export), **Time comparison**.
* Square window buttons: **—** minimise, **□** maximise (the square fills the window; only the app name, grid size,
  magic sum and method are shown), **✕** close. **Esc** leaves the maximised view.
* Zoom the square with **Fit / − / + **, **Ctrl + mouse wheel**, **Ctrl +**, **Ctrl −**, **Ctrl 0**; drag to move;
  double-click to reset. Numbers are hidden when the cells are too small to read and return when you zoom in.
* **Theme** button (top right of the Control Panel): Black & Gold → Light Violet → Sage Calm.

## 6. Known limits

* Brute force is exponential: naive search only finishes for n = 3, and backtracking finishes n = 3 and n = 4 but not
  n = 5 or n = 6 within a practical time. This is expected and is the point of the time-complexity comparison.
* The PDF writer uses the built-in PDF fonts, so `²` and `µ` appear as `^2` and `u` in exported PDFs.

## 7. AI use

AI tools were used to help write this program and are declared in `AI_LOG.md` (tools, main prompts, and what was
accepted, changed or rejected).
