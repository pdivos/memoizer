import pandas as pd
from .core import NodeId
from .caches import AbstractCache
from .context import MemoizerContext
from .html_templates import render_html
from .context import current_asof
import io
from typing import Callable
from enum import Enum
Endpoint = Enum("Endpoint", ["eval", "latest", "download_csv"])

def construct_url(f: Callable, *args, **kwargs) -> str:
    return _node_id_to_url(Endpoint.latest, NodeId.from_call(current_asof(), f, *args, **kwargs))

def construct_download_csv_url(f: Callable, *args, **kwargs) -> str:
    return _node_id_to_url(Endpoint.download_csv, NodeId.from_call(current_asof(), f, *args, **kwargs))

def _node_id_to_url(endpoint: Endpoint, node_id: NodeId) -> str:
    assert type(node_id) is NodeId
    if endpoint == Endpoint.latest:
        call_id, _ = node_id.to_call_id_and_asof()
        query_string = call_id.to_query_string()
    else:
        query_string = node_id.to_query_string()
    return f"/{endpoint.name}?{query_string}"

def handle_eval(cache: AbstractCache, node_id: NodeId) -> str:
    _eval(cache, node_id)
    metadata = cache.read_metadata(node_id)
    res = cache.read_result(node_id)
    html = render_html(res, metadata, lambda node_id: _node_id_to_url(Endpoint.eval, node_id), lambda node_id: _node_id_to_url(Endpoint.download_csv, node_id))
    return html

def handle_download_csv(cache: AbstractCache, node_id: NodeId) -> str:
    _eval(cache, node_id)
    df = cache.read_result(node_id)
    assert type(df) is pd.DataFrame
    bytes_io = io.BytesIO()
    df.to_csv(bytes_io)
    bytes_io.seek(0)
    call_id, _ = node_id.to_call_id_and_asof()
    fname = call_id.to_fname() + '.csv'
    return fname, bytes_io

def _eval(cache: AbstractCache, node_id: NodeId) -> NodeId:
    call_id, asof = node_id.to_call_id_and_asof()
    if not cache.contains(node_id):
        with MemoizerContext(cache=cache, asof=asof):
            f, args, kwargs = call_id.to_call()
            f(*args, **kwargs)