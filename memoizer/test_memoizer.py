from memoizer import memoize, MemoizerContext, InMemoryCache
from memoizer.core import NodeId, CallId
import unittest
from datetime import datetime
import os

@memoize
def fib(n):
    return fib(n-1) + fib(n-2) if n > 1 else n

class Tests(unittest.TestCase):
    def test_memoizer(self):
        asof = datetime(2024, 4, 27, 12, 0, 0)
        with MemoizerContext(cache=InMemoryCache(10000)):
            fib(10)
            with MemoizerContext(asof=asof):
                fib(10)

if __name__ == "__main__":
    unittest.main(verbosity=2)