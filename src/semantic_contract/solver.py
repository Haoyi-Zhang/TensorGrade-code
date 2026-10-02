"""A small, unmodified-Z3 adapter using its public C API and SMT-LIB.

No solver code is vendored.  The host must provide the Z3 shared library.
Every query is reset, single threaded, and given an explicit timeout.
"""
from __future__ import annotations
import ctypes as C
import ctypes.util
from dataclasses import dataclass
from fractions import Fraction
import re
import time
from typing import Any

class SolverError(RuntimeError):
    pass

def sexprs(text: str) -> list[Any]:
    """Parse the restricted, non-string SMT value language returned here."""
    tokens = re.findall(r'\(|\)|[^\s()]+', text)
    stack: list[list[Any]] = [[]]
    for tok in tokens:
        if tok == '(':
            stack.append([])
        elif tok == ')':
            if len(stack) == 1:
                raise SolverError('unbalanced solver response')
            value = stack.pop()
            stack[-1].append(value)
        else:
            stack[-1].append(tok)
    if len(stack) != 1:
        raise SolverError('unterminated solver response')
    return stack[0]

def scalar(value: Any) -> Fraction | bool:
    if value == 'true': return True
    if value == 'false': return False
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, list) and len(value) == 2 and value[0] == '-':
        return -scalar(value[1])
    if isinstance(value, list) and len(value) == 3 and value[0] == '/':
        return scalar(value[1]) / scalar(value[2])
    raise SolverError(f'unsupported model numeral: {value!r}')

@dataclass
class Answer:
    status: str
    values: dict[str, str | bool]
    cpu_seconds: float
    wall_seconds: float
    encoding_bytes: int
    detail: str = ''

class Solver:
    """Use only from one thread; an object owns one Z3 context."""
    def __init__(self, timeout_ms: int = 1500):
        if not 1 <= timeout_ms <= 120000:
            raise ValueError('timeout must be 1..120000 ms')
        name = ctypes.util.find_library('z3')
        if name is None:
            raise SolverError('Z3 shared library not found; install the system libz3 package')
        self.lib = C.CDLL(name)
        self.timeout_ms = timeout_ms
        self.total_cpu = 0.0
        self.queries = 0
        p, b = C.c_void_p, C.c_char_p
        def bind(name, result, args):
            f = getattr(self.lib, name); f.restype = result; f.argtypes = args
            return f
        self._config = bind('Z3_mk_config', p, [])
        self._set = bind('Z3_set_param_value', None, [p,b,b])
        self._context = bind('Z3_mk_context', p, [p])
        self._del_config = bind('Z3_del_config', None, [p])
        self._delete = bind('Z3_del_context', None, [p])
        self._eval = bind('Z3_eval_smtlib2_string', b, [p,b])
        self._error_code = bind('Z3_get_error_code', C.c_uint, [p])
        self._error_msg = bind('Z3_get_error_msg', b, [p,C.c_uint])
        self._callback_type = C.CFUNCTYPE(None,p,C.c_int)
        self._callback = self._callback_type(lambda _c,_e: None)
        self._set_handler = bind('Z3_set_error_handler',None,[p,self._callback_type])
        cfg = self._config()
        self._set(cfg,b'timeout',str(timeout_ms).encode())
        self.ctx = self._context(cfg)
        self._del_config(cfg)
        self._set_handler(self.ctx,self._callback)

    def _run(self, text: str) -> str:
        if self.ctx is None:
            raise SolverError('solver has been closed')
        answer = self._eval(self.ctx,text.encode('ascii'))
        code = self._error_code(self.ctx)
        if code:
            raise SolverError(self._error_msg(self.ctx,code).decode('utf8','replace'))
        result = answer.decode('utf8','replace') if answer else ''
        if '(error' in result:
            raise SolverError(result)
        return result

    def check(self, declarations: dict[str,str], assertions: list[str],
              definitions: list[str] | None = None) -> Answer:
        for name, sort in declarations.items():
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name) or sort not in ('Int','Real','Bool'):
                raise ValueError('unsafe SMT declaration')
        text = '\n'.join([
            '(reset)', '(set-option :produce-models true)',
            f'(set-option :timeout {self.timeout_ms})', '(set-option :smt.random_seed 0)',
            *[f'(declare-const {n} {s})' for n,s in declarations.items()],
            *(definitions or []),
            *[f'(assert {a})' for a in assertions], '(check-sat)'])
        cpu, wall = time.process_time(),time.perf_counter()
        result = self._run(text).strip()
        values: dict[str,str|bool] = {}
        detail = ''
        if result == 'sat' and declarations:
            parsed = sexprs(self._run('(get-value ('+' '.join(declarations)+'))'))
            if len(parsed) != 1:
                raise SolverError('malformed model response')
            for pair in parsed[0]:
                if not isinstance(pair,list) or len(pair) != 2:
                    raise SolverError('malformed model binding')
                v = scalar(pair[1])
                values[pair[0]] = v if isinstance(v,bool) else str(v)
        elif result == 'unknown':
            detail = self._run('(get-info :reason-unknown)').strip()
        elif result != 'unsat' and result != 'sat':
            raise SolverError(f'unexpected solver result {result!r}')
        used, elapsed = time.process_time()-cpu,time.perf_counter()-wall
        self.total_cpu += used; self.queries += 1
        return Answer(result,values,used,elapsed,len(text.encode('ascii')),detail)

    def close(self) -> None:
        if self.ctx is not None:
            self._delete(self.ctx); self.ctx = None
    def __enter__(self): return self
    def __exit__(self,*_args): self.close()
