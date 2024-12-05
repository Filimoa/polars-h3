# File: /h3_polars/typing.py
from typing import Union

import sys
import polars as pl

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

# Remove TYPE_CHECKING condition so types are available at runtime
IntoExprColumn = Union[pl.Expr, str, pl.Series]
PolarsDataType = Union[pl.datatypes.DataType, pl.datatypes.DataTypeClass]
