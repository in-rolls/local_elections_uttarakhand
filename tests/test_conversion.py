"""Preserve candidate granularity, original scripts, and numeric-looking strings."""

import csv

import pyarrow.parquet as pq
import pytest
from to_parquet import CONTRACTS, read_source, write_atomic


def source(tmp_path, name, *, year=None, suspect=False, missing=False, ragged=False):
    contract = CONTRACTS[name]
    mapped = dict.fromkeys(contract["columns"].values(), "")
    mapped["year"] = str(year if year is not None else contract["years"][0])
    mapped["candidate_raw"] = "" if missing else "उदाहरण"
    mapped["district_raw"] = "\u0430§¶" if suspect else "जनपद"
    mapped["candidate_votes_raw"] = "0010"
    if "winner_votes_raw" in mapped:
        mapped["winner_votes_raw"] = "0200"
    row = list(mapped.values())
    if ragged:
        row.pop()
    path = tmp_path / name
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(contract["columns"])
        writer.writerows([row, row])
    return path, contract


@pytest.mark.parametrize("name", CONTRACTS)
def test_roundtrip_preserves_source_values_and_duplicate_observations(tmp_path, name):
    path, contract = source(tmp_path, name)
    table = read_source(path, contract)
    out = tmp_path / "result.parquet"
    write_atomic(out, table)
    assert pq.read_table(out).equals(table, check_metadata=True)
    assert table.num_rows == 2
    row = table.to_pylist()[0]
    assert row["candidate_votes_raw"] == "0010"
    assert row["district_raw"] == "जनपद"
    assert row["candidate_raw"] == "उदाहरण"
    assert row["source_row"] == 1
    assert table.to_pylist()[1]["source_row"] == 2
    if "winner_votes_raw" in row:
        assert row["winner_votes_raw"] == "0200"


def test_encoding_and_missing_candidate_are_flagged_without_repair(tmp_path):
    path, contract = source(tmp_path, next(iter(CONTRACTS)), suspect=True, missing=True)
    row = read_source(path, contract).to_pylist()[0]
    assert row["district_raw"] == "\u0430§¶"
    assert row["candidate_raw"] is None
    assert row["quality_flags"] == ["text_encoding_suspect", "candidate_missing"]


def test_unexpected_year_fails(tmp_path):
    path, contract = source(tmp_path, next(iter(CONTRACTS)), year=2099)
    with pytest.raises(ValueError, match="unexpected year"):
        read_source(path, contract)


def test_ragged_row_fails(tmp_path):
    path, contract = source(tmp_path, next(iter(CONTRACTS)), ragged=True)
    with pytest.raises(ValueError, match="column count"):
        read_source(path, contract)


def test_unexpected_header_fails(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("other,columns\n1,2\n")
    with pytest.raises(ValueError, match="unexpected header"):
        read_source(path, next(iter(CONTRACTS.values())))


def test_failed_write_preserves_existing_release(tmp_path, monkeypatch):
    out = tmp_path / "result.parquet"
    out.write_bytes(b"previous")

    def fail(_table, path, **_kwargs):
        path.write_bytes(b"partial")
        raise OSError("interrupted")

    monkeypatch.setattr(pq, "write_table", fail)
    with pytest.raises(OSError):
        write_atomic(out, None)
    assert out.read_bytes() == b"previous"
    assert not out.with_suffix(".parquet.part").exists()
