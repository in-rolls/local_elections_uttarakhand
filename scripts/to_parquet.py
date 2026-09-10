"""Preserve Uttarakhand candidate records and repeated contest-level fields."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONTRACTS = json.loads((ROOT / "schemas.json").read_text())


def schema(contract):
    return pa.schema(
        [
            pa.field(name, pa.int16() if name == "year" else pa.string())
            for name in contract["columns"].values()
        ]
        + [
            pa.field("source_row", pa.int32(), nullable=False),
            pa.field(
                "quality_flags",
                pa.list_(pa.field("element", pa.string())),
                nullable=False,
            ),
        ]
    )


def read_source(path, contract):
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        if next(reader, None) != list(contract["columns"]):
            raise ValueError(f"{path}: unexpected header")
        for number, values in enumerate(reader, 1):
            if len(values) != len(contract["columns"]):
                raise ValueError(f"{path}:{number}: inconsistent column count")
            row = dict(zip(contract["columns"].values(), values, strict=True))
            if row["year"] not in {str(y) for y in contract["years"]}:
                raise ValueError(f"{path}:{number}: unexpected year")
            row = {key: value or None for key, value in row.items()}
            row["year"] = int(row["year"])
            flags = []
            if any(re.search(r"[\u0400-\u04ff]", value) for value in values):
                flags.append("text_encoding_suspect")
            if row["candidate_raw"] is None:
                flags.append("candidate_missing")
            row.update(source_row=number, quality_flags=flags)
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no candidate records")
    return pa.Table.from_pylist(rows, schema=schema(contract))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_atomic(path, table):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".parquet.part")
    try:
        pq.write_table(table, temporary, compression="zstd")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def export(data, out, check=False):
    manifest = {
        "format_version": 1,
        "column_map_sha256": digest(ROOT / "schemas.json"),
        "files": [],
    }
    for name, contract in CONTRACTS.items():
        source = data / name
        table = read_source(source, contract)
        target = out / contract["output"]
        if check:
            if not table.equals(pq.read_table(target), check_metadata=True):
                raise ValueError(f"{target}: schema or values differ from source")
        else:
            write_atomic(target, table)
        manifest["files"].append(
            {
                "file": target.name,
                "source_csv": name,
                "source_sha256": digest(source),
                "sha256": digest(target),
                "rows": table.num_rows,
                "schema": [
                    {"name": f.name, "type": str(f.type), "nullable": f.nullable}
                    for f in table.schema
                ],
            }
        )
        print(f"{target.name}: {table.num_rows:,} candidate records")
    path = out / "MANIFEST.json"
    if check:
        if json.loads(path.read_text()) != manifest:
            raise ValueError(f"{path}: source hashes or export metadata changed")
    else:
        temporary = path.with_suffix(".json.part")
        temporary.write_text(json.dumps(manifest, indent=2) + "\n")
        temporary.replace(path)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        export(args.data, args.out or args.data / "fin", args.check)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
