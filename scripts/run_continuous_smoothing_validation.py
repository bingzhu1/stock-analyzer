"""scripts/run_continuous_smoothing_validation.py — dry-run validation orchestrator.

Step 3R-3.3A implementation per Step 3R-3.3 design (commit ``8a24295``)
+ checkpoint (``2535467``). Stitches the three Step 3R layers
(candidate / adapter / helper) into a single read-only orchestrator
that takes caller-injected replay rows + W4 manifest dict + a
``regime_label_provider`` callable, and returns a combined run dict
(plus optional 4 output files).

This module is **read-only diagnostics**:
- never reads DB / network; never imports ``yfinance`` / ``requests``
  / trading APIs / ``services.prediction_store`` / ``predict`` /
  ``scanner`` / ``streamlit``
- does NOT read the W4 jsonl file; caller injects ``replay_rows``
- does NOT read the W4 manifest file; caller injects ``w4_manifest``
  dict
- does NOT mutate input rows or manifest
- does NOT sweep / learn / pick ``candidate_threshold``; caller passes
  it (default 0.60 is a v1 design seed only — see Step 3R-3.3 §5)
- 2026 final-test cutoff: any row with analysis_date >= cutoff is
  skipped and run_manifest.final_test_touched is set True
- when ``write_outputs=True``: writes exactly 4 files into
  ``output_dir``; refuses to write into a pre-existing directory

Public API:
    run_continuous_smoothing_validation(
        replay_rows,
        *,
        regime_label_provider,
        w4_manifest,
        candidate_threshold=0.60,
        candidate_name="continuous_smoothing_v1",
        final_test_cutoff="2026-01-01",
        output_dir=None,
        write_outputs=False,
    ) -> dict
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from services.continuous_smoothing_candidate import (
    build_continuous_smoothing_candidate,
)
from services.regime_validation_helper import build_regime_validation_report
from services.replay_validation_record_adapter import (
    DEFAULT_WINDOWS,
    build_replay_validation_records,
)


RUN_SCHEMA_VERSION = "continuous_smoothing_validation_run.v1"
RUN_MANIFEST_SCHEMA_VERSION = "regime_validation_run_manifest.v1"
DEFAULT_CANDIDATE_NAME = "continuous_smoothing_v1"
DEFAULT_CANDIDATE_THRESHOLD = 0.60
DEFAULT_FINAL_TEST_CUTOFF = "2026-01-01"


# ── helpers ──────────────────────────────────────────────────────────────


def _extract_analysis_date(row: dict[str, Any]) -> str | None:
    candidate_keys = ("as_of_date", "analysis_date")
    for key in candidate_keys:
        v = row.get(key)
        if isinstance(v, str):
            return v
    return None


def _enrich_row_with_candidate(
    row: dict[str, Any],
    *,
    regime_label_provider: Callable[[str, dict[str, Any]], dict[str, Any]],
    analysis_date: str,
    final_test_cutoff: str,
) -> tuple[dict[str, Any], list[str], bool]:
    """Return (enriched_row_copy, warnings, candidate_final_test_touched)."""
    warnings: list[str] = []
    enriched = deepcopy(row)

    try:
        labels = regime_label_provider(analysis_date, row)
    except Exception as exc:  # pragma: no cover — caller bug
        warnings.append(f"regime_label_provider_failed:{type(exc).__name__}")
        return enriched, warnings, False

    if not isinstance(labels, dict):
        warnings.append("regime_label_provider_returned_non_dict")
        return enriched, warnings, False

    labels_refusal = bool(labels.get("final_test_refusal"))

    candidate = build_continuous_smoothing_candidate(
        labels,
        as_of_date=analysis_date,
        final_test_cutoff=final_test_cutoff,
    )
    enriched["candidate"] = candidate
    if isinstance(labels.get("labels"), dict):
        enriched["labels"] = deepcopy(labels["labels"])

    candidate_refusal = bool(candidate.get("final_test_refusal"))
    return enriched, warnings, labels_refusal or candidate_refusal


def _build_run_manifest(
    *,
    candidate_name: str,
    candidate_threshold: float,
    w4_manifest_status: str,
    final_test_cutoff: str,
    final_test_touched: bool,
    records_loaded: int,
    records_adapted: int,
    report_status: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "candidate_name": candidate_name,
        "candidate_threshold": candidate_threshold,
        "fold_count": 4,
        "windows": {
            name: {"start": span["start"], "end": span["end"]}
            for name, span in DEFAULT_WINDOWS.items()
        },
        "w4_manifest_status": w4_manifest_status,
        "final_test_cutoff": final_test_cutoff,
        "final_test_touched": bool(final_test_touched),
        "records_loaded": records_loaded,
        "records_adapted": records_adapted,
        "report_status": report_status,
        "warnings": list(warnings),
    }


def _render_summary_md(
    *,
    run_manifest: dict[str, Any],
    report: dict[str, Any],
) -> str:
    overall = report.get("overall_status")
    worst = report.get("worst_window")
    fail_reason = report.get("fail_reason")
    lines = [
        "# Continuous Smoothing Validation Run Summary",
        "",
        f"- candidate_name: {run_manifest['candidate_name']}",
        f"- candidate_threshold: {run_manifest['candidate_threshold']}",
        f"- fold_count: {run_manifest['fold_count']}",
        f"- final_test_cutoff: {run_manifest['final_test_cutoff']}",
        f"- final_test_touched: {run_manifest['final_test_touched']}",
        f"- w4_manifest_status: {run_manifest['w4_manifest_status']}",
        f"- records_loaded: {run_manifest['records_loaded']}",
        f"- records_adapted: {run_manifest['records_adapted']}",
        f"- report_status: {run_manifest['report_status']}",
        f"- overall_status: {overall}",
        f"- worst_window: {worst}",
        f"- fail_reason: {fail_reason}",
        "",
        "_This run is a read-only diagnostic; pass does not grant production permission._",
    ]
    return "\n".join(lines) + "\n"


def _write_outputs_files(
    *,
    output_dir: Path,
    records_payload: dict[str, Any],
    report: dict[str, Any],
    run_manifest: dict[str, Any],
    summary_md: str,
) -> None:
    if output_dir.exists():
        raise FileExistsError(
            f"output_dir already exists: {output_dir}; refuse to overwrite"
        )
    output_dir.mkdir(parents=True, exist_ok=False)

    def _dump_json(name: str, payload: Any) -> None:
        path = output_dir / name
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    _dump_json("replay_validation_records.json", records_payload)
    _dump_json("regime_validation_report.json", report)
    _dump_json("run_manifest.json", run_manifest)
    (output_dir / "regime_validation_summary.md").write_text(
        summary_md, encoding="utf-8"
    )


# ── public API ───────────────────────────────────────────────────────────


def run_continuous_smoothing_validation(
    replay_rows: list[dict[str, Any]],
    *,
    regime_label_provider: Callable[[str, dict[str, Any]], dict[str, Any]],
    w4_manifest: dict[str, Any],
    candidate_threshold: float = DEFAULT_CANDIDATE_THRESHOLD,
    candidate_name: str = DEFAULT_CANDIDATE_NAME,
    final_test_cutoff: str = DEFAULT_FINAL_TEST_CUTOFF,
    output_dir: str | Path | None = None,
    write_outputs: bool = False,
) -> dict[str, Any]:
    """Stitch candidate → adapter → helper for a dry-run validation pass.

    See module docstring for full read-only constraints.
    """
    if write_outputs and output_dir is None:
        raise ValueError(
            "output_dir is required when write_outputs=True"
        )

    warnings: list[str] = []
    enriched_rows: list[dict[str, Any]] = []
    final_test_touched = False
    records_loaded = 0

    for row in replay_rows:
        if not isinstance(row, dict):
            warnings.append("orchestrator_skipped:row_not_dict")
            continue
        records_loaded += 1
        analysis_date = _extract_analysis_date(row)
        if analysis_date is None:
            warnings.append("orchestrator_skipped:missing_analysis_date")
            continue
        if analysis_date >= final_test_cutoff:
            final_test_touched = True
            warnings.append(
                f"orchestrator_skipped:final_test_range_refusal:{analysis_date}"
            )
            continue
        enriched, row_warnings, refusal_flag = _enrich_row_with_candidate(
            row,
            regime_label_provider=regime_label_provider,
            analysis_date=analysis_date,
            final_test_cutoff=final_test_cutoff,
        )
        warnings.extend(row_warnings)
        if refusal_flag:
            final_test_touched = True
        enriched_rows.append(enriched)

    records_payload = build_replay_validation_records(
        enriched_rows,
        candidate_threshold=candidate_threshold,
        candidate_name=candidate_name,
        final_test_cutoff=final_test_cutoff,
        require_w4_manifest=True,
        w4_manifest=w4_manifest,
    )
    warnings.extend(records_payload.get("warnings", []))
    if records_payload.get("final_test_refusal"):
        final_test_touched = True

    adapter_failures = [
        w
        for w in records_payload.get("warnings", [])
        if isinstance(w, str)
        and w.startswith("w4_")
        and w != "w4_manifest_not_required"
    ]
    w4_manifest_status = "error" if adapter_failures else "ok"

    records_for_helper = list(records_payload.get("records", []))
    report = build_regime_validation_report(
        records_for_helper,
        candidate_name=candidate_name,
        candidate_kind="smoothing",
        final_test_cutoff=final_test_cutoff,
        require_w4_manifest=False,
        w4_manifest_path=None,
    )
    warnings.extend(report.get("warnings", []))
    if report.get("final_test_refusal"):
        final_test_touched = True

    helper_status = report.get("overall_status", "error")
    if final_test_touched or w4_manifest_status == "error":
        report_status = "error"
    elif helper_status in ("pass", "fail", "error"):
        report_status = helper_status
    else:
        report_status = "error"

    run_manifest = _build_run_manifest(
        candidate_name=candidate_name,
        candidate_threshold=candidate_threshold,
        w4_manifest_status=w4_manifest_status,
        final_test_cutoff=final_test_cutoff,
        final_test_touched=final_test_touched,
        records_loaded=records_loaded,
        records_adapted=len(records_payload.get("records", [])),
        report_status=report_status,
        warnings=warnings,
    )

    summary_md = _render_summary_md(run_manifest=run_manifest, report=report)

    if write_outputs:
        out_path = Path(output_dir)  # type: ignore[arg-type]
        _write_outputs_files(
            output_dir=out_path,
            records_payload=records_payload,
            report=report,
            run_manifest=run_manifest,
            summary_md=summary_md,
        )

    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "candidate_name": candidate_name,
        "candidate_threshold": candidate_threshold,
        "records_loaded": records_loaded,
        "records_adapted": len(records_payload.get("records", [])),
        "report_status": report_status,
        "replay_validation_records": records_payload,
        "regime_validation_report": report,
        "run_manifest": run_manifest,
        "warnings": warnings,
    }


if __name__ == "__main__":
    print(
        "This script exposes run_continuous_smoothing_validation as a library "
        "function.\n"
        "Direct CLI execution is intentionally not provided in v1; integration "
        "is by future Step 3R-3.3C real validation run.",
        flush=True,
    )
    raise SystemExit(0)
