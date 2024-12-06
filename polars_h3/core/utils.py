from typing import Literal

HexResolution = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]


def _assert_valid_resolution(resolution: HexResolution) -> None:
    if resolution < 0 or resolution > 15:
        raise ValueError("Resolution must be between 0 and 15")
