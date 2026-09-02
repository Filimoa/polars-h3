from typing import TYPE_CHECKING, TypeAlias, Union

if TYPE_CHECKING:
    import polars as pl
    from polars.datatypes import DataType, DataTypeClass

    IntoExprColumn: TypeAlias = Union[pl.Expr, str, pl.Series]
    PolarsDataType: TypeAlias = Union[DataType, DataTypeClass]
