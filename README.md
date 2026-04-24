# pycov

**Statement, decision (branch), and MC/DC coverage for Python 3.10 – 3.13.**

`pycov` is a source-code coverage analyser that instruments Python at the
AST level. It captures three complementary metrics, runs either as a
stand-alone script runner or as a `pytest` plugin, and emits text, JSON,
and self-contained HTML reports.

---

## Coverage metrics

| Metric | What it measures |
| --- | --- |
| **Statement** | Each executable statement must execute at least once. |
| **Decision** (branch) | Each boolean decision — `if`, `while`, `assert`, conditional expression `x if c else y`, comprehension `if` filters, and `match` case guards — must evaluate to both `True` and `False`. |
| **MC/DC** | Every individual condition inside a decision must be shown to *independently* affect the outcome. `pycov` reports both *unique-cause* MC/DC (strict, DO-178B) and *masking* MC/DC (DO-178C) side-by-side. |

Probes are injected at compile time via an `ast.NodeTransformer`, so
measurement works uniformly across CPython 3.10 – 3.13 without relying on
`sys.settrace` or `sys.monitoring`.

---

## Dependencies

### Runtime
- **Python**: 3.10, 3.11, 3.12, or 3.13 — whether sourced from Anaconda /
  Miniconda or from a plain CPython install via `python -m venv`.
- **Third-party packages**: none — `pycov` uses only the standard library
  (`ast`, `importlib.machinery`, `tokenize`, `threading`, `runpy`,
  `tomllib`/`tomli`, etc.)

### Optional
- **pytest** ≥ 7.0 — required only if you use the `--pycov` pytest plugin.
  Included in both the conda `environment.yml` and the `[project.optional-dependencies].pytest` extra.

### Development
- **pytest** — self-test suite
- **nox** *(optional)* — multi-Python (3.10 – 3.13) test matrix

---

## Installation

`pycov` supports two equivalent setups — pick whichever fits your
workflow. Both install the package in editable mode so local changes are
picked up without reinstalling.

### Option A — Anaconda / Miniconda (conda environment)

If you prefer conda-managed interpreters, the repository ships an
`environment.yml` that creates a self-contained conda environment with
Python, `pytest`, and the package installed via `pip`.

1. Install **Miniconda** or the full **Anaconda** distribution from
   <https://www.anaconda.com/download> or
   <https://docs.conda.io/projects/miniconda/>.
2. Create the `pycov` environment:

   ```bash
   git clone <repo-url> pycov && cd pycov
   conda env create -f environment.yml
   ```

   This creates an environment named `pycov` using Python 3.12 by
   default (edit `environment.yml` to pick any of 3.10 – 3.13).
3. Activate it:

   ```bash
   conda activate pycov
   ```

**Update / remove:**

```bash
conda env update -f environment.yml --prune   # after environment.yml changes
conda deactivate
conda env remove -n pycov
```

### Option B — pip + `venv` (plain CPython)

If you already have a compatible CPython (3.10 – 3.13) on `PATH` and do
not want to involve conda, use the standard-library `venv` plus `pip`.

1. Create and activate a virtual environment:

   ```bash
   git clone <repo-url> pycov && cd pycov
   python -m venv .venv

   # Linux / macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```
2. Install the package in editable mode:

   ```bash
   pip install --upgrade pip
   pip install -e .                 # runtime only
   pip install -e ".[pytest]"       # also pulls in pytest (for the plugin + self-tests)
   ```

**Update / remove:**

```bash
pip install -e ".[pytest]" --upgrade     # refresh deps after a pull
deactivate
rm -rf .venv                             # Windows: rmdir /s /q .venv
```

Either option puts the `pycov` command on your `PATH` and makes
`import pycov` available inside the activated environment.

---

## Usage

All commands below assume you have activated the environment you
installed into — `conda activate pycov` for Option A, or
`source .venv/bin/activate` (Linux / macOS) /
`.venv\Scripts\Activate.ps1` (Windows) for Option B.

### 1. Run a script under pycov

```bash
pycov run --report text,json,html --output build/report \
    examples/fizzbuzz.py 15
```

`pycov run` instruments the entry script *and* every imported module that
matches the include filter, executes the target (arguments after the path
are forwarded to `sys.argv`), flushes coverage data on exit, and then
renders the requested reports. Open `build/report/index.html` to browse
the HTML output.

> **Flag ordering** — all `pycov` options (`--report`, `--output`,
> `--include`, …) must appear **before** the target script path.
> Anything after the target is forwarded to the target's own `sys.argv`.
> If your target's own arguments begin with `-`, use `--` to separate
> them: `pycov run --report html -- my_script.py --some-flag=value`.

Equivalent module form:

```bash
pycov run --report text,json,html --output build/report \
    -m mypkg.cli -- --some-arg
```

### 2. Use with pytest

Register the plugin via `--pycov`:

```bash
pytest --pycov \
    --pycov-include='src/*' \
    --pycov-report=text,html \
    --pycov-output=build/report
```

The plugin installs the import hook during `pytest_configure` and renders
the report in `pytest_sessionfinish`. `--pycov-fail-under=90` fails the
session when statement coverage drops below a threshold.

### 3. Render a report from existing data

```bash
pycov report --data-dir .pycov_data \
    --output build/report \
    --report all
```

Useful when multiple processes share a `--data-dir` and you want to merge
their coverage into a single report.

### 4. Clean saved data

```bash
pycov clean --data-dir .pycov_data
```

---

## Command-line reference

```
pycov run [options] TARGET [args...]   # instrument and run a script
pycov run [options] -m MODULE [args...]
pycov report [options]                 # render a report from saved data
pycov clean [options]                  # remove saved coverage data
```

### Common flags

| Flag | Meaning |
| --- | --- |
| `--include PATTERN` | Glob that a file must match to be instrumented. Repeatable. |
| `--exclude PATTERN` | Glob that disqualifies a file. Repeatable. `pycov` itself, `site-packages`, and `dist-packages` are always excluded. |
| `--data-dir DIR` | Where coverage data is written / read (default `.pycov_data`). |
| `--report FORMAT` | Comma-separated: `text`, `json`, `html`, or `all` (default `text`). |
| `--output DIR` | Destination for JSON / HTML output (default `pycov-report`). |
| `--fail-under N` | Exit with status 2 when statement coverage falls below `N` %. |
| `--json-include-raw` | Include the raw per-observation data in the JSON report. |

Run `pycov --help` and `pycov run --help` for the full list.

---

## Configuration file

Defaults can be set in `pyproject.toml` under `[tool.pycov]`; CLI flags
override any value found there:

```toml
[tool.pycov]
include = ["src/*"]
exclude = ["tests/*", "vendor/*"]
data-dir = ".pycov_data"
```

---

## Output formats

- **Text** — a per-file table of statements / branches / MC/DC-unique /
  MC/DC-masking, followed by collapsed ranges of missed statements and
  each missing branch or MC/DC condition.
- **JSON** (`coverage.json`) — machine-readable structured report with
  `meta`, per-file coverage, and `totals`. Add `--json-include-raw` to
  embed every recorded decision observation.
- **HTML** — `index.html` plus one page per source file. Source code is
  rendered line-by-line with green/red backgrounds for statement
  coverage, T/F chips per decision, and U*n* / M*n* chips per MC/DC
  condition with hover tooltips. Self-contained CSS, no JavaScript.

---

## Running the test suite

Inside the activated environment (conda or `venv`):

```bash
pytest                          # run everything on the environment's Python
nox -s tests                    # full 3.10 – 3.13 matrix (requires `pip install nox`)
```

The suite covers the AST transformer across every supported node kind,
short-circuit observation capture, MC/DC correctness against hand-picked
observation sets, threaded collector isolation, `pyproject.toml` loading,
CLI end-to-end runs, and the pytest plugin.

---

## Project layout

```
src/pycov/
  ast_transform.py   # NodeTransformer: injects statement + decision probes
  probes.py          # runtime probe functions called by instrumented code
  collector.py       # thread-safe coverage data collector
  importer.py        # MetaPathFinder + Loader (bypasses __pycache__/*.pyc)
  runner.py          # `pycov run` — instruments on import + runs target
  pytest_plugin.py   # pytest11 hooks
  analysis/          # statements, decisions, MC/DC (unique + masking)
  report/            # text / JSON / HTML reporters
  cli.py             # argparse-based CLI
examples/fizzbuzz.py # demo target
tests/               # unit + e2e tests
```

---

## Limitations

- Dynamic code (`eval` / `exec` of strings constructed at runtime) is not
  seen by the import hook — call `pycov.instrument_source(src, path)`
  explicitly if you need to measure it.
- `python -O` strips `assert`, so `assert` decisions become uncoverable.
- Frozen stdlib modules and C extensions are out of scope (no Python
  source to instrument).
