"""Verify published records and refresh their README inventory."""

import argparse
import json
import re

from local_elections_uttarakhand.parse.to_parquet import DATA, ROOT, export


def data_summary():
    manifest = json.loads((DATA / "fin/MANIFEST.json").read_text())
    lines = [
        "<!-- datasets:start -->",
        "",
        "| File | Rows | Each row represents |",
        "| --- | ---: | --- |",
    ]
    for entry in sorted(manifest["files"], key=lambda e: e["file"]):
        name = entry["file"]
        kind = (
            "Haridwar panchayat"
            if "haridwar" in name
            else "Panchayat"
            if "panchayat" in name
            else "Urban local-body"
        )
        lines.append(
            f"| [fin/{name}](data/fin/{name}) | {entry['rows']:,} | "
            f"{kind} candidate record |"
        )
    lines.extend(["", "<!-- datasets:end -->"])
    path = ROOT / "README.md"
    text = path.read_text()
    pattern = r"<!-- datasets:start -->.*?<!-- datasets:end -->"
    if len(re.findall(pattern, text, flags=re.S)) != 1:
        raise ValueError("README must contain one dataset inventory block")
    path.write_text(re.sub(pattern, lambda _: "\n".join(lines), text, flags=re.S))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "summary"])
    args = parser.parse_args()
    if args.command == "verify":
        export(DATA, DATA / "fin", check=True)
    else:
        data_summary()


if __name__ == "__main__":
    main()
