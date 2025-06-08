import ast
import hashlib
from typing import Tuple, Callable, Dict, List
from datetime import datetime
from urllib.parse import parse_qs, urlencode
import os

_MEMOIZER_WRAPPED_ATTRIBUTE = '__memoizer_wrapped'
_FILENAME_MAX_LEN = 128
_FILENAME_ALLOWED_CHARS = ' !#$%&()+-.;=@{}~[]^_'
_QUERYSTRING_MAX_LEN = 512
is_windows = os.name == 'nt'

class CallId:
    def __init__(self, _id: str):
        assert type(_id) is str
        self.id = _id

    @staticmethod
    def from_call(f: Callable, *args, **kwargs):
        return CallId(_call_to_id(f, *args, **kwargs))
    
    def to_call(self) -> Tuple[Callable, Tuple, Dict]:
        return _call_id_to_call(self.id)
    
    def to_fname(self) -> str:
        return _call_id_to_fname(self.id)
    
    def to_query_string(self) -> str:
        query_string = urlencode({'call': self.id})
        assert len(query_string) <= _QUERYSTRING_MAX_LEN
        return query_string
    
    @staticmethod
    def from_query_string(query_string: str):
        parsed_query_string = parse_qs(query_string)
        return CallId(parsed_query_string['call'][0])
    
    def __str__(self):
        return self.id
    
    def __repr__(self):
        return f"{CallId.__name__}({repr(self.id)})"
    
    def __eq__(self, other):
        return type(other) is type(self) and other.id == self.id
    
    def __hash__(self):
        return hash(self.id)
    
class NodeId:
    def __init__(self, _id: str):
        assert type(_id) is str
        self.id = _id

    @staticmethod
    def from_call(asof: datetime, f: Callable, *args, **kwargs):
        return NodeId.from_call_id_and_asof(CallId.from_call(f, *args, **kwargs), asof)
     
    @staticmethod
    def from_call_id_and_asof(call_id: CallId, asof: datetime):
        assert type(call_id) is CallId and type(asof) is datetime
        assert asof.tzinfo is None
        return NodeId(f"{call_id.id}@{datetime_to_str(asof)}")
    
    @staticmethod
    def from_query_string(query_string: str):
        parsed_query_string = parse_qs(query_string)
        call_id = CallId(parsed_query_string['call'][0])
        asof = datetime_from_str(parsed_query_string['asof'][0])
        return NodeId.from_call_id_and_asof(call_id, asof)
    
    def to_query_string(self) -> str:
        call_id, asof = self.to_call_id_and_asof()
        query_string = urlencode({'call': call_id.id, 'asof': datetime_to_str(asof)})
        assert len(query_string) <= _QUERYSTRING_MAX_LEN
        return query_string
    
    def to_call_id_and_asof(self) -> Tuple[CallId, datetime]:
        idx = self.id.rfind('@')
        call_id = CallId(self.id[:idx])
        asof = datetime_from_str(self.id[(idx+1):])
        return (call_id, asof)
    
    def __str__(self):
        return self.id
    
    def __repr__(self):
        return f"{NodeId.__name}({self.id})"
    
    def __eq__(self, other):
        return type(other) is type(self) and self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
def assert_type(o, t):
    assert type(o) is t, [o, type(o), t]
    return o

class Metadata:
    def __init__(self, node_id: NodeId, call_id: CallId, asof: datetime, module: str, function: str, args: Tuple, kwargs: Dict, children: List[NodeId], start_time: datetime, end_time: datetime, cpu_time_sec: float, source: str, return_type: str):
        self.node_id: NodeId = assert_type(node_id, NodeId)
        self.call_id: CallId = assert_type(call_id, CallId)
        self.asof: datetime = assert_type(asof, datetime)
        self.module: str = assert_type(module, str)
        self.function: str = assert_type(function, str)
        self.args: Tuple = assert_type(args, tuple)
        self.kwargs: Dict = assert_type(kwargs, dict)
        self.children: List[NodeId] = assert_type(children, list)
        self.start_time: datetime = assert_type(start_time, datetime)
        self.end_time: datetime = assert_type(end_time, datetime)
        self.cpu_time_sec: float = assert_type(cpu_time_sec, float)
        self.source: str = assert_type(source, str)
        self.return_type: str = assert_type(return_type, str)

_datetime_fmt_ymd = lambda fmty04: f'%{"04" if fmty04 else ""}Y-%m-%d'
_datetime_fmt_ymdhms = lambda fmty04: _datetime_fmt_ymd(fmty04) + ' %H:%M:%S'
_datetime_fmt_ymdhmsm = lambda fmty04: _datetime_fmt_ymdhms(fmty04) + '.%f'

def datetime_to_str(dt: datetime) -> str:
    assert dt.tzinfo is None
    if dt.microsecond != 0: return dt.strftime(_datetime_fmt_ymdhmsm(not is_windows))
    if not (dt.second == 0 and dt.minute == 0 and dt.hour == 0): return dt.strftime(_datetime_fmt_ymdhms(not is_windows))
    return dt.strftime(_datetime_fmt_ymd(not is_windows))

def datetime_from_str(s: str) -> datetime:
    if len(s) == 10: return datetime.strptime(s, _datetime_fmt_ymd(False))
    if len(s) == 19: return datetime.strptime(s, _datetime_fmt_ymdhms(False))
    if len(s) == 26: return datetime.strptime(s, _datetime_fmt_ymdhmsm(False))
    raise Exception(f'unrecognised format: {s}')

def _call_to_id(f: Callable, *args, **kwargs) -> str:
    return f"{_f_to_str(f)}{_args_to_str(args, kwargs)}"

def _call_id_to_call(s: str) -> Tuple[Callable, Tuple, Dict]:
    module_name, func_name, args_kwargs_str = _split_to_module_func_argskwargs(s)
    f = _str_to_f(module_name, func_name)
    s = func_name + args_kwargs_str
    tree = ast.parse(s)
    assert type(tree) is ast.Module
    exprs = tree.body
    assert type(exprs) is list and len(exprs) == 1
    expr = exprs[0]
    assert type(expr) is ast.Expr
    call = expr.value
    assert type(call) is ast.Call, ast.dump(call)
    args = _parse_args(call.args)
    kwargs = _parse_kwargs(call.keywords)
    return f, args, kwargs

def _call_id_to_fname(s: str):
    from urllib.parse import quote
    s = quote(s, safe=_FILENAME_ALLOWED_CHARS)
    if len(s) > _FILENAME_MAX_LEN:
        _hash = _hex(sha256(s.encode('utf-8')))
        s = s[:(_FILENAME_MAX_LEN - len(_hash) - 1)] + '@' + _hash
    return s

def _is_memoized(f):
    assert callable(f)
    return hasattr(f, _MEMOIZER_WRAPPED_ATTRIBUTE)

def _get_wrapped(memoized):
    assert _is_memoized(memoized)
    return getattr(memoized, _MEMOIZER_WRAPPED_ATTRIBUTE)

def _set_wrapped(memoized, wrapped):
    assert not _is_memoized(memoized)
    assert callable(wrapped)
    return setattr(memoized, _MEMOIZER_WRAPPED_ATTRIBUTE, wrapped)

def _f_to_str(f):
    if _is_memoized(f):
        f = _get_wrapped(f)
    return f"{f.__module__}.{f.__name__}"

def _is_primitive(o):
    return o is None or type(o) in (bool, int, float, str, bytes)

def _obj_to_str(o):
    if _is_primitive(o):
        return repr(o)
    if type(o) is tuple:
        return f"({','.join((_obj_to_str(el) for el in o))})"
    if type(o) is list:
        return f"[{','.join((_obj_to_str(el) for el in o))}]"
    if type(o) is set:
        return '{' + ','.join(sorted(_obj_to_str(el) for el in o)) + '}'
    if type(o) is dict:
        return '{' + ','.join((f'{x[0]}:{x[1]}' for x in sorted(((_obj_to_str(k), _obj_to_str(v)) for k, v in o.items()), key = lambda x: x[0]))) + '}'
    raise Exception(f'unsupported type {type(o).__name__}')

def _args_to_str(args, kwargs):
    parts = [_obj_to_str(el) for el in args] + [f"{k}={_obj_to_str(kwargs[k])}" for k in sorted(kwargs)]
    return f"({','.join(parts)})"

def _str_to_f(module_name: str, func_name: str):
    import importlib
    module = importlib.import_module(module_name)
    fun = getattr(module, func_name)
    assert callable(fun)
    return fun

def _parse_obj(obj):
    if type(obj) is ast.Constant:
        o = obj.value
        assert _is_primitive(o)
        return o
    if type(obj) is ast.Tuple:
        return tuple((_parse_obj(el) for el in obj.elts))
    if type(obj) is ast.List:
        return [_parse_obj(el) for el in obj.elts]
    if type(obj) is ast.Set:
        return set((_parse_obj(el) for el in obj.elts))
    if type(obj) is ast.Dict:
        return dict(zip((_parse_obj(x) for x in obj.keys), (_parse_obj(x) for x in obj.values)))
    raise Exception(f"unhandled type: {type(obj).__name__}")

def _parse_args(args):
    assert type(args) is list
    return tuple([_parse_obj(arg) for arg in args])

def _parse_kwargs(keywords):
    assert type(keywords) is list
    kwargs = {}
    for kw in keywords:
        assert type(kw) is ast.keyword
        k = kw.arg
        v = _parse_obj(kw.value)
        kwargs[k] = v
    return kwargs

def _split_to_module_func_argskwargs(s):
    idx_par = s.index('(')
    module_func_str = s[:idx_par]
    idx_lastdot = module_func_str.rfind('.')
    module_name = module_func_str[:idx_lastdot]
    func_name = module_func_str[(idx_lastdot+1):]
    args_kwargs_str = s[idx_par:]
    return module_name, func_name, args_kwargs_str

def sha256(v: bytes) -> bytes:
    assert type(v) is bytes
    return hashlib.sha256(v).digest()

def _hex(v: bytes) -> str:
    assert isinstance(v, bytes)
    import binascii
    return binascii.hexlify(v).decode('utf-8')

