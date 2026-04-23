"""
services/log_store.py

Lightweight file-based log system for the AVGO projection pipeline.

Three log types
---------------
prediction_log   — one entry per projection run; records predicted state,
                   features, Top1/Top2, exclusion & consistency results.
outcome_log      — one entry per captured actual result; links back to
                   prediction_log via prediction_log_id; records actual
                   five-state label and whether prediction was correct.
rule_trace_log   — one entry per rule evaluation event across all layers
                   (exclusion / main_projection / consistency); links back
                   to prediction_log_id for full traceability.

Storage format: JSONL (JSON Lines) — one JSON object per line, append-only.
Default log directory: <project_root>/logs/

Public write API
----------------
write_prediction_log(record)    -> str  (log_id)
write_outcome_log(record)       -> str  (log_id)
write_rule_trace_log(record)    -> str  (log_id)

Public read API
---------------
read_prediction_log(*, symbol, date, since_date, limit)   -> list[dict]
read_outcome_log(*, prediction_log_id, date, limit)        -> list[dict]
read_rule_trace_log(*, prediction_log_id, layer, limit)    -> list[dict]

All read functions return newest-first (reverse file order).
All write functions auto-inject log_id (UUID4) and created_at if absent.
Functions never raise on missing/empty log files — they return [].
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.state_label import label_state

# ── configuration ─────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR      = _PROJECT_ROOT / "logs"

_PRED_FILE    = LOGS_DIR / "prediction_log.jsonl"
_OUTCOME_FILE = LOGS_DIR / "outcome_log.jsonl"
_TRACE_FILE   = LOGS_DIR / "rule_trace_log.jsonl"


# ── internal helpers ──────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return str(uuid.uuid4())


def _ensure_logs_dir() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _append(path: Path, record: dict[str, Any]) -> None:
    _ensure_logs_dir()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_all(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _inject_meta(record: dict[str, Any]) -> dict[str, Any]:
    """Ensure log_id and created_at exist."""
    r = dict(record)
    if not r.get("log_id"):
        r["log_id"] = _new_id()
    if not r.get("created_at"):
        r["created_at"] = _now_iso()
    return r


# ── prediction_log ────────────────────────────────────────────────────────────
#
# Required fields (caller should supply these):
#   symbol                 str          "AVGO"
#   analysis_date          str          "YYYY-MM-DD"  — date analysis ran
#   prediction_for_date    str          "YYYY-MM-DD"  — date being predicted
#   window_days            int          always 20
#   predicted_state        str          "大涨"|"小涨"|"震荡"|"小跌"|"大跌"
#   predicted_top1         dict         {"state":"小涨","probability":0.42}
#   predicted_top2         dict         {"state":"震荡","probability":0.24}
#   state_probabilities    dict[str,float]  {"大涨":0.10, ...}
#   direction              str          "偏多"|"偏空"|"中性"
#   confidence             str          "high"|"medium"|"low"
#   exclusion_action       str          "allow"|"exclude"
#   exclusion_triggered_rule  str|None
#   excluded_state         str|None     "大涨"|"大跌"（由 triggered_rule 推导）
#   consistency_passed     bool
#   consistency_flag       str|None     "consistent"|"mixed"|"conflict"
#   consistency_score      float|None   0.0 ~ 1.0
#   consistency_conflicts  list[str]
#   feature_snapshot       dict         from compute_20d_features()
#   peer_alignment         dict         from build_peer_alignment()
#   notes                  list[str]
#
# Auto-injected:
#   log_id                 str          UUID4
#   created_at             str          ISO 8601 UTC

def write_prediction_log(record: dict[str, Any]) -> str:
    """Append one entry to prediction_log.jsonl.  Returns the log_id."""
    r = _inject_meta(record)
    predicted_top1 = r.get("predicted_top1") if isinstance(r.get("predicted_top1"), dict) else {}
    predicted_top2 = r.get("predicted_top2") if isinstance(r.get("predicted_top2"), dict) else {}
    if r.get("predicted_state") is None and predicted_top1.get("state") is not None:
        r["predicted_state"] = predicted_top1.get("state")
    if not predicted_top1 and r.get("predicted_state") is not None:
        predicted_top1 = {
            "state": r.get("predicted_state"),
            "probability": None,
        }
        r["predicted_top1"] = predicted_top1

    if r.get("consistency_passed") is None and r.get("consistency_flag") is not None:
        r["consistency_passed"] = r.get("consistency_flag") == "consistent"

    if r.get("excluded_state") is None:
        rule = r.get("exclusion_triggered_rule")
        if rule == "exclude_big_up":
            r["excluded_state"] = "大涨"
        elif rule == "exclude_big_down":
            r["excluded_state"] = "大跌"

    # Defensive: ensure all expected top-level keys exist (None = unknown)
    defaults: dict[str, Any] = {
        "symbol":                   "AVGO",
        "analysis_date":            None,
        "prediction_for_date":      None,
        "window_days":              20,
        "predicted_state":          None,
        "predicted_top1":           predicted_top1,
        "predicted_top2":           predicted_top2,
        "state_probabilities":      {},
        "direction":                None,
        "confidence":               None,
        "exclusion_action":         None,
        "exclusion_triggered_rule": None,
        "excluded_state":           None,
        "consistency_passed":       None,
        "consistency_flag":         None,
        "consistency_score":        None,
        "consistency_conflicts":    [],
        "feature_snapshot":         {},
        "peer_alignment":           {},
        "notes":                    [],
    }
    for k, v in defaults.items():
        r.setdefault(k, v)
    _append(_PRED_FILE, r)
    return r["log_id"]


def read_prediction_log(
    *,
    symbol: str | None = None,
    date: str | None = None,       # exact prediction_for_date
    since_date: str | None = None, # prediction_for_date >= since_date
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return up to *limit* prediction_log entries, newest first.

    Filters (all optional, AND-combined):
      symbol      — match record["symbol"]
      date        — match record["prediction_for_date"] exactly
      since_date  — record["prediction_for_date"] >= since_date
    """
    entries = _read_all(_PRED_FILE)
    if symbol:
        entries = [e for e in entries if e.get("symbol") == symbol]
    if date:
        entries = [e for e in entries if e.get("prediction_for_date") == date]
    if since_date:
        entries = [e for e in entries if (e.get("prediction_for_date") or "") >= since_date]
    return list(reversed(entries))[:limit]


# ── outcome_log ───────────────────────────────────────────────────────────────
#
# Required fields:
#   prediction_log_id      str          log_id from write_prediction_log()
#   symbol                 str          "AVGO"
#   prediction_for_date    str          "YYYY-MM-DD"
#   actual_open            float|None
#   actual_high            float|None
#   actual_low             float|None
#   actual_close           float|None
#   actual_prev_close      float|None
#   actual_close_change_pct float|None  percentage: 2.1 means +2.1%
#                                       (convert from ratio × 100 if needed)
#   actual_state           str|None     five-state from state_label.label_state()
#   predicted_state        str|None     copied from prediction_log
#   state_match            bool|None    actual_state == predicted_state
#   direction_correct      bool|None
#   actual_upper_shadow_ratio float|None
#   actual_lower_shadow_ratio float|None
#
# Auto-injected:
#   log_id, created_at

def write_outcome_log(record: dict[str, Any]) -> str:
    """Append one entry to outcome_log.jsonl.  Returns the log_id."""
    r = _inject_meta(record)
    actual_close_change_pct = r.get("actual_close_change_pct")
    if r.get("actual_state") is None and actual_close_change_pct is not None:
        try:
            r["actual_state"] = label_state(float(actual_close_change_pct))
        except (TypeError, ValueError):
            pass
    if (
        r.get("state_match") is None
        and r.get("actual_state") is not None
        and r.get("predicted_state") is not None
    ):
        r["state_match"] = r.get("actual_state") == r.get("predicted_state")
    defaults: dict[str, Any] = {
        "prediction_log_id":          None,
        "symbol":                     "AVGO",
        "prediction_for_date":        None,
        "actual_open":                None,
        "actual_high":                None,
        "actual_low":                 None,
        "actual_close":               None,
        "actual_prev_close":          None,
        "actual_close_change_pct":    None,
        "actual_state":               None,
        "predicted_state":            None,
        "state_match":                None,
        "direction_correct":          None,
        "actual_upper_shadow_ratio":  None,
        "actual_lower_shadow_ratio":  None,
    }
    for k, v in defaults.items():
        r.setdefault(k, v)
    _append(_OUTCOME_FILE, r)
    return r["log_id"]


def read_outcome_log(
    *,
    prediction_log_id: str | None = None,
    date: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return up to *limit* outcome_log entries, newest first.

    Filters (optional, AND-combined):
      prediction_log_id — match record["prediction_log_id"]
      date              — match record["prediction_for_date"] exactly
    """
    entries = _read_all(_OUTCOME_FILE)
    if prediction_log_id:
        entries = [e for e in entries if e.get("prediction_log_id") == prediction_log_id]
    if date:
        entries = [e for e in entries if e.get("prediction_for_date") == date]
    return list(reversed(entries))[:limit]


# ── rule_trace_log ────────────────────────────────────────────────────────────
#
# Required fields:
#   prediction_log_id  str           log_id from write_prediction_log()
#   symbol             str           "AVGO"
#   analysis_date      str           "YYYY-MM-DD"
#   prediction_for_date str          "YYYY-MM-DD"
#   layer              str           "exclusion"|"main_projection"|"consistency"
#   rule_name          str           identifier of the rule evaluated
#   rule_result        str           "triggered"|"not_triggered"|"conflict"
#   feature_values     dict          relevant feature subset when rule ran
#   summary            str           human-readable description
#
# Auto-injected:
#   log_id, created_at

def write_rule_trace_log(record: dict[str, Any]) -> str:
    """Append one entry to rule_trace_log.jsonl.  Returns the log_id."""
    r = _inject_meta(record)
    defaults: dict[str, Any] = {
        "prediction_log_id":  None,
        "symbol":             "AVGO",
        "analysis_date":      None,
        "prediction_for_date": None,
        "layer":              None,
        "rule_name":          None,
        "rule_result":        None,
        "feature_values":     {},
        "summary":            "",
    }
    for k, v in defaults.items():
        r.setdefault(k, v)
    _append(_TRACE_FILE, r)
    return r["log_id"]


def read_rule_trace_log(
    *,
    prediction_log_id: str | None = None,
    layer: str | None = None,
    rule_name: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return up to *limit* rule_trace_log entries, newest first.

    Filters (optional, AND-combined):
      prediction_log_id — match record["prediction_log_id"]
      layer             — match record["layer"]
      rule_name         — match record["rule_name"]
    """
    entries = _read_all(_TRACE_FILE)
    if prediction_log_id:
        entries = [e for e in entries if e.get("prediction_log_id") == prediction_log_id]
    if layer:
        entries = [e for e in entries if e.get("layer") == layer]
    if rule_name:
        entries = [e for e in entries if e.get("rule_name") == rule_name]
    return list(reversed(entries))[:limit]


# ── convenience helpers ───────────────────────────────────────────────────────

def get_prediction_by_id(log_id: str) -> dict[str, Any] | None:
    """Return the first prediction_log entry with the given log_id, or None."""
    for entry in _read_all(_PRED_FILE):
        if entry.get("log_id") == log_id:
            return entry
    return None


def get_latest_prediction(symbol: str = "AVGO") -> dict[str, Any] | None:
    """Return the most recent prediction_log entry for *symbol*, or None."""
    entries = read_prediction_log(symbol=symbol, limit=1)
    return entries[0] if entries else None


def summarize_logs() -> dict[str, Any]:
    """Return count and date range for each log file (for diagnostics)."""
    result: dict[str, Any] = {}
    for name, path in (
        ("prediction_log", _PRED_FILE),
        ("outcome_log", _OUTCOME_FILE),
        ("rule_trace_log", _TRACE_FILE),
    ):
        entries = _read_all(path)
        dates = sorted(
            e.get("prediction_for_date") or e.get("analysis_date") or ""
            for e in entries
            if e.get("prediction_for_date") or e.get("analysis_date")
        )
        result[name] = {
            "count": len(entries),
            "earliest": dates[0] if dates else None,
            "latest":   dates[-1] if dates else None,
        }
    return result
