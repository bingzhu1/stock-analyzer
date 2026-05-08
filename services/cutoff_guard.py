"""Shared target_date cutoff guard for online memory / review / preflight paths.

Boundary contract (06 / 07A / 07B / 07C / 11D):

Online recall paths must never surface historical records that were not
yet available on ``target_date``. ``filter_records_by_cutoff`` is the
single helper every online recall path uses to enforce this. It applies
three gates:

1. Does the record carry a usable audit-date field?
   - Yes → continue to gate 2.
   - No  → SKIP, reason ``missing_audit_date``.
2. Can the audit-date string be parsed as ISO ``YYYY-MM-DD``?
   - Yes → continue to gate 3.
   - No  → SKIP, reason ``unparseable_date``.
3. Is the record date <= ``target_date``?
   - Yes → ALLOW.
   - No  → SKIP, reason ``record_after_target_date``.

In strict mode (the default), the helper never falls back to "use all
records" when filtering empties the list — the caller sees
``allowed_records == []`` and must decide how to surface that.

Audit-date priority (11D §6.1 / §6.3):

    available_as_of  > reviewed_at > created_at  >
    prediction_date  > analysis_date

``prediction_for_date`` alone is **not** a sufficient audit date — it is
the predict target, not when the record became available — so a record
that carries only ``prediction_for_date`` is treated as missing audit
date. This is the 11D §6.3 constraint.

The helper is read-only: input records are never mutated, never re-keyed,
never deep-copied unnecessarily. It does not import any DB / LLM / I/O
surface; it is a pure function over dicts.
"""

from __future__ import annotations

from typing import Any

# Strong audit-date fields. Any of these alone is enough to gate a
# record. Order matters: earlier entries take priority.
_STRONG_DATE_FIELDS: tuple[str, ...] = (
    "available_as_of",
    "reviewed_at",
    "created_at",
    "prediction_date",
    "analysis_date",
)

# Fields that exist but are NOT a sufficient audit date on their own.
# Per 11D §6.3, prediction_for_date is the predict target, not when the
# record became available, so it cannot pass the cutoff guard alone.
_INSUFFICIENT_FIELDS: frozenset[str] = frozenset({"prediction_for_date"})

_VALID_MODES: frozenset[str] = frozenset({"strict", "offline_bypass"})


def _coerce_date_token(value: Any) -> str | None:
    """Return the first ``YYYY-MM-DD`` token in ``value``, or None.

    Accepts plain ISO dates ("2026-04-21"), ISO timestamps with time
    suffix ("2026-04-21T10:00:00"), and ISO with timezone suffix
    ("2026-04-21T10:00:00+00:00"). Anything else returns None.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) < 10:
        return None
    head = text[:10]
    if (
        len(head) == 10
        and head[4] == "-"
        and head[7] == "-"
        and head[:4].isdigit()
        and head[5:7].isdigit()
        and head[8:10].isdigit()
    ):
        # Validate month/day ranges so things like "2026-13-40" are
        # treated as unparseable.
        try:
            month = int(head[5:7])
            day = int(head[8:10])
        except ValueError:
            return None
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return None
        return head
    return None


def _audit_record_cutoff(
    record: dict[str, Any],
    target_date: str | None,
) -> tuple[bool, str, str | None]:
    """Apply the three-gate cutoff to a single record.

    Returns ``(allowed, reason, audited_date)`` where:

    - ``allowed`` is True only if the record passes all three gates.
    - ``reason`` is the audit reason code:
        * ``audited_by:<field>`` on allow
        * ``missing_audit_date`` if no usable audit-date field was found
        * ``unparseable_date`` if a candidate field was non-empty but
          could not be parsed as YYYY-MM-DD
        * ``record_after_target_date`` if the parsed date > target_date
    - ``audited_date`` is the parsed audit-date string when available.
    """
    if not isinstance(record, dict):
        return False, "missing_audit_date", None

    # Walk the strong audit-date fields in priority order.
    chosen_field: str | None = None
    chosen_iso: str | None = None
    for field in _STRONG_DATE_FIELDS:
        if field not in record:
            continue
        value = record.get(field)
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        iso = _coerce_date_token(text)
        if iso is None:
            return False, "unparseable_date", None
        chosen_field = field
        chosen_iso = iso
        break

    if chosen_iso is None or chosen_field is None:
        # No strong audit-date field. If the record only carries an
        # insufficient field (e.g. prediction_for_date), surface that as
        # missing_audit_date — never use it alone.
        if any(field in record for field in _INSUFFICIENT_FIELDS):
            return False, "missing_audit_date", None
        return False, "missing_audit_date", None

    if target_date is None:
        # Strict mode + missing target_date → no record is provably
        # cutoff-safe, so SKIP with the same reason as missing audit info.
        # The caller can downgrade to "no historical context".
        return False, "missing_audit_date", chosen_iso

    if chosen_iso > target_date:
        return False, "record_after_target_date", chosen_iso

    return True, f"audited_by:{chosen_field}", chosen_iso


def filter_records_by_cutoff(
    records: list[dict[str, Any]] | None,
    *,
    target_date: str | None,
    date_fields: list[str] | None = None,
    mode: str = "strict",
) -> dict[str, Any]:
    """Filter ``records`` to those provably available on/before ``target_date``.

    Returns::

        {
            "allowed_records": list[dict],
            "skipped_records": list[dict],
            "cutoff_guard": {
                "target_date": str | None,
                "mode": "strict" | "offline_bypass",
                "allowed_count": int,
                "skipped_count": int,
                "skipped_reasons": list[str],   # deduped reason codes
                "by_reason": dict[str, int],    # reason → count
            },
        }

    The helper is read-only: ``records`` are never mutated or re-keyed.
    The returned ``allowed_records`` / ``skipped_records`` lists alias the
    same dict objects in their original order; callers must not mutate
    them either.

    Modes:
      - ``strict`` (default): no audit-date → SKIP; date > target_date →
        SKIP; target_date missing → SKIP everything (no fallback).
      - ``offline_bypass``: allow all records without filtering. ONLY
        valid for offline training / calibration callers; online paths
        must never use this mode.

    The ``date_fields`` argument is reserved for future custom priority
    overrides and is currently ignored — the default priority order
    encodes the 11D §6.1 / §6.3 contract.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            f"cutoff_guard mode must be one of {sorted(_VALID_MODES)!r}; got {mode!r}"
        )

    items = list(records or [])

    if mode == "offline_bypass":
        return {
            "allowed_records": items,
            "skipped_records": [],
            "cutoff_guard": {
                "target_date": target_date,
                "mode": "offline_bypass",
                "allowed_count": len(items),
                "skipped_count": 0,
                "skipped_reasons": [],
                "by_reason": {},
            },
        }

    allowed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    by_reason: dict[str, int] = {}

    for record in items:
        ok, reason_code, _ = _audit_record_cutoff(record, target_date)
        if ok:
            allowed.append(record)
            continue
        skipped.append(record)
        # Normalise the reason code into one of the three canonical buckets
        # that callers and tests expect.
        bucket = _bucket_for_reason(reason_code)
        by_reason[bucket] = by_reason.get(bucket, 0) + 1

    skipped_reasons = sorted(by_reason.keys())
    return {
        "allowed_records": allowed,
        "skipped_records": skipped,
        "cutoff_guard": {
            "target_date": target_date,
            "mode": "strict",
            "allowed_count": len(allowed),
            "skipped_count": len(skipped),
            "skipped_reasons": skipped_reasons,
            "by_reason": by_reason,
        },
    }


def _bucket_for_reason(reason_code: str) -> str:
    if reason_code.startswith("record_after_target_date"):
        return "record_after_target_date"
    if reason_code.startswith("unparseable_date"):
        return "unparseable_date"
    return "missing_audit_date"


def merge_cutoff_summaries(*summaries: dict[str, Any] | None, target_date: str | None) -> dict[str, Any]:
    """Combine multiple ``cutoff_guard`` summaries into one for surfacing.

    Each input is the ``cutoff_guard`` block from a downstream module
    (memory, review, etc). Counts add; reasons are deduped/unioned. The
    output preserves ``target_date`` as the caller's value so downstream
    consumers see one consistent cutoff.
    """
    allowed = 0
    skipped = 0
    by_reason: dict[str, int] = {}
    for summary in summaries:
        if not isinstance(summary, dict):
            continue
        allowed += int(summary.get("allowed_count") or 0)
        skipped += int(summary.get("skipped_count") or 0)
        for reason, count in (summary.get("by_reason") or {}).items():
            try:
                by_reason[reason] = by_reason.get(reason, 0) + int(count)
            except (TypeError, ValueError):
                continue
    return {
        "target_date": target_date,
        "mode": "strict",
        "allowed_count": allowed,
        "skipped_count": skipped,
        "skipped_reasons": sorted(by_reason.keys()),
        "by_reason": by_reason,
    }
