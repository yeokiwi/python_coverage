# pycov

Statement, decision (branch), and MC/DC (Modified Condition / Decision Coverage) for Python 3.10–3.13.

`pycov` instruments Python source code at the AST level. It can run a script directly or hook into pytest, and emits text, JSON, and self-contained HTML reports.

## Install

```bash
uv sync
```

## Usage

Run a script and produce reports:

```bash
uv run pycov run examples/fizzbuzz.py 15 --report all --output build/report
```

Use with pytest:

```bash
uv run pytest --pycov --pycov-include 'src/*' --pycov-report=text,html
```

Report only (from a previous run's data directory):

```bash
uv run pycov report --input .pycov_data --report all --output build/report
```

## Coverage metrics

- **Statement**: each executable statement must execute.
- **Decision**: each boolean decision (`if`, `while`, `assert`, conditional expression, comprehension filters, `match` guards) must evaluate to both `True` and `False`.
- **MC/DC**: every condition inside a decision must be shown to independently affect the outcome. `pycov` reports both *unique-cause* and *masking* variants.
