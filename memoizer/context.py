from collections import namedtuple
from .caches import AbstractCache, NoOpCache
from datetime import datetime

Context = namedtuple('Context', ['cache', 'asof', 'render_html', 'render_csv'])
_default_context = Context(NoOpCache(), datetime.min, False, False)

def current_context() -> Context:
    return MemoizerContext._stack[-1]

def current_cache():
    return current_context().cache

def current_asof():
    return current_context().asof

class MemoizerContext():
    _stack = [_default_context]

    def __init__(self, cache: AbstractCache = None, asof: datetime = None, render_html: bool = None, render_csv: bool = None):
        assert isinstance(cache, AbstractCache) or cache is None
        assert type(asof) is datetime or asof is None
        assert cache is not None or asof is not None
        prev_cache, prev_asof, prev_render_html, prev_render_csv = current_context()
        self.cache = cache or prev_cache
        self.asof = asof or prev_asof
        self.render_html = render_html or prev_render_html
        self.render_csv = render_csv or prev_render_csv

    def __enter__(self):
        MemoizerContext._stack.append(Context(self.cache, self.asof, self.render_html, self.render_csv))

    def __exit__(self, type, value, traceback):
        MemoizerContext._stack.pop()
