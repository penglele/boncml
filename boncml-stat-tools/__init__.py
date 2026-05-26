import importlib.util, sys, os
_dir = os.path.dirname(os.path.abspath(__file__))
_so = os.path.join(_dir, "__init__.cpython-311-x86_64-linux-gnu.so")
spec = importlib.util.spec_from_file_location("_init_mod", _so)
_mod = importlib.util.module_from_spec(spec)
_mod.__path__ = [_dir]
spec.loader.exec_module(_mod)
sys.modules[__name__] = _mod
globals().update({k: getattr(_mod, k) for k in dir(_mod) if not k.startswith("__")})
