# EIBO statistical core package exports. Dependencies: Python standard library and numpy/scipy/sklearn via statcore.

from .statcore import (
    TVUpperBoundResult,
    alphabet_cardinality,
    grid_cardinality,
    quantize,
    quantization_grid,
    symbol_to_id,
    tv_lower_bound,
    tv_upper_bound,
)


def __getattr__(name: str):
    """Lazily expose divisibility, which needs scipy.

    Importing it eagerly here made `from eibo import statcore` fail in any
    environment without scipy, even when only statcore was wanted.
    """
    if name == "tv_lower_bound_divisibility":
        from .divisibility import tv_lower_bound_divisibility

        return tv_lower_bound_divisibility
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "TVUpperBoundResult",
    "alphabet_cardinality",
    "grid_cardinality",
    "quantize",
    "quantization_grid",
    "symbol_to_id",
    "tv_lower_bound",
    "tv_upper_bound",
    "tv_lower_bound_divisibility",
]
