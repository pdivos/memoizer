import unittest
from datetime import datetime
from urllib.parse import quote
from memoizer.core import CallId, _obj_to_str, _parse_obj, _args_to_str, datetime_from_str, datetime_to_str
# from .memoizer import memoize

# @memoize
# def fib(n):
#     return fib(n-1) + fib(n-2) if n > 1 else n

def _test_fun():
    pass

class Tests(unittest.TestCase):
    def test_obj_parser(self):
        import ast
        test_cases = [
            (None, 'None'),
            (True, 'True'),
            (1, '1'),
            (3.14, '3.14'),
            ('hello world', "'hello world'"),
            ('hello world"', "'hello world\"'"),
            ('hello world\'', '"hello world\'"'),
            (b'bytes', "b'bytes'"),
            ((1,2,3), '(1,2,3)'),
            ([1,2,3], '[1,2,3]'),
            ({1,2,3}, '{1,2,3}'),
            ({3,2,1}, '{1,2,3}'),
            ({'a':1,'b':2}, "{'a':1,'b':2}"),
            ({'b':2,'a':1}, "{'a':1,'b':2}"),
            ({(None,3.14,('hello','world')):{'a','b'},None:[{'c','d'},{'e','f'},[1,2,[3]]]}, "{(None,3.14,('hello','world')):{'a','b'},None:[{'c','d'},{'e','f'},[1,2,[3]]]}")
        ]
        for obj, s in test_cases:
            act_obj = _parse_obj(ast.parse(s).body[0].value)
            assert obj == act_obj, [obj, act_obj]
            assert _obj_to_str(obj) == s, [_obj_to_str(obj), s]

    def test_args(self):
        test_cases = [
            ((), {}, "()"),
            ((), {'a':1, 'b':None}, "(a=1,b=None)"),
            ((), {'b':None, 'a':1}, "(a=1,b=None)"),
            (('hello', 3.14, None), {}, "('hello',3.14,None)"),
            (('hello', 3.14, None), {'A': True}, "('hello',3.14,None,A=True)"),
        ]
        for args, kwargs, s in test_cases:
            assert s == _args_to_str(args, kwargs), [s, _args_to_str(args, kwargs)]
    
    def test_call_id(self):
        test_cases = [
            ("urllib.parse.quote()", quote, (), {}),
            ("urllib.parse.quote('hello',3.14,(None,(None,False,'abc')))", quote, ('hello',3.14, (None, (None, False, "abc"))), {}),
            ("urllib.parse.quote(hello=3.14,world=None)", quote, (), {'hello' :3.14, 'world' :None}),
            ("urllib.parse.quote('hello',3.14,(None,(None,False,'abc')),hello=3.14,world=None)", quote, ('hello',3.14, (None, (None, False, "abc"))), {'hello': 3.14, "world": None}),
        ]
        for test_case in test_cases:
            with self.subTest(case=test_case):
                s, f, args, kwargs = test_case
                assert s == CallId.from_call(f, *args, **kwargs).id, [s, CallId.from_call(f, *args, **kwargs).id]
                assert CallId(s).to_call() == (f, args, kwargs)

    def test_call_id_unique(self):
        chrs = [chr(i) for i in range(256)]
        node_ids = []
        for c1 in chrs:
            node_ids.append(CallId.from_call(_test_fun, c1).id)
            for c2 in chrs:
                node_ids.append(CallId.from_call(_test_fun, c1 + c2).id)
                node_ids.append(CallId.from_call(_test_fun, c1, c2).id)
                node_ids.append(CallId.from_call(_test_fun, c1, c2, 3.14).id)
                node_ids.append(CallId.from_call(_test_fun, c1, c2, None).id)
                node_ids.append(CallId.from_call(_test_fun, c1, c2, larargl='hello world').id)
        assert len(node_ids) == len(set(node_ids))

    def test_datetime(self):
        test_cases = [
            (datetime(2024, 4, 26, 12, 23, 45, 123), '2024-04-26 12:23:45.000123'),
            (datetime(2024, 4, 26, 12, 23, 45, 0), '2024-04-26 12:23:45'),
            (datetime(2024, 4, 26, 12, 23, 45), '2024-04-26 12:23:45'),
            (datetime(2024, 4, 26, 0, 0, 0, 0), '2024-04-26'),
            (datetime(2024, 4, 26), '2024-04-26'),
            (datetime.min, '0001-01-01'),
        ]
        for (dt, s) in test_cases:
            assert dt == datetime_from_str(s), [dt, datetime_from_str(s)]
            assert datetime_to_str(dt) == s, [datetime_to_str(dt), s]

if __name__ == '__main__':
    unittest.main(verbosity=2)