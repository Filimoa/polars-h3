import importlib
import typing as _t

__all__ = ["Benchmark", "ParamConfig", "BenchmarkResult"]


def __getattr__(name: str) -> _t.Any:  # noqa: ANN401
    if name in __all__:
        mod = importlib.import_module(__name__ + ".engine")
        return getattr(mod, name)
    raise AttributeError(name)
