from datetime import datetime
from time import time
from memoizer.context import current_context
from memoizer.core import NodeId, CallId, Metadata, _is_memoized, _get_wrapped, _set_wrapped
from memoizer.caches import FileCache
import inspect
from typing import Callable
from functools import lru_cache

_children_stack = [set()]
_selftimes_stack = [[]]

def memoize(f):
    def memoized(*args, **kwargs):
        assert not _is_memoized(f)
        return _eval_cached(f, *args, **kwargs)
    _set_wrapped(memoized, f)
    return memoized

def blow_cache(memoized: Callable, *args, **kwargs):
    asof = current_context().asof
    f = _get_wrapped(memoized)
    node_id = NodeId.from_call(asof, f, *args, **kwargs)
    cache = current_context().cache
    if cache.contains(node_id):
        cache.remove(node_id)

def _eval_cached(f, *args, **kwargs):
    cache = current_context().cache
    asof = current_context().asof
    call_id = CallId.from_call(f, *args, **kwargs)
    node_id = NodeId.from_call_id_and_asof(call_id, asof)
    _children_stack[-1].add(node_id)
    if not cache.contains(node_id):
        _children_stack.append(set())
        _selftimes_stack.append([])

        # TODO pass in loglevel from context
        logger().info(f"eval {node_id.id}")
        res, start_time, end_time = _eval(f, *args, **kwargs)
        wall_time = end_time - start_time
        logger().info(f"done {node_id.id} in {wall_time}")

        cpu_time_sec = wall_time - sum(el[3] for el in _selftimes_stack.pop())
        children = _children_stack.pop()
        _selftimes_stack[-1].append((node_id, start_time, end_time, wall_time))
        metadata = Metadata(
            node_id,
            call_id,
            asof,
            f.__module__,
            f.__name__,
            args,
            kwargs,
            list(children),
            datetime.fromtimestamp(start_time),
            datetime.fromtimestamp(end_time),
            cpu_time_sec,
            ''.join(inspect.getsourcelines(f)[0]),
            type(res).__name__
        )
        cache.write(node_id, res, metadata)
        if current_context().render_html:
            _render_html(cache, node_id, res, metadata)
        if current_context().render_csv:
            _render_csv(cache, node_id, res, metadata)
        return res
    return cache.read_result(node_id)

def _href_eval(cache: FileCache, node_id: NodeId):
    fname = cache._fname(node_id, ".html")
    fname = fname.split('/')[-1] # this is a hack needed because Docker vs host machine full paths are different.
    fname = fname.replace("%","%25") # this replace is a hack but this is how it works
    # fname = "file:///" + fname
    return fname

def _render_html(cache, node_id, res, metadata):
    from .html_templates import render_html
    from .caches import FileCache, write_file
    if type(cache) is not FileCache: return
    href_eval = lambda node_id: _href_eval(cache, node_id)
    html = render_html(res, metadata, href_eval, lambda node_id: "")
    fname = cache._fname(node_id, ".html")
    write_file(fname, html.encode('utf-8'))

def _render_csv(cache, node_id, res, metadata):
    from .caches import FileCache, write_file
    import pandas as pd
    from .web import handle_download_csv
    if type(cache) is not FileCache or type(res) is not pd.DataFrame: return
    _, bytes_io = handle_download_csv(cache, node_id)
    content = bytes_io.getvalue()
    write_file(cache._fname(node_id, ".csv"), content)

def _eval(f, *args, **kwargs):
    start_time = time()
    res = f(*args, **kwargs)
    end_time = time()
    return res, start_time, end_time

@lru_cache
def logger():
    import logging
    logger = logging.getLogger('memoizer')
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger