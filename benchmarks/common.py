"""Shared measurement and evidence handling; no eager engine imports."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


def positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def add_controls(parser, *, rows=100_000):
    parser.add_argument("--rows", type=positive, default=rows)
    parser.add_argument("--threads", type=positive, default=8)
    parser.add_argument("--iterations", type=positive, default=5)
    parser.add_argument("--warmups", type=positive, default=2)
    parser.add_argument("--functions", nargs="+", default=["all"])
    parser.add_argument("--list", action="store_true", help="List available workloads")
    parser.add_argument("--plugin-path", type=Path, help="Saved current plugin binary")
    parser.add_argument(
        "--baseline-plugin", type=Path, help="Saved original plugin binary"
    )
    parser.add_argument(
        "--output", type=Path, help="New JSON results path (required for runs)"
    )


def configure(args, parser):
    # Must precede imports that initialize either native thread pool.
    os.environ["POLARS_MAX_THREADS"] = str(args.threads)
    os.environ["RAYON_NUM_THREADS"] = str(args.threads)
    for name in ("plugin_path", "baseline_plugin"):
        path = getattr(args, name)
        if path:
            if not path.is_file():
                parser.error(f"--{name.replace('_', '-')} must be an existing binary")
            setattr(args, name, path.resolve())
    if not args.list:
        if args.output is None:
            parser.error("--output is required for benchmark runs")
        if args.output.exists():
            parser.error("output already exists; choose a new path")


def select_cases(suite, args, parser):
    if args.list:
        print("\n".join(suite))
        return []
    names = list(suite) if args.functions == ["all"] else args.functions
    if unknown := set(names) - suite.keys():
        parser.error(f"unknown functions: {sorted(unknown)}")
    if len(set(names)) != len(names):
        parser.error("duplicate functions are not allowed")
    return names


def measure(call):
    start_cpu = time.process_time()
    start = time.perf_counter()
    output = call()
    return output, {
        "wall_seconds": time.perf_counter() - start,
        "cpu_seconds": time.process_time() - start_cpu,
    }


def collect_samples(runners, args, validate, *, prepare=None, materialize=None):
    """Rotate engines, exclude warmups, validate every output outside timing."""
    samples = {engine: [] for engine in runners}
    for iteration in range(-args.warmups, args.iterations):
        order = list(runners)
        # With two engines, rotation plus reversal would cancel each other.
        if len(order) > 2:
            shift = iteration % len(order)
            order = order[shift:] + order[:shift]
        if iteration % 2:
            order.reverse()
        for engine in order:
            if prepare:
                prepare(engine)
            gc.collect()
            output, timing = measure(runners[engine])
            if materialize:
                output = materialize(engine, output)
            validate(output)
            timing["output_chunks"] = (
                output.n_chunks()
                if hasattr(output, "n_chunks")
                else output.column(0).num_chunks
            )
            if iteration >= 0:
                samples[engine].append(timing)
            del output
    return samples


def summarize(samples, mode):
    records = []
    for engine, runs in samples.items():
        walls = [run["wall_seconds"] for run in runs]
        records.append(
            {
                "mode": mode,
                "engine": engine,
                "median_seconds": statistics.median(walls),
                "min_seconds": min(walls),
                "max_seconds": max(walls),
                "runs": runs,
            }
        )
    return records


def use_plugin(path):
    import polars_h3

    selected = path or Path(polars_h3.__file__).parent
    for module in (
        "indexing",
        "inspection",
        "traversal",
        "edge",
        "vertexes",
        "metrics",
        "geometry",
    ):
        importlib.import_module(f"polars_h3.core.{module}").LIB = selected


def metadata(args, suite, packages=()):
    import polars as pl
    from polars.plugins import _resolve_plugin_path

    import polars_h3

    binary = _resolve_plugin_path(
        args.plugin_path or Path(polars_h3.__file__).parent, use_abs_path=True
    )
    return {
        "suite": suite,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("polars", "polars-h3", *packages)
        },
        "polars_threads": pl.thread_pool_size(),
        "rayon_threads": os.environ["RAYON_NUM_THREADS"],
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], text=True),
        "binary": str(binary),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "baseline_binary_sha256": hashlib.sha256(
            args.baseline_plugin.read_bytes()
        ).hexdigest()
        if args.baseline_plugin
        else None,
        "settings": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
    }


class Report:
    """Reserve a new path and atomically checkpoint complete/failed run status."""

    def __init__(self, path, metadata):
        self.path = path
        self.data = {
            "schema_version": 2,
            "status": "running",
            "metadata": metadata,
            "cases": [],
        }

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("x") as stream:
            json.dump(self.data, stream, indent=2)
        return self

    def save(self):
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self.path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            try:
                json.dump(self.data, stream, indent=2)
                stream.write("\n")
                stream.close()
                temporary.replace(self.path)
            finally:
                temporary.unlink(missing_ok=True)

    def append(self, case):
        self.data["cases"].append(case)
        self.save()

    def __exit__(self, kind, error, traceback):
        incomplete = any(
            case.get("status", "complete") != "complete" for case in self.data["cases"]
        )
        self.data["status"] = (
            "failed" if kind else "partial" if incomplete else "complete"
        )
        if kind:
            self.data["error"] = f"{kind.__name__}: {error}"
        self.save()
