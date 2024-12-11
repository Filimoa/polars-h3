"""
Utility script to benchmark the performance of the H3 Polars extension.

- If you know how to make any of these other libraries more performant, please open a PR. I want to be as fair as possible.
- I'm not an expert in DuckDB, but copying the data should be 0 cost due to Apache Arrow?
- I used `h3==4.1.2`, `polars==1.8.2` and `duckdb==1.1.3`.
- Attempted to also benchmark H3-Pandas, but project appears to be abandoned and doesn't work with h3 >= 4.0.0.
"""

import random
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

import duckdb
import h3
import polars as pl

import polars_h3 as plh3

random.seed(42)

Library = Literal["plh3", "duckdb", "h3_py", "h3ronpy", "h3pandas"]
Difficulty = Literal[
    "basic",  # Simple operations like conversions
    "medium",  # Operations involving some computation
    "complex",  # Operations that are particularly expensive
]


@dataclass
class BenchmarkResult:
    library: Library
    name: str
    avg_seconds: float
    num_rows: int
    num_iterations: int
    std_seconds: float = 0.0

    @property
    def num_rows_human(self) -> str:
        if self.num_rows < 1_000:
            return f"{self.num_rows:,}"
        elif self.num_rows < 1_000_000:
            return f"{self.num_rows / 1_000:,.0f}K"
        else:
            return f"{self.num_rows / 1_000_000:,.0f}M"

    def __repr__(self) -> str:
        if self.num_iterations == 0:
            return f"{self.library}::{self.name}::{self.num_rows_human} = {self.avg_seconds:.2f}s"
        else:
            return f"{self.library}::{self.name}::{self.num_rows_human} = {self.avg_seconds:.2f}s ± {self.std_seconds:.2f}s"


@dataclass
class ParamConfig:
    num_iterations: int
    resolution: int
    grid_ring_distance: int
    libraries: list[Library] | Literal["all"] = "all"
    functions: list[str] | Literal["all"] = "all"
    difficulty_to_num_rows: dict[Difficulty, int] = field(
        default_factory=lambda: {
            "basic": 10_000,
            "medium": 1_000,
            "complex": 1_000,
        }
    )
    verbose: bool = False

    @property
    def max_num_rows(self) -> int:
        return max(self.difficulty_to_num_rows.values())


def generate_points_within_bbox(
    n: int, min_lat: float, max_lat: float, min_lon: float, max_lon: float
) -> list[tuple[float, float]]:
    points = []
    while len(points) < n:
        lat = min_lat + random.random() * (max_lat - min_lat)
        lon = min_lon + random.random() * (max_lon - min_lon)
        points.append((lat, lon))
    return points


def generate_test_data(n: int, resolution: int) -> pl.DataFrame:
    """
    Generate test data for benchmarking, constrained to points within Ohio.
    """
    ohio_bbox = {
        "min_lat": 38.403,
        "max_lat": 41.978,
        "min_lon": -84.820,
        "max_lon": -80.518,
    }
    points = generate_points_within_bbox(
        n,
        ohio_bbox["min_lat"],
        ohio_bbox["max_lat"],
        ohio_bbox["min_lon"],
        ohio_bbox["max_lon"],
    )
    lats, lons = zip(*points)
    return (
        pl.DataFrame({"lat": lats, "lon": lons})
        .with_columns(int_h3_cell=plh3.latlng_to_cell("lat", "lon", resolution))
        .with_columns(str_h3_cell=plh3.int_to_str("int_h3_cell"))
        .with_columns(
            [
                pl.col("int_h3_cell").shift(-1).alias("int_h3_cell_end"),
                pl.col("str_h3_cell").shift(-1).alias("str_h3_cell_end"),
            ]
        )
        .drop_nulls()
    )


class Benchmark:
    def __init__(self, config: ParamConfig):
        con = duckdb.connect()
        con.execute("INSTALL h3 FROM community;")
        con.execute("LOAD h3;")
        self.con = con

        self.config = config

        self.function_configs = {
            "latlng_to_cell": {
                "category": "basic",
                "funcs": {
                    "plh3": self._get_hex_ids_plh3,
                    "duckdb": self._get_hex_ids_duckdb,
                    "h3_py": self._get_hex_ids_h3_py,
                },
            },
            "cell_to_latlng": {
                "category": "basic",
                "funcs": {
                    "plh3": self._cell_to_latlng_plh3,
                    "duckdb": self._cell_to_latlng_duckdb,
                    "h3_py": self._cell_to_latlng_h3_py,
                },
            },
            "get_resolution": {
                "category": "basic",
                "funcs": {
                    "plh3": self._get_resolution_plh3,
                    "duckdb": self._get_resolution_duckdb,
                    "h3_py": self._get_resolution_h3_py,
                },
            },
            "int_hex_to_str": {
                "category": "basic",
                "funcs": {
                    "plh3": self._int_hex_to_str_plh3,
                    "duckdb": self._int_hex_to_str_duckdb,
                    "h3_py": self._int_hex_to_str_h3_py,
                },
            },
            "str_hex_to_int": {
                "category": "basic",
                "funcs": {
                    "plh3": self._str_hex_to_int_plh3,
                    "duckdb": self._str_hex_to_int_duckdb,
                    "h3_py": self._str_hex_to_int_h3_py,
                },
            },
            "is_valid_cell": {
                "category": "basic",
                "funcs": {
                    "plh3": self._is_valid_cell_plh3,
                    "duckdb": self._is_valid_cell_duckdb,
                    "h3_py": self._is_valid_cell_h3_py,
                },
            },
            "are_neighbor_cells": {
                "category": "basic",
                "funcs": {
                    "plh3": self._are_neighbor_cells_plh3,
                    "duckdb": self._are_neighbor_cells_duckdb,
                    "h3_py": self._are_neighbor_cells_h3_py,
                },
            },
            "cell_to_parent": {
                "category": "medium",
                "funcs": {
                    "plh3": self._cell_to_parent_plh3,
                    "duckdb": self._cell_to_parent_duckdb,
                    "h3_py": self._cell_to_parent_h3_py,
                },
            },
            "cell_to_children": {
                "category": "medium",
                "funcs": {
                    "plh3": self._cell_to_children_plh3,
                    "duckdb": self._cell_to_children_duckdb,
                    "h3_py": self._cell_to_children_h3_py,
                },
            },
            "grid_disk": {
                "category": "medium",
                "funcs": {
                    "plh3": self._grid_disk_plh3,
                    "duckdb": self._grid_disk_duckdb,
                    "h3_py": self._grid_disk_h3_py,
                },
            },
            "grid_ring": {
                "category": "medium",
                "funcs": {
                    "plh3": self._get_grind_ring_plh3,
                    "duckdb": self._get_grid_ring_duckdb,
                    "h3_py": self._get_grid_ring_py_h3,
                },
            },
            "grid_path": {
                "category": "complex",
                "funcs": {
                    "plh3": self._get_grid_paths_plh3,
                    "duckdb": self._get_grid_paths_duckdb,
                    "h3_py": self._get_grid_paths_py_h3,
                },
            },
            "grid_distance": {
                "category": "medium",
                "funcs": {
                    "plh3": self._grid_distance_plh3,
                    "duckdb": self._grid_distance_duckdb,
                    "h3_py": self._grid_distance_h3_py,
                },
            },
            "cell_to_boundary": {
                "category": "basic",
                "funcs": {
                    "plh3": self._cell_to_boundary_plh3,
                    "duckdb": self._cell_to_boundary_duckdb,
                    "h3_py": self._cell_to_boundary_h3_py,
                },
            },
        }

    def run_all(
        self,
    ) -> list[BenchmarkResult]:
        """
        Run benchmarks for specified functions.

        Args:
            function_names: List of function names to benchmark or "all"
        """
        results = []

        # Filter functions to run
        functions_to_run = (
            self.function_configs.items()
            if self.config.functions == "all"
            else {
                k: v
                for k, v in self.function_configs.items()
                if k in self.config.functions
            }.items()
        )

        df = generate_test_data(self.config.max_num_rows, self.config.resolution)
        for func_name, config in functions_to_run:
            print(f"\n========== {func_name} ==========\n")

            num_rows = self.config.difficulty_to_num_rows[config["category"]]

            libraries = (
                config["funcs"].keys()
                if self.config.libraries == "all"
                else [lib for lib in self.config.libraries if lib in config["funcs"]]
            )

            for library in libraries:
                func = config["funcs"][library]

                perf_times = []
                for _ in range(self.config.num_iterations):
                    start = time.perf_counter()
                    result_df = func(df.head(num_rows))
                    perf_times.append(time.perf_counter() - start)

                if self.config.verbose:
                    print(f"Library: {library}")
                    print(f"Function: {func_name}")
                    print(result_df.select("result").head(1))

                results.append(
                    BenchmarkResult(
                        name=func_name,
                        library=library,  # type: ignore
                        avg_seconds=statistics.mean(perf_times),
                        std_seconds=statistics.stdev(perf_times)
                        if len(perf_times) > 1
                        else 0,
                        num_rows=num_rows,
                        num_iterations=self.config.num_iterations,
                    )
                )
            print("done...")

        return results

    #########################
    ### LATLNG TO HEX IDS ###
    #########################

    def _get_hex_ids_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            result=plh3.latlng_to_cell("lat", "lon", self.config.resolution)
        )

    def _get_hex_ids_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            f"SELECT h3_latlng_to_cell(lat, lon, {self.config.resolution}) as result FROM df;"
        ).pl()

    def _get_hex_ids_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["lat", "lon"])
            .map_elements(
                lambda row: h3.latlng_to_cell(
                    row["lat"], row["lon"], self.config.resolution
                ),
                return_dtype=pl.Utf8,
            )
            .alias("result")
        )

    #####################
    ### IS VALID CELL ###
    #####################

    def _is_valid_cell_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(plh3.is_valid_cell("int_h3_cell").alias("result"))

    def _is_valid_cell_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_is_valid_cell(int_h3_cell) as result FROM df;"
        ).pl()

    def _is_valid_cell_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.is_valid_cell(row["str_h3_cell"]),
                return_dtype=pl.Boolean,
            )
            .alias("result")
        )

    ############################
    ### STRING HEX IDS TO INT ###
    ############################

    def _str_hex_to_int_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(plh3.str_to_int("str_h3_cell").alias("result"))

    def _str_hex_to_int_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_string_to_h3(str_h3_cell) as result FROM df;"
        ).pl()

    def _str_hex_to_int_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.str_to_int(row["str_h3_cell"]), return_dtype=pl.UInt64
            )
            .alias("result")
        )

    ############################
    ### INT HEX ID TO STRING ###
    ############################

    def _int_hex_to_str_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(plh3.int_to_str("int_h3_cell").alias("result"))

    def _int_hex_to_str_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_h3_to_string(int_h3_cell) as result FROM df;"
        ).pl()

    def _int_hex_to_str_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["int_h3_cell"])
            .map_elements(
                lambda row: h3.int_to_str(row["int_h3_cell"]),
                return_dtype=pl.Utf8,
            )
            .alias("result")
        )

    ######################
    ### CELL TO LATLNG ###
    ######################

    def _cell_to_latlng_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(plh3.cell_to_latlng("int_h3_cell").alias("result"))

    def _cell_to_latlng_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_cell_to_latlng(int_h3_cell) as result FROM df;"
        ).pl()

    def _cell_to_latlng_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.cell_to_latlng(row["str_h3_cell"]),
                return_dtype=pl.List(pl.Float64),
            )
            .alias("result")
        )

    ######################
    ### HEX RESOLUTION ###
    ######################

    def _get_resolution_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(plh3.get_resolution("int_h3_cell").alias("result"))

    def _get_resolution_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_get_resolution(int_h3_cell) as result FROM df;"
        ).pl()

    def _get_resolution_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.get_resolution(row["str_h3_cell"]),
                return_dtype=pl.UInt32,
            )
            .alias("result")
        )

    ######################
    ### CELL TO PARENT ###
    ######################

    def _cell_to_parent_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            plh3.cell_to_parent("int_h3_cell", self.config.resolution).alias("result")
        )

    def _cell_to_parent_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            f"SELECT h3_cell_to_parent(int_h3_cell, {self.config.resolution}) as result FROM df;"
        ).pl()

    def _cell_to_parent_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.cell_to_parent(
                    row["str_h3_cell"], self.config.resolution
                ),
                return_dtype=pl.Utf8,
            )
            .alias("result")
        )

    ########################
    ### CELL TO CHILDREN ###
    ########################

    def _cell_to_children_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            plh3.cell_to_children("int_h3_cell", self.config.resolution + 1).alias(
                "result"
            )
        )

    def _cell_to_children_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            f"SELECT h3_cell_to_children(int_h3_cell, {self.config.resolution + 1}) as result FROM df;"
        ).pl()

    def _cell_to_children_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.cell_to_children(
                    row["str_h3_cell"], self.config.resolution + 1
                ),
                return_dtype=pl.List(pl.Utf8),
            )
            .alias("result")
        )

    #################
    ### GRID DISK ###
    #################

    def _grid_disk_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            plh3.grid_disk("int_h3_cell", self.config.grid_ring_distance).alias(
                "result"
            )
        )

    def _grid_disk_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            f"SELECT h3_grid_disk(int_h3_cell, {self.config.grid_ring_distance}) as result FROM df;"
        ).pl()

    def _grid_disk_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.grid_disk(
                    row["str_h3_cell"], self.config.grid_ring_distance
                ),
                return_dtype=pl.List(pl.Utf8),
            )
            .alias("result")
        )

    #################
    ### GRID RING ###
    #################

    # Note, if bounding boxes is too large these start to fail

    def _get_grind_ring_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            result=plh3.grid_ring("int_h3_cell", self.config.grid_ring_distance)
        )

    def _get_grid_ring_py_h3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.grid_ring(
                    row["str_h3_cell"], self.config.grid_ring_distance
                ),
                return_dtype=pl.List(pl.Utf8),
            )
            .alias("result")
        )

    def _get_grid_ring_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            f"SELECT h3_grid_ring_unsafe(int_h3_cell, {self.config.grid_ring_distance}) as result FROM df;"
        ).pl()

    #####################
    ### GRID DISTANCE ###
    #####################

    def _grid_distance_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            plh3.grid_distance("int_h3_cell", "int_h3_cell_end").alias("result")
        )

    def _grid_distance_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_grid_distance(int_h3_cell, int_h3_cell_end) as result FROM df;"
        ).pl()

    def _grid_distance_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell", "str_h3_cell_end"])
            .map_elements(
                lambda row: h3.grid_distance(
                    row["str_h3_cell"], row["str_h3_cell_end"]
                ),
                return_dtype=pl.Int64,
            )
            .alias("result")
        )

    ########################
    ### CELL TO BOUNDARY ###
    ########################

    def _cell_to_boundary_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(plh3.cell_to_boundary("int_h3_cell").alias("result"))

    def _cell_to_boundary_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_cell_to_boundary_wkt(int_h3_cell) as result FROM df;"
        ).pl()

    def _cell_to_boundary_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell"])
            .map_elements(
                lambda row: h3.cell_to_boundary(row["str_h3_cell"]),
                return_dtype=pl.List(pl.List(pl.Float64)),
            )
            .alias("result")
        )

    ##########################
    ### ARE NEIGHBOR CELLS ###
    ##########################

    def _are_neighbor_cells_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            plh3.are_neighbor_cells("int_h3_cell", "int_h3_cell_end").alias("result")
        )

    def _are_neighbor_cells_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_are_neighbor_cells(int_h3_cell, int_h3_cell_end) as result FROM df;"
        ).pl()

    def _are_neighbor_cells_h3_py(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell", "str_h3_cell_end"])
            .map_elements(
                lambda row: h3.are_neighbor_cells(
                    row["str_h3_cell"], row["str_h3_cell_end"]
                ),
                return_dtype=pl.Boolean,
            )
            .alias("result")
        )

    ##################
    ### GRID PATHS ###
    ##################

    def _get_grid_paths_plh3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            plh3.grid_path_cells("int_h3_cell", "int_h3_cell_end").alias("result")
        )

    def _get_grid_paths_duckdb(self, df: pl.DataFrame) -> pl.DataFrame:
        return self.con.execute(
            "SELECT h3_grid_path_cells(int_h3_cell, int_h3_cell_end) as result FROM df;"
        ).pl()

    def _get_grid_paths_py_h3(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.struct(["str_h3_cell", "str_h3_cell_end"])
            .map_elements(
                lambda row: h3.grid_path_cells(
                    row["str_h3_cell"], row["str_h3_cell_end"]
                ),
                return_dtype=pl.List(pl.Utf8),
            )
            .alias("result")
        )


def _pretty_print_avg_results(results: list[BenchmarkResult]):
    by_name = defaultdict(list)

    for d in results:
        by_name[d.name].append(d)

    multiples = []
    for speeds in by_name.values():
        fastest = min(v.avg_seconds for v in speeds)
        for v in speeds:
            multiples.append((v.library, v.avg_seconds / fastest))

    by_lib = defaultdict(list)
    for lib, mult in multiples:
        by_lib[lib].append(mult)

    median_by_lib = {lib: round(statistics.median(ms), 2) for lib, ms in by_lib.items()}
    avg_by_lib = {lib: round(sum(ms) / len(ms), 2) for lib, ms in by_lib.items()}

    print("\n\n======= Benchmark Final Results =======\n")
    print(f"{'Library':<10} {'Median':<8} {'Average':<8}")
    print("-" * 26)
    for lib in median_by_lib:
        print(f"{lib:<10} {median_by_lib[lib]:<8} {avg_by_lib[lib]:<8}")


if __name__ == "__main__":
    fast_factor = 1
    param_config = ParamConfig(
        resolution=9,
        grid_ring_distance=3,
        num_iterations=3,
        libraries="all",
        difficulty_to_num_rows={
            "basic": 10_000_000 // fast_factor,
            "medium": 10_000_000 // fast_factor,
            "complex": 100_000 // fast_factor,
        },
        # functions=["latlng_to_cell"],
        # verbose=True,
    )
    benchmark = Benchmark(config=param_config)
    results = benchmark.run_all()
    prev_func = None
    for result in results:
        if prev_func != result.name:
            print(f"\n{result.name} (num_iterations={param_config.num_iterations})")
            prev_func = result.name
        print(result)

    _pretty_print_avg_results(results)

    import json
    from dataclasses import asdict

    if param_config.functions == "all":
        with open("benchmarks/benchmarks-results.json", "w") as f:
            json.dump([asdict(r) for r in results], f, indent=2)
