"""Build from an extracted sdist and verify the vendored dependency and license."""

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    license_bytes = (root / "vendor/h3o/LICENSE").read_bytes()
    with tempfile.TemporaryDirectory(prefix="polars-h3-sdist-") as temporary:
        work = Path(temporary)
        subprocess.run(["maturin", "sdist", "--out", str(work)], cwd=root, check=True)
        archive = next(work.glob("*.tar.gz"))
        with tarfile.open(archive) as source:
            source.extractall(work / "source", filter="data")
        extracted = next((work / "source").iterdir())
        assert (extracted / "vendor/h3o/LICENSE").read_bytes() == license_bytes
        for directory in ("src", "vendor/h3o/src"):
            for source in (root / directory).rglob("*.rs"):
                relative = source.relative_to(root)
                assert (
                    (extracted / relative).read_bytes() == source.read_bytes()
                ), f"sdist source differs: {relative}"
        for relative in (
            "fuzz/Cargo.toml",
            "fuzz/Cargo.lock",
            "fuzz/fuzz_targets/latltng_to_cell.rs",
            "tests/integration_tests.rs",
            "dataset/latLngToCell.txt",
        ):
            assert (extracted / "vendor/h3o" / relative).is_file(), relative
        metadata = json.loads(
            subprocess.check_output(
                ["cargo", "metadata", "--locked", "--format-version", "1"],
                cwd=extracted,
            )
        )
        h3o = [package for package in metadata["packages"] if package["name"] == "h3o"]
        assert len(h3o) == 1 and h3o[0]["source"] is None
        assert (
            Path(h3o[0]["manifest_path"]).resolve().is_relative_to(extracted.resolve())
        )
        # Reuse compiled third-party dependencies, but force these two crates
        # to rebuild. Normalized archive mtimes can otherwise allow Cargo to
        # reuse an earlier package build despite changed source contents.
        env = {**os.environ, "CARGO_TARGET_DIR": str(root / "target")}
        subprocess.run(
            ["cargo", "clean", "--package", "polars-h3", "--package", "h3o"],
            cwd=extracted,
            env=env,
            check=True,
        )
        subprocess.run(
            [
                "maturin",
                "build",
                "--locked",
                "--interpreter",
                sys.executable,
                "--out",
                str(work / "wheels"),
            ],
            cwd=extracted,
            env=env,
            check=True,
        )
        wheel = next((work / "wheels").glob("*.whl"))
        with zipfile.ZipFile(wheel) as built:
            assert any(
                ".dist-info/licenses/" in name and built.read(name) == license_bytes
                for name in built.namelist()
                if name.endswith("LICENSE")
            ), "h3o license missing from wheel"
        print(
            "Extracted sdist builds successfully and the wheel includes h3o's license."
        )


if __name__ == "__main__":
    main()
