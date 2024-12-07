from ._types import HexResolution


def assert_valid_resolution(resolution: HexResolution) -> None:
    if resolution < 0 or resolution > 15:
        raise ValueError("Resolution must be between 0 and 15")
