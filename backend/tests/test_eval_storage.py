"""Tests for the eval results JSONL store."""

import json
import os

import pytest

from eval.storage import append_result, read_results


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    path = tmp_path / "eval.jsonl"
    monkeypatch.setenv("EVAL_RESULTS_PATH", str(path))
    return str(path)


def test_append_creates_file_if_missing(tmp_store):
    append_result({"case": "x", "score": {"composite": 0.5}})
    assert os.path.exists(tmp_store)
    rows = read_results()
    assert len(rows) == 1
    assert rows[0]["case"] == "x"


def test_append_adds_recorded_ts_when_missing(tmp_store):
    append_result({"case": "y"})
    row = read_results()[0]
    assert "recorded_ts" in row
    assert isinstance(row["recorded_ts"], float)


def test_read_results_returns_newest_first(tmp_store):
    append_result({"case": "first", "recorded_ts": 1.0})
    append_result({"case": "second", "recorded_ts": 2.0})
    append_result({"case": "third", "recorded_ts": 3.0})
    rows = read_results()
    assert [r["case"] for r in rows] == ["third", "second", "first"]


def test_read_results_honors_limit(tmp_store):
    for i in range(5):
        append_result({"case": f"c{i}", "recorded_ts": float(i)})
    rows = read_results(limit=2)
    assert len(rows) == 2
    # Still newest-first
    assert rows[0]["case"] == "c4"


def test_read_results_filters_by_case(tmp_store):
    append_result({"case": "a", "recorded_ts": 1.0})
    append_result({"case": "b", "recorded_ts": 2.0})
    append_result({"case": "a", "recorded_ts": 3.0})
    rows = read_results(case="a")
    assert len(rows) == 2
    assert all(r["case"] == "a" for r in rows)


def test_read_missing_file_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("EVAL_RESULTS_PATH", str(tmp_path / "does-not-exist.jsonl"))
    assert read_results() == []


def test_malformed_line_is_skipped(tmp_store):
    # Write a legit row, then a garbage line, then another legit row.
    append_result({"case": "good1", "recorded_ts": 1.0})
    with open(tmp_store, "a", encoding="utf-8") as fh:
        fh.write("not json\n")
    append_result({"case": "good2", "recorded_ts": 2.0})
    rows = read_results()
    cases = {r["case"] for r in rows}
    assert cases == {"good1", "good2"}
