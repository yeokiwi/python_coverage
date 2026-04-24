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
- **Python**: 3.10, 3.11, 3.12, or 3.13
- **Third-party packages**: none — `pycov` uses only the standard library
  (`ast`, `importlib.machinery`, `tokenize`, `threading`, `runpy`,
  `tomllib`/`tomli`, etc.)

### Optional
- **pytest** ≥ 7.0 — required only if you use the `--pycov` pytest plugin.
  Installed automatically with `pip install pycov[pytest]` or
  `uv sync --group dev`.

### Development
- **pytest** — self-test suite
- **nox** *(optional)* — multi-Python (3.10 – 3.13) test matrix

---

## Installation

### Using `uv` (recommended)

```bash
git clone <repo-url> pycov && cd pycov
uv sync                 # create .venv and install in editable mode
uv sync --group dev     # also install pytest for running the test suite
```

### Using `pip`

```bash
git clone <repo-url> pycov && cd pycov
python -m venv .venv && source .venv/bin/activate
pip install -e .                # runtime only
pip install -e ".[pytest]"      # with pytest integration
```

After either, the `pycov` command is on your `PATH` inside the virtualenv.

---

## Usage

### 1. Run a script under pycov

```bash
uv run pycov run examples/fizzbuzz.py 15 \
    --report text,json,html \
    --output build/report
```

`pycov run` instruments the entry script *and* every imported module that
matches the include filter, executes the target (arguments after the path
are forwarded to `sys.argv`), flushes coverage data on exit, and then
renders the requested reports. Open `build/report/index.html` to browse
the HTML output.

Equivalent module form:

```bash
uv run pycov run -m mypkg.cli -- --some-arg
```

### 2. Use with pytest

Register the plugin via `--pycov`:

```bash
uv run pytest --pycov \
    --pycov-include='src/*' \
    --pycov-report=text,html \
    --pycov-output=build/report
```

The plugin installs the import hook during `pytest_configure` and renders
the report in `pytest_sessionfinish`. `--pycov-fail-under=90` fails the
session when statement coverage drops below a threshold.

### 3. Render a report from existing data

```bash
uv run pycov report --data-dir .pycov_data \
    --output build/report \
    --report all
```

Useful when multiple processes share a `--data-dir` and you want to merge
their coverage into a single report.

### 4. Clean saved data

```bash
uv run pycov clean --data-dir .pycov_data
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

```bash
uv run pytest                   # run everything on the current Python
uv run nox -s tests             # full 3.10 – 3.13 matrix (requires nox)
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
