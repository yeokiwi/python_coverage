"""Collector should keep nested / threaded decision observations isolated."""
from __future__ import annotations

import textwrap
import threading

import pytest

from pycov.ast_transform import instrument
from pycov.collector import get_collector


@pytest.fixture(autouse=True)
def reset_collector():
    get_collector().reset()
    yield
    get_collector().reset()


def test_threaded_decisions_do_not_clobber():
    """Each thread's buffer stack is independent."""
    src = textwrap.dedent(
        """
        def decide(a, b):
            if a and b:
                return 1
            return 0
        """
    )
    code, meta = instrument("<threaded>", src)
    ns: dict = {}
    exec(code, ns)

    # Drive the decision from many threads, each with its own (a, b) tuple.
    # Without a per-thread buffer stack the outer observations from different
    # threads would merge and produce bogus condition tuples.
    inputs = [
        (True, True), (True, False), (False, True), (False, False),
    ] * 20
    results: list = []
    lock = threading.Lock()

    def worker(a, b):
        r = ns["decide"](a, b)
        with lock:
            results.append((a, b, r))

    threads = [threading.Thread(target=worker, args=inp) for inp in inputs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    obs = get_collector().decisions[(meta["file_id"], meta["decisions"][0]["id"])]
    # Only the four legitimate observation tuples should be present — a buffer
    # leak between threads would produce extra spurious ones.
    expected = {
        ((True, True), True),
        ((True, False), False),
        ((False, None), False),
    }
    assert obs == expected
