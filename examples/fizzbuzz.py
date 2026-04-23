"""Tiny sample target for pycov."""
from __future__ import annotations

import sys


def classify(n: int) -> str:
    if n % 3 == 0 and n % 5 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)


def main(argv: list[str]) -> int:
    limit = int(argv[1]) if len(argv) > 1 else 15
    for i in range(1, limit + 1):
        print(classify(i))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
