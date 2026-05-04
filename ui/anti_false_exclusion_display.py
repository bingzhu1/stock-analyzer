"""ui/anti_false_exclusion_display.py — read-only sidecar diagnostic.

Step 2G-7A implementation per Step 2G-7 design (commit `cd571e4`).
Pure-function helper that builds the
``anti_false_exclusion_display.v1`` sidecar for a given
``soft_metadata.v1`` payload + optional ``prediction_correct`` flag.
The output explicitly quantifies "why the metadata cannot be hard-
exclusion": surfaces the 5 protective findings (Step 2G-7 §6) so the
Predict / Review UI can show "为什么这里只做提示" expandable section.

Design contract (Step 2G-7 §7 / §10):
- pure function: never reads DB / CSV / network; never imports
  simulator / prediction_store / yfinance / requests / trading APIs /
  v1 stub trio
- never mutates input
- always returns a dict; never raises
- ``hard_exclusion_allowed`` is **always** ``False`` (v1 spec strong
  invariant)
- never produces forbidden copy (Step 2G-7 §9 — superset of the 16
  renderer FORBIDDEN_COPY_TOKENS plus standalone ``hard``/``forced``/
  ``排除``); tests grep the rendered markdown to lock this

Public API:
    build_anti_false_exclusion_display(
        soft_metadata, *, prediction_correct=None,
    ) -> dict
    render_anti_false_exclusion_markdown(display) -> str

Severity enum (scoped to this sidecar; NOT the renderer's):
    "informational" | "medium" | "high"
"""
from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "anti_false_exclusion_display.v1"

# Hard-gate thresholds (mirror Step 2G-3 / 2G-4.5 / Step 2G-5).
_FE_GATE = 0.10
_NB_GATE = 0.05

# Sidecar-local severity enum.
SEVERITY_INFORMATIONAL = "informational"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"

# Forbidden copy that this sidecar must NEVER emit. Tests grep
# render_anti_false_exclusion_markdown output for these.
# Includes the 16 renderer tokens + standalone "hard" / "forced" /
# "排除" (per Step 2G-7 §9).
FORBIDDEN_COPY_TOKENS: tuple[str, ...] = (
    "禁止交易", "强制否定", "必须不做",
    "hard exclusion", "forced exclusion",
    "自动拦截", "no_trade",
    "卖出信号", "做空信号", "看空信号",
    "否决主推演", "推翻主推演",
    "强制平仓", "force close",
    "阻止下单", "block order",
    " hard ", " forced ", "排除",
)


# ── helpers ──────────────────────────────────────────────────────────────

def _is_real_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _find_signal(signals: list[Any], name: str) -> dict | None:
    for s in signals:
        if isinstance(s, dict) and s.get("name") == name:
            return s
    return None


def _derive_correct_count(metrics: dict) -> int | None:
    """correct_when_triggered ≈ accuracy × paired (rounded).

    The simulator does not expose ``correct`` directly, but for bullish
    slices (R4 / residual) ``predicted_bullish_rate=1.0`` makes
    ``false_exclusion_rate == accuracy``, so ``correct = paired ×
    accuracy`` to the nearest integer is exact (modulo float rounding).
    """
    paired = metrics.get("paired")
    acc = metrics.get("accuracy")
    if not _is_real_number(paired) or not _is_real_number(acc):
        return None
    return round(float(acc) * int(paired))


def _empty_display(warnings: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "visible": False,
        "status": "blocked",
        "hard_exclusion_allowed": False,
        "primary_reason": None,
        "protective_findings": [],
        "recommended_action": "review_only",
        "required_next_step": None,
        "warnings": list(warnings),
    }


# ── per-finding builders ────────────────────────────────────────────────

def _maybe_r4_survival_case(
    r4_signal: dict | None,
    *,
    prediction_correct: bool | None,
) -> dict | None:
    if r4_signal is None:
        return None
    if prediction_correct is not True:
        return None
    metrics = _safe_dict(r4_signal.get("historical_metrics_in_sample"))
    return {
        "name": "r4_survival_case",
        "severity": SEVERITY_INFORMATIONAL,
        "evidence": {
            "survived_count": _derive_correct_count(metrics),
            "total_triggered_count": metrics.get("paired"),
            "survival_rate": metrics.get("accuracy"),
        },
        "message": (
            "风险触发但本次结构幸存。该信号未来不能作为自动决策依据，"
            "仅供复盘提示。"
        ),
    }


def _maybe_r4_false_exclusion_risk(r4_signal: dict | None) -> dict | None:
    if r4_signal is None:
        return None
    metrics = _safe_dict(r4_signal.get("historical_metrics_in_sample"))
    fer = metrics.get("false_exclusion_rate")
    if not _is_real_number(fer) or float(fer) <= _FE_GATE:
        return None
    return {
        "name": "r4_false_exclusion_risk",
        "severity": SEVERITY_MEDIUM,
        "evidence": {
            "false_exclusion_rate": float(fer),
            "threshold": _FE_GATE,
            "correct_when_triggered": _derive_correct_count(metrics),
            "paired": metrics.get("paired"),
        },
        "message": (
            "误杀风险较高：该信号触发时仍有较多正确样本，当前只允许"
            "复盘提示，不能作为自动决策依据。"
        ),
    }


def _maybe_holdout_fail(signals: list[Any]) -> dict | None:
    has_fail = any(
        isinstance(s, dict) and s.get("holdout_status") == "FAIL"
        for s in signals
    )
    if not has_fail:
        return None
    return {
        "name": "soft_metadata_holdout_fail",
        "severity": SEVERITY_MEDIUM,
        "evidence": {"holdout_status": "FAIL"},
        "message": "跨窗口验证未通过，仅供复盘参考。",
    }


def _maybe_net_benefit_insufficient(r4_signal: dict | None) -> dict | None:
    if r4_signal is None:
        return None
    metrics = _safe_dict(r4_signal.get("historical_metrics_in_sample"))
    nb = metrics.get("net_benefit")
    if not _is_real_number(nb) or float(nb) >= _NB_GATE:
        return None
    return {
        "name": "net_benefit_insufficient",
        "severity": SEVERITY_MEDIUM,
        "evidence": {
            "net_benefit": float(nb),
            "threshold": _NB_GATE,
        },
        "message": "净收益不足，不满足自动决策的最低门槛。",
    }


def _missing_protection_layer() -> dict[str, Any]:
    return {
        "name": "missing_protection_layer",
        "severity": SEVERITY_HIGH,
        "evidence": {
            "connected_protection_modules": 0,
            "candidate_modules": 4,
        },
        "message": (
            "保护层未接入：4 个候选保护模块全部离线，当前只允许"
            "复盘提示。"
        ),
    }


def _pick_primary_reason(findings: list[dict]) -> str | None:
    """Most-actionable single label (Step 2G-7 §7).

    Prefer ``false_exclusion_rate_too_high`` when the relevant finding
    is present; otherwise fall back to the first non-informational
    finding's name; otherwise None.
    """
    for f in findings:
        if f["name"] == "r4_false_exclusion_risk":
            return "false_exclusion_rate_too_high"
    for f in findings:
        if f.get("severity") != SEVERITY_INFORMATIONAL:
            return f["name"]
    if findings:
        return findings[0]["name"]
    return None


# ── public API: build ──────────────────────────────────────────────────

def build_anti_false_exclusion_display(
    soft_metadata: dict,
    *,
    prediction_correct: bool | None = None,
) -> dict[str, Any]:
    """Build the ``anti_false_exclusion_display.v1`` sidecar.

    Pure function. Always returns a dict; never raises.
    ``hard_exclusion_allowed`` is always ``False`` regardless of input
    (v1 spec strong invariant).
    """
    sm = soft_metadata if isinstance(soft_metadata, dict) else {}
    summary = _safe_dict(sm.get("summary"))
    warnings = [str(w) for w in _safe_list(summary.get("warnings")) if w]
    signals = _safe_list(sm.get("signals"))

    if not signals:
        return _empty_display(warnings)

    r4_signal = _find_signal(signals, "r4_overextension")
    findings: list[dict] = []

    f1 = _maybe_r4_survival_case(r4_signal, prediction_correct=prediction_correct)
    if f1 is not None:
        findings.append(f1)
    f2 = _maybe_r4_false_exclusion_risk(r4_signal)
    if f2 is not None:
        findings.append(f2)
    f3 = _maybe_holdout_fail(signals)
    if f3 is not None:
        findings.append(f3)
    f4 = _maybe_net_benefit_insufficient(r4_signal)
    if f4 is not None:
        findings.append(f4)
    findings.append(_missing_protection_layer())

    return {
        "schema_version": SCHEMA_VERSION,
        "visible": True,
        "status": "blocked",
        "hard_exclusion_allowed": False,
        "primary_reason": _pick_primary_reason(findings),
        "protective_findings": findings,
        "recommended_action": "review_only",
        "required_next_step": "collect_more_review_outcomes",
        "warnings": warnings,
    }


# ── public API: markdown renderer ──────────────────────────────────────

def _format_pct(value: Any) -> str:
    if not _is_real_number(value):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _format_evidence_kv(evidence: dict) -> list[str]:
    """Pretty-print evidence values for display."""
    out: list[str] = []
    for key, value in evidence.items():
        if key in ("false_exclusion_rate", "survival_rate", "threshold",
                   "net_benefit"):
            out.append(f"{key}={_format_pct(value)}")
        elif value is None:
            out.append(f"{key}=n/a")
        else:
            out.append(f"{key}={value}")
    return out


def render_anti_false_exclusion_markdown(display: dict) -> str:
    """Render the sidecar into a safe markdown string.

    Pure function. Empty string when ``display.visible`` is False.
    Output is grep-safe per Step 2G-7 §9 forbidden-copy list (tests
    lock this).
    """
    cd = display if isinstance(display, dict) else {}
    if not cd.get("visible"):
        return ""
    findings = _safe_list(cd.get("protective_findings"))
    if not findings:
        return ""

    lines: list[str] = []
    lines.append("**为什么这里只做提示**")
    lines.append(
        "本卡片只解释为什么 metadata **不能**作为自动决策依据；"
        "不改变主推演方向，不构成交易指令。"
    )

    primary = cd.get("primary_reason")
    if primary:
        lines.append(f"_主要原因：_ `{primary}`")

    for f in findings:
        if not isinstance(f, dict):
            continue
        name = f.get("name", "")
        severity = f.get("severity", "")
        message = f.get("message", "")
        evidence = _safe_dict(f.get("evidence"))
        lines.append("")
        lines.append(f"- **{name}**（{severity}）：{message}")
        if evidence:
            evidence_str = " · ".join(_format_evidence_kv(evidence))
            lines.append(f"  · _evidence:_ {evidence_str}")

    nxt = cd.get("required_next_step")
    if nxt:
        lines.append("")
        lines.append(f"_待补条件：_ `{nxt}`（在此之前只允许复盘提示）")

    return "\n".join(lines).strip() + "\n"
