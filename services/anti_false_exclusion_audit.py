"""Task 071A — anti-false-exclusion audit (offline-only).

This module implements an *audit layer* that decides whether the system
is allowed to **硬否定大涨** ("hard-exclude 大涨") on a given day, given
the same per-day features captured by Task 070 (``enriched_*.csv``).

It does **not** predict 大涨 and **does not modify any production
prediction or exclusion rule**. It only converts an *already-decided*
hard exclusion into one of three outcomes::

    final_decision ∈ {hard_excluded, soft_excluded, blocked_by_audit}

Versions
--------
v1 (Task 071A original)
    3 auditors (rebound / breakout / peer_catchup) with fixed thresholds.
    ``risk_count >= 2`` → block.

v2 (Task 071A-v2 sweep)
    Adds a 4th auditor (``consolidation_breakout_risk``), tightens the
    peer-catchup conditions, and switches to a combo-based decision
    matrix. Thresholds and audit toggles are exposed via :class:`AuditConfig`.

The default ``audit_big_up_exclusion(row)`` call still reproduces v1
exactly; v2 is opt-in via ``audit_big_up_exclusion(row, config=...)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_bool(value: Any) -> bool | None:
    """Tolerant bool parser. Accepts native bool, ``"true"`` / ``"false"`` /
    ``"True"`` / ``"1"`` / ``"0"`` / ``""``. Returns ``None`` when truly
    missing so callers can distinguish "field absent" from "field is False"."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value != value:
            return None
        return bool(int(value))
    s = str(value).strip().lower()
    if s in ("true", "t", "1", "yes"):
        return True
    if s in ("false", "f", "0", "no"):
        return False
    return None


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _structure_contains(structure: Any, *needles: str) -> bool:
    """True if any needle appears in the structure label string."""
    if not isinstance(structure, str) or not structure:
        return False
    return any(n in structure for n in needles)


def _peer_avg_return(row: dict[str, Any]) -> float | None:
    parts: list[float] = []
    for key in ("NVDA_T_return", "SOXX_T_return", "QQQ_T_return"):
        v = _safe_float(row.get(key))
        if v is not None:
            parts.append(v)
    if not parts:
        return None
    return sum(parts) / len(parts)


def _peer_alignment(row: dict[str, Any]) -> str:
    return str(row.get("peer_alignment") or "").strip().lower() or "missing"


def _excluded_contains_big_up(row: dict[str, Any]) -> bool:
    raw = row.get("forced_excluded_states") or row.get("excluded_states") or ""
    if isinstance(raw, list):
        return "大涨" in raw
    if not isinstance(raw, str):
        return False
    parts = raw.split("|") if "|" in raw else (
        [p.strip().strip("'\"") for p in raw.strip("[]").split(",")]
        if raw.strip().startswith("[") else [raw]
    )
    return any(p.strip() == "大涨" for p in parts)


# ── configuration ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuditConfig:
    """Audit thresholds and feature toggles.

    ``AuditConfig()`` (all defaults) reproduces v1 behaviour exactly.

    * v2 (Task 071A-v2): set ``peer_catchup_version=2``,
      ``enable_consolidation=True``, ``decision_logic_version=2``.
    * v3 (Task 074): set ``enable_market_rebound=True``,
      ``enable_crisis_regime=True``, ``enable_low_sample=True``,
      ``decision_logic_version=3``. peer_catchup and consolidation are
      toggled OFF in this mode (proven harmful or non-discriminating
      in 071A-v1/v2 + Task 073 残差).
    """
    # auditor thresholds
    rebound_threshold: int = 3
    breakout_threshold: int = 4
    peer_catchup_threshold: int = 3
    consolidation_threshold: int = 3
    market_rebound_threshold: int = 2     # v3
    crisis_regime_threshold: int = 2      # v3
    low_sample_threshold: int = 1         # v3

    # v5 contradiction-detector thresholds (Task 084)
    macro_contradiction_threshold: int = 1
    earnings_post_window_threshold: int = 1
    sample_invalidation_threshold: int = 2
    macro_score_for_block: int = 4        # macro alone can block when score ≥ this

    # decision logic thresholds
    risk_flag_block_at: int = 2          # v1 only
    counter_downgrade_at: int = 2
    breakout_score_for_block: int = 5    # v2 + v3

    # feature toggles
    peer_catchup_version: int = 1        # 1 = original; 2 = v2 sweep
    enable_peer_catchup: bool = True      # v3 turns this OFF
    enable_consolidation: bool = False    # v2 only
    enable_market_rebound: bool = False   # v3
    enable_crisis_regime: bool = False    # v3
    enable_low_sample: bool = False       # v3
    enable_macro_contradiction: bool = False    # v5
    enable_earnings_post_window: bool = False   # v5
    enable_sample_invalidation: bool = False    # v5
    enable_old_signals: bool = True             # v5 — gates oversold + breakout in v5 mode
    decision_logic_version: int = 1      # 1 risk-count; 2 v2 combo; 3 v3 combo; 5 v5 contradiction

    def label(self) -> str:
        """Compact identifier for sweep output rows."""
        if self.decision_logic_version == 5:
            return (
                "v5"
                f"_macro{self.macro_contradiction_threshold}"
                f"_earnings{self.earnings_post_window_threshold}"
                f"_sample{self.sample_invalidation_threshold}"
                f"_oldsig{int(self.enable_old_signals)}"
            )
        if self.decision_logic_version == 3:
            return (
                "v3"
                f"_oversold{self.rebound_threshold}"
                f"_breakout{self.breakout_threshold}"
                f"_market{self.market_rebound_threshold}"
                f"_crisis{self.crisis_regime_threshold}"
                f"_lowsample{self.low_sample_threshold}"
            )
        return (
            f"v{self.decision_logic_version}"
            f"_oversold{self.rebound_threshold}"
            f"_breakout{self.breakout_threshold}"
            f"_peer{self.peer_catchup_threshold}"
            f"_consol{self.consolidation_threshold}"
            f"_pc{self.peer_catchup_version}"
            f"_consolEnabled{int(self.enable_consolidation)}"
        )


# Convenience defaults.
DEFAULT_V1_CONFIG = AuditConfig()
DEFAULT_V2_CONFIG = AuditConfig(
    rebound_threshold=3,
    breakout_threshold=3,
    peer_catchup_threshold=4,
    consolidation_threshold=4,
    peer_catchup_version=2,
    enable_consolidation=True,
    decision_logic_version=2,
)
DEFAULT_V3_CONFIG = AuditConfig(
    rebound_threshold=3,
    breakout_threshold=3,
    market_rebound_threshold=2,
    crisis_regime_threshold=2,
    low_sample_threshold=1,
    peer_catchup_threshold=999,         # never fires (kept for type-stability)
    consolidation_threshold=999,
    enable_peer_catchup=False,
    enable_consolidation=False,
    enable_market_rebound=True,
    enable_crisis_regime=True,
    enable_low_sample=True,
    decision_logic_version=3,
)
DEFAULT_V5_CONFIG = AuditConfig(
    rebound_threshold=3,
    breakout_threshold=3,
    macro_contradiction_threshold=1,
    earnings_post_window_threshold=1,
    sample_invalidation_threshold=2,
    macro_score_for_block=4,
    peer_catchup_threshold=999,
    consolidation_threshold=999,
    enable_peer_catchup=False,
    enable_consolidation=False,
    enable_market_rebound=False,
    enable_crisis_regime=False,
    enable_low_sample=False,
    enable_macro_contradiction=True,
    enable_earnings_post_window=True,
    enable_sample_invalidation=True,
    enable_old_signals=True,
    decision_logic_version=5,
)


# ── individual auditors ───────────────────────────────────────────────────────

def _audit_rebound_risk(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Auditor 1 — oversold rebound risk."""
    reasons: list[str] = []
    score = 0

    avgo_t = _safe_float(row.get("AVGO_T_return"))
    ret3 = _safe_float(row.get("ret3"))
    ret5 = _safe_float(row.get("ret5"))
    pos20 = _safe_float(row.get("pos20"))
    pos30 = _safe_float(row.get("pos30"))
    lower = _safe_float(row.get("lower_shadow"))
    structure = row.get("AVGO_T_structure")

    if avgo_t is not None and avgo_t <= -2.5:
        score += 1
        reasons.append(f"+1 AVGO_T_return={avgo_t:.2f}≤-2.5")
    if (ret3 is not None and ret3 <= -3.5) or (ret5 is not None and ret5 <= -5):
        score += 1
        reasons.append(f"+1 ret3/ret5 严重负偏 (ret3={ret3}, ret5={ret5})")
    if (pos20 is not None and pos20 <= 35) or (pos30 is not None and pos30 <= 40):
        score += 1
        reasons.append(f"+1 低位 (pos20={pos20}, pos30={pos30})")
    if (lower is not None and lower >= 0.35) or _structure_contains(structure, "低开高走"):
        score += 1
        reasons.append(f"+1 下方承接 (lower_shadow={lower}, structure={structure})")

    if _structure_contains(structure, "低开低走") and (lower is not None and lower < 0.2):
        score -= 1
        reasons.append("-1 低开低走且无下影承接")

    avg_peer = _peer_avg_return(row)
    if (
        _peer_alignment(row) == "unsupported"
        and avgo_t is not None
        and avg_peer is not None
        and avgo_t < avg_peer
    ):
        score -= 1
        reasons.append(f"-1 同行不支持且 AVGO 弱于同行均值 ({avgo_t:.2f}<{avg_peer:.2f})")

    return score, reasons


def _audit_breakout_continuation(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Auditor 2 — breakout continuation risk."""
    reasons: list[str] = []
    score = 0

    avgo_t = _safe_float(row.get("AVGO_T_return"))
    vol = _safe_float(row.get("vol_ratio20"))
    upper = _safe_float(row.get("upper_shadow"))
    pos20 = _safe_float(row.get("pos20"))
    ret5 = _safe_float(row.get("ret5"))
    structure = row.get("AVGO_T_structure")
    align = _peer_alignment(row)

    if avgo_t is not None and avgo_t >= 2:
        score += 1
        reasons.append(f"+1 当日强阳 AVGO_T={avgo_t:.2f}≥2")
    if vol is not None and 1.3 <= vol <= 3.5:
        score += 1
        reasons.append(f"+1 放量但未异常 (vol_ratio20={vol:.2f})")
    if upper is not None and upper <= 0.35:
        score += 1
        reasons.append(f"+1 上影短 (upper_shadow={upper:.2f}≤0.35)")
    if _structure_contains(structure, "高开高走", "低开高走", "平开走高"):
        score += 1
        reasons.append(f"+1 走高结构 ({structure})")
    if align in ("supported", "partial"):
        score += 1
        reasons.append(f"+1 同行 {align}")

    if pos20 is not None and pos20 >= 95:
        score -= 1
        reasons.append(f"-1 极高位 pos20={pos20:.1f}≥95")
    if ret5 is not None and ret5 >= 10:
        score -= 1
        reasons.append(f"-1 5日累计 ret5={ret5:.2f}≥10 已显著透支")
    if upper is not None and upper >= 0.6:
        score -= 1
        reasons.append(f"-1 长上影 upper_shadow={upper:.2f}≥0.6")

    return score, reasons


def _audit_peer_catchup_v1(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Auditor 3 (v1) — peer-catchup risk (original Task 071A spec)."""
    reasons: list[str] = []
    score = 0

    align = _peer_alignment(row)
    avgo_t = _safe_float(row.get("AVGO_T_return"))
    avg_peer = _peer_avg_return(row)
    pos20 = _safe_float(row.get("pos20"))
    upper = _safe_float(row.get("upper_shadow"))
    structure = row.get("AVGO_T_structure")

    if align == "supported":
        score += 1
        reasons.append("+1 peer_alignment=supported")
    if avgo_t is not None and avg_peer is not None and avgo_t < avg_peer:
        score += 1
        reasons.append(f"+1 AVGO_T={avgo_t:.2f} < peer_avg={avg_peer:.2f}")
    if avgo_t is not None and avgo_t > -2.5:
        score += 1
        reasons.append(f"+1 AVGO 未破位 ({avgo_t:.2f}>-2.5)")
    if pos20 is not None and pos20 < 85:
        score += 1
        reasons.append(f"+1 pos20={pos20:.1f}<85")

    if _structure_contains(structure, "高开低走"):
        score -= 1
        reasons.append("-1 高开低走 (走弱形态)")
    if upper is not None and upper >= 0.5:
        score -= 1
        reasons.append(f"-1 上影偏长 upper_shadow={upper:.2f}≥0.5")

    return score, reasons


def _audit_peer_catchup_v2(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Auditor 3 (v2) — tightened peer-catchup risk.

    Now requires both *peer strength* and *measurable AVGO underperformance*
    plus a sane mid-range posture. Designed to fire less and only on the
    pattern "peers明显走强 + AVGO 持平/小幅落后 + 不破位 + 中位".
    """
    reasons: list[str] = []
    score = 0

    align = _peer_alignment(row)
    avgo_t = _safe_float(row.get("AVGO_T_return"))
    avg_peer = _peer_avg_return(row)
    pos20 = _safe_float(row.get("pos20"))
    upper = _safe_float(row.get("upper_shadow"))
    structure = row.get("AVGO_T_structure")

    if align == "supported":
        score += 1
        reasons.append("+1 peer_alignment=supported")
    if avg_peer is not None and avg_peer >= 0.8:
        score += 1
        reasons.append(f"+1 peer_avg_return={avg_peer:.2f}≥+0.8")
    if avg_peer is not None and avgo_t is not None and (avg_peer - avgo_t) >= 1.0:
        score += 1
        reasons.append(f"+1 peer_avg − AVGO_T={avg_peer - avgo_t:.2f}≥1.0")
    if avgo_t is not None and -1.5 <= avgo_t <= 0.8:
        score += 1
        reasons.append(f"+1 AVGO_T={avgo_t:.2f} ∈ [-1.5, +0.8]")
    if pos20 is not None and 25 <= pos20 <= 80:
        score += 1
        reasons.append(f"+1 pos20={pos20:.1f} ∈ [25, 80]")

    if _structure_contains(structure, "高开低走"):
        score -= 1
        reasons.append("-1 高开低走 (走弱形态)")
    if upper is not None and upper >= 0.5:
        score -= 1
        reasons.append(f"-1 上影偏长 upper_shadow={upper:.2f}≥0.5")
    if avgo_t is not None and avgo_t <= -2.5:
        score -= 1
        reasons.append(f"-1 AVGO_T={avgo_t:.2f}≤-2.5 (已破位)")

    return score, reasons


def _audit_consolidation_breakout(row: dict[str, Any]) -> tuple[int, list[str]]:
    """Auditor 4 (v2 only) — consolidation-breakout risk.

    Designed to catch the pattern that v1 missed:
    缩量、中位、方向未决的震荡日不应被硬否定大涨。
    """
    reasons: list[str] = []
    score = 0

    avgo_t = _safe_float(row.get("AVGO_T_return"))
    vol = _safe_float(row.get("vol_ratio20"))
    pos20 = _safe_float(row.get("pos20"))
    upper = _safe_float(row.get("upper_shadow"))
    structure = row.get("AVGO_T_structure")
    align = _peer_alignment(row)
    avg_peer = _peer_avg_return(row)
    ret3 = _safe_float(row.get("ret3"))
    ret5 = _safe_float(row.get("ret5"))

    if avgo_t is not None and abs(avgo_t) <= 1.0:
        score += 1
        reasons.append(f"+1 |AVGO_T|={abs(avgo_t):.2f}≤1.0 中性")
    if vol is not None and vol <= 0.75:
        score += 1
        reasons.append(f"+1 极缩量 vol_ratio20={vol:.2f}≤0.75")
    if pos20 is not None and 30 <= pos20 <= 75:
        score += 1
        reasons.append(f"+1 pos20={pos20:.1f}∈[30,75]")
    if _structure_contains(structure, "平开震荡", "低开震荡", "高开震荡"):
        score += 1
        reasons.append(f"+1 震荡结构 ({structure})")
    if upper is not None and upper <= 0.5:
        score += 1
        reasons.append(f"+1 上影未严重 (upper_shadow={upper:.2f}≤0.5)")
    if align != "unsupported":
        score += 1
        reasons.append(f"+1 同行未明确转弱 (peer_alignment={align})")

    if (ret3 is not None and ret3 <= -3.5) or (ret5 is not None and ret5 <= -5):
        score -= 1
        reasons.append(f"-1 ret3/ret5 已严重负偏 (ret3={ret3}, ret5={ret5})")
    if _structure_contains(structure, "高开低走"):
        score -= 1
        reasons.append("-1 高开低走 走弱形态")
    if align == "unsupported" and avg_peer is not None and avg_peer < -0.5:
        score -= 1
        reasons.append(f"-1 同行明显转弱 (peer_avg={avg_peer:.2f}<-0.5)")

    return score, reasons


# ── v3 auditors (Task 074) ───────────────────────────────────────────────────

def _audit_market_rebound_softening(row: dict[str, Any]) -> tuple[int, list[str]]:
    """v3 auditor — market_rebound_softening.

    Softening signal: T-day market environment is in a rebound-candidate
    posture, so the system should not be allowed to confidently
    hard-exclude 大涨. This is **not** a 大涨 prediction; it widens the
    confidence interval.
    """
    reasons: list[str] = []
    score = 0

    is_rebound_cand = _safe_bool(row.get("is_market_rebound_candidate"))
    qqq_t = _safe_float(row.get("QQQ_T_return"))
    soxx_t = _safe_float(row.get("SOXX_T_return"))
    qqq_5d = _safe_float(row.get("qqq_5d_return"))
    soxx_5d = _safe_float(row.get("soxx_5d_return"))
    avgo_t = _safe_float(row.get("AVGO_T_return"))
    label = str(row.get("market_regime_label") or "").strip().lower()
    structure = row.get("AVGO_T_structure")
    lower = _safe_float(row.get("lower_shadow"))
    sample_conf = str(row.get("historical_sample_confidence") or "").strip().lower()
    big_up_rate = _safe_float(row.get("historical_big_up_rate"))

    if is_rebound_cand is True:
        score += 1
        reasons.append("+1 is_market_rebound_candidate=True")
    if qqq_t is not None and qqq_t < 0 and soxx_t is not None and soxx_t < 0:
        score += 1
        reasons.append(f"+1 QQQ_T={qqq_t:.2f} & SOXX_T={soxx_t:.2f} 同步下跌")
    if (qqq_5d is not None and qqq_5d <= -5) or (soxx_5d is not None and soxx_5d <= -6):
        score += 1
        reasons.append(f"+1 5日市场跌幅 (qqq_5d={qqq_5d}, soxx_5d={soxx_5d})")
    if label in ("high_vol", "crisis"):
        score += 1
        reasons.append(f"+1 regime={label}")
    if avgo_t is not None and avgo_t <= 0:
        score += 1
        reasons.append(f"+1 AVGO_T={avgo_t:.2f}≤0")

    if (
        _structure_contains(structure, "低开低走")
        and lower is not None and lower < 0.2
    ):
        score -= 1
        reasons.append("-1 低开低走且无下影承接 (real breakdown)")
    if (
        avgo_t is not None and qqq_t is not None and soxx_t is not None
        and avgo_t < qqq_t and avgo_t < soxx_t
    ):
        score -= 1
        reasons.append(
            f"-1 AVGO_T={avgo_t:.2f} 弱于 QQQ_T={qqq_t:.2f} 与 SOXX_T={soxx_t:.2f}"
            f"（AVGO-specific 走弱）"
        )
    if (
        sample_conf == "high"
        and big_up_rate is not None and big_up_rate == 0
    ):
        score -= 1
        reasons.append("-1 历史 high-confidence 显示 big_up_rate=0")

    return score, reasons


def _audit_crisis_regime_softening(row: dict[str, Any]) -> tuple[int, list[str]]:
    """v3 auditor — crisis_regime_softening.

    Softens hard exclusion in crisis / high-vol regimes. Some +1
    conditions intentionally overlap (e.g. ``is_crisis_regime`` is a
    strict subset of ``is_high_vol_regime`` is roughly a subset of
    ``vol≥1.5``) — the score therefore peaks on full-crisis days,
    naturally aligning with sweep thresholds 2-4.
    """
    reasons: list[str] = []
    score = 0

    is_crisis = _safe_bool(row.get("is_crisis_regime"))
    is_high_vol = _safe_bool(row.get("is_high_vol_regime"))
    label = str(row.get("market_regime_label") or "").strip().lower()
    qqq_v20 = _safe_float(row.get("qqq_20d_volatility"))
    qqq_t = _safe_float(row.get("QQQ_T_return"))
    soxx_t = _safe_float(row.get("SOXX_T_return"))
    avgo_t = _safe_float(row.get("AVGO_T_return"))
    lower = _safe_float(row.get("lower_shadow"))
    sample_conf = str(row.get("historical_sample_confidence") or "").strip().lower()
    big_up_rate = _safe_float(row.get("historical_big_up_rate"))

    if is_crisis is True:
        score += 1
        reasons.append("+1 is_crisis_regime=True")
    if is_high_vol is True:
        score += 1
        reasons.append("+1 is_high_vol_regime=True (≥75pct expanding)")
    if label == "crisis":
        score += 1
        reasons.append("+1 market_regime_label=crisis")
    if qqq_v20 is not None and qqq_v20 >= 1.5:
        score += 1
        reasons.append(f"+1 qqq_20d_volatility={qqq_v20:.2f}≥1.5 (absolute high)")
    if (
        (qqq_t is not None and abs(qqq_t) >= 1.5)
        or (soxx_t is not None and abs(soxx_t) >= 2.0)
    ):
        score += 1
        reasons.append("+1 大盘当日波动显著 (|QQQ|≥1.5 或 |SOXX|≥2.0)")

    if (
        avgo_t is not None and avgo_t <= -5
        and lower is not None and lower < 0.2
    ):
        score -= 1
        reasons.append("-1 AVGO 已破位 (AVGO_T≤-5 且 无下影承接)")
    if (
        sample_conf == "high"
        and big_up_rate is not None and big_up_rate < 0.03
    ):
        score -= 1
        reasons.append(f"-1 high-confidence 历史 big_up_rate={big_up_rate:.3f}<0.03")

    return score, reasons


def _audit_low_sample_confidence_softening(
    row: dict[str, Any],
) -> tuple[int, list[str]]:
    """v3 auditor — low_sample_confidence_softening.

    Softens hard exclusion when the historical-pattern evidence is thin.
    Contract: per Task 074 spec this auditor *cannot* single-handedly
    cause ``blocked_by_audit`` — that constraint is enforced by
    :func:`_decide_v3` (not here).
    """
    reasons: list[str] = []
    score = 0

    sample_conf = str(row.get("historical_sample_confidence") or "").strip().lower()
    match_count = _safe_float(row.get("historical_match_count"))
    big_up_count_raw = row.get("historical_big_up_count")
    big_up_count_missing = big_up_count_raw in (None, "", "None")
    big_up_rate = _safe_float(row.get("historical_big_up_rate"))
    p_big_up = _safe_float(row.get("p_大涨"))

    if sample_conf == "missing":
        score += 1
        reasons.append("+1 historical_sample_confidence=missing")
    if sample_conf == "low":
        score += 1
        reasons.append("+1 historical_sample_confidence=low")
    if match_count is None or match_count < 20:
        score += 1
        reasons.append(f"+1 historical_match_count={match_count}<20 或 null")
    if big_up_count_missing:
        score += 1
        reasons.append("+1 historical_big_up_count missing")
    if p_big_up is not None and p_big_up <= 0.01:
        score += 1
        reasons.append(f"+1 p_大涨={p_big_up:.4f}≤0.01")

    if sample_conf == "high":
        score -= 1
        reasons.append("-1 historical_sample_confidence=high")
    if match_count is not None and match_count >= 50:
        score -= 1
        reasons.append(f"-1 historical_match_count={int(match_count)}≥50")
    if (
        big_up_rate is not None and big_up_rate == 0
        and match_count is not None and match_count >= 50
    ):
        score -= 1
        reasons.append("-1 高样本量历史 big_up_rate=0 (强反证)")

    return score, reasons


# ── v5 auditors (Task 084 — contradiction detector) ────────────────────────

def _audit_macro_contradiction_softening(
    row: dict[str, Any],
) -> tuple[int, list[str]]:
    """v5 auditor — macro_contradiction_softening.

    Base trigger: ``macro_contradicts_big_up_exclusion`` must be True
    (i.e. macro environment is supportive AND p_大涨 ≤ 0.01). When the
    base is False/None the auditor returns score 0 with the reason
    "base trigger missing" so it never fires.
    """
    reasons: list[str] = []
    base_trigger = _safe_bool(row.get("macro_contradicts_big_up_exclusion"))
    if base_trigger is not True:
        return 0, ["base trigger missing (macro_contradicts_big_up_exclusion not True)"]

    score = 0

    # +1 for the base trigger itself (per spec optional +1 list)
    score += 1
    reasons.append("+1 macro_contradicts_big_up_exclusion")

    if _safe_bool(row.get("is_nq_short_term_oversold")) is True:
        score += 1
        reasons.append("+1 is_nq_short_term_oversold")
    if _safe_bool(row.get("is_nq_rebound_candidate")) is True:
        score += 1
        reasons.append("+1 is_nq_rebound_candidate")
    if _safe_bool(row.get("is_vix_spike")) is True:
        score += 1
        reasons.append("+1 is_vix_spike")
    macro_score = _safe_float(row.get("macro_risk_support_score"))
    if macro_score is not None and macro_score >= 3:
        score += 1
        reasons.append(f"+1 macro_risk_support_score={macro_score:.0f}≥3")
    if _safe_bool(row.get("is_market_rebound_candidate")) is True:
        score += 1
        reasons.append("+1 is_market_rebound_candidate")

    avgo_t = _safe_float(row.get("AVGO_T_return"))
    lower = _safe_float(row.get("lower_shadow"))
    if (
        avgo_t is not None and avgo_t <= -5
        and lower is not None and lower < 0.2
    ):
        score -= 1
        reasons.append("-1 AVGO_T≤-5 且无下影承接")
    sample_conf = str(row.get("historical_sample_confidence") or "").strip().lower()
    big_up_rate = _safe_float(row.get("historical_big_up_rate"))
    if sample_conf == "high" and big_up_rate is not None and big_up_rate == 0:
        score -= 1
        reasons.append("-1 historical high-confidence big_up_rate=0")

    return score, reasons


def _audit_earnings_post_window_softening(
    row: dict[str, Any],
) -> tuple[int, list[str]]:
    """v5 auditor — earnings_post_window_softening.

    Base trigger: ``is_post_earnings_window`` must be True. The post-hoc
    field ``is_earnings_gap_candidate`` is **explicitly NOT consumed**
    here (Task 077 / Task 078 forbid it as audit input).
    """
    reasons: list[str] = []
    base_trigger = _safe_bool(row.get("is_post_earnings_window"))
    if base_trigger is not True:
        return 0, ["base trigger missing (is_post_earnings_window not True)"]

    score = 0
    score += 1
    reasons.append("+1 is_post_earnings_window")

    eps_surprise = _safe_float(row.get("eps_surprise_last_quarter"))
    if eps_surprise is not None:
        if eps_surprise > 0:
            score += 1
            reasons.append(f"+1 eps_surprise={eps_surprise:.2f}>0")
        elif eps_surprise < 0:
            score -= 1
            reasons.append(f"-1 eps_surprise={eps_surprise:.2f}<0")

    if _safe_bool(row.get("is_near_earnings")) is True:
        score += 1
        reasons.append("+1 is_near_earnings")

    sample_conf = str(row.get("historical_sample_confidence") or "").strip().lower()
    big_up_rate = _safe_float(row.get("historical_big_up_rate"))
    if sample_conf == "high" and big_up_rate is not None and big_up_rate == 0:
        score -= 1
        reasons.append("-1 historical high-confidence big_up_rate=0")

    return score, reasons


def _audit_sample_confidence_invalidation(
    row: dict[str, Any],
) -> tuple[int, list[str]]:
    """v5 auditor — sample_confidence_invalidation.

    Detects: system gives p_大涨 ≈ 0 but the historical sample base is
    too thin to support that confidence → exclusion is unreliable.
    """
    reasons: list[str] = []
    score = 0

    sample_conf = str(row.get("historical_sample_confidence") or "").strip().lower()
    match_count = _safe_float(row.get("historical_match_count"))
    big_up_rate = _safe_float(row.get("historical_big_up_rate"))
    p_big_up = _safe_float(row.get("p_大涨"))
    score_zeroed = _safe_bool(row.get("score_distribution_zeroed"))

    if sample_conf in ("missing", "low"):
        score += 1
        reasons.append(f"+1 sample_confidence={sample_conf}")
    if match_count is None or (match_count is not None and match_count < 20):
        score += 1
        reasons.append(f"+1 match_count={match_count}<20 或 null")
    if p_big_up is not None and p_big_up <= 0.01:
        score += 1
        reasons.append(f"+1 p_大涨={p_big_up:.4f}≤0.01")
    if score_zeroed is True:
        score += 1
        reasons.append("+1 score_distribution_zeroed")

    if sample_conf == "high":
        score -= 1
        reasons.append("-1 sample_confidence=high")
    if match_count is not None and match_count >= 50:
        score -= 1
        reasons.append(f"-1 match_count={int(match_count)}≥50")
    if (
        big_up_rate is not None and big_up_rate == 0
        and match_count is not None and match_count >= 50
    ):
        score -= 1
        reasons.append("-1 high-sample big_up_rate=0 (strong veto)")

    return score, reasons


# ── counter flags ─────────────────────────────────────────────────────────────

def _counter_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []

    structure = row.get("AVGO_T_structure")
    avgo_t = _safe_float(row.get("AVGO_T_return"))
    lower = _safe_float(row.get("lower_shadow"))
    upper = _safe_float(row.get("upper_shadow"))
    pos20 = _safe_float(row.get("pos20"))
    align = _peer_alignment(row)
    avg_peer = _peer_avg_return(row)

    if (
        _structure_contains(structure, "低开低走")
        and lower is not None and lower < 0.2
        and avgo_t is not None and avgo_t <= -2.5
    ):
        flags.append("continued_breakdown_risk")

    if pos20 is not None and pos20 >= 95 and upper is not None and upper >= 0.5:
        flags.append("exhaustion_risk")

    if (
        align == "unsupported"
        and avgo_t is not None
        and avg_peer is not None
        and avgo_t < avg_peer
    ):
        flags.append("peer_drag_risk")

    return flags


# ── decision matrix ───────────────────────────────────────────────────────────

def _decide_v1(
    risk_flags: list[str],
    counter_flags: list[str],
    auditor_scores: dict[str, int],
    config: AuditConfig,
) -> tuple[str, str]:
    if len(risk_flags) >= config.risk_flag_block_at:
        decision = "blocked_by_audit"
    elif len(risk_flags) == 1:
        decision = "soft_excluded"
    else:
        decision = "hard_excluded"

    downgrade = ""
    if len(counter_flags) >= config.counter_downgrade_at:
        if decision == "blocked_by_audit":
            decision = "soft_excluded"
            downgrade = "≥2 counter_flags → blocked 降级为 soft"
        elif decision == "soft_excluded":
            decision = "hard_excluded"
            downgrade = "≥2 counter_flags → soft 降级为 hard"
    return decision, downgrade


def _decide_v2(
    risk_flags: list[str],
    counter_flags: list[str],
    auditor_scores: dict[str, int],
    config: AuditConfig,
) -> tuple[str, str]:
    """Combo-based decision matrix per Task 071A-v2 §3.

    * 0 risk flags                                  → hard_excluded
    * 1 risk flag (any kind)                        → soft_excluded
    * ≥2 risk flags BUT no qualifying combo        → soft_excluded
    * Qualifying combos that do allow blocked:
        - oversold_rebound_risk + peer_catchup_risk
        - oversold_rebound_risk + consolidation_breakout_risk AND no strong counter
        - breakout_continuation_risk AND breakout_score >= 5
        - ≥3 risk flags AND counter_count == 0
    * counter_count >= 2 always downgrades one notch.
    """
    n_risk = len(risk_flags)
    flags = set(risk_flags)
    n_counter = len(counter_flags)

    if n_risk == 0:
        return "hard_excluded", ""
    if n_risk == 1:
        return "soft_excluded", ""

    decision = "soft_excluded"
    note = ""

    breakout_score = auditor_scores.get("breakout", 0)

    if {"oversold_rebound_risk", "peer_catchup_risk"} <= flags:
        decision = "blocked_by_audit"
        note = "combo: oversold + peer_catchup"
    elif (
        {"oversold_rebound_risk", "consolidation_breakout_risk"} <= flags
        and n_counter == 0
    ):
        decision = "blocked_by_audit"
        note = "combo: oversold + consolidation (no counter)"
    elif (
        "breakout_continuation_risk" in flags
        and breakout_score >= config.breakout_score_for_block
    ):
        decision = "blocked_by_audit"
        note = f"breakout_score={breakout_score}≥{config.breakout_score_for_block}"
    elif n_risk >= 3 and n_counter == 0:
        decision = "blocked_by_audit"
        note = "≥3 risk flags, no counter"

    downgrade = ""
    if n_counter >= config.counter_downgrade_at:
        if decision == "blocked_by_audit":
            decision = "soft_excluded"
            downgrade = "≥2 counter_flags → blocked 降级为 soft"
        elif decision == "soft_excluded":
            decision = "hard_excluded"
            downgrade = "≥2 counter_flags → soft 降级为 hard"

    if note and downgrade:
        return decision, f"{note}; {downgrade}"
    return decision, note or downgrade


def _decide_v3(
    risk_flags: list[str],
    counter_flags: list[str],
    auditor_scores: dict[str, int],
    config: AuditConfig,
) -> tuple[str, str]:
    """Task 074 v3 decision matrix.

    Single-flag rule: any one risk flag → ``soft_excluded``.
    ``low_sample_confidence_softening`` *cannot* be the basis for a 2-way
    blocked combo.

    blocked combos:
        * {oversold, market_rebound}
        * {oversold, crisis_regime}
        * breakout AND breakout_score ≥ ``breakout_score_for_block``
        * {market_rebound, crisis_regime, low_sample}
        * ≥3 risk flags AND counter_count == 0
    """
    n_risk = len(risk_flags)
    flags = set(risk_flags)
    n_counter = len(counter_flags)

    if n_risk == 0:
        return "hard_excluded", ""
    if n_risk == 1:
        return "soft_excluded", ""

    decision = "soft_excluded"
    note = ""

    breakout_score = auditor_scores.get("breakout", 0)

    if {"oversold_rebound_risk", "market_rebound_softening"} <= flags:
        decision = "blocked_by_audit"
        note = "combo: oversold + market_rebound"
    elif {"oversold_rebound_risk", "crisis_regime_softening"} <= flags:
        decision = "blocked_by_audit"
        note = "combo: oversold + crisis_regime"
    elif (
        "breakout_continuation_risk" in flags
        and breakout_score >= config.breakout_score_for_block
    ):
        decision = "blocked_by_audit"
        note = f"breakout_score={breakout_score}≥{config.breakout_score_for_block}"
    elif {
        "market_rebound_softening",
        "crisis_regime_softening",
        "low_sample_confidence_softening",
    } <= flags:
        decision = "blocked_by_audit"
        note = "combo: market_rebound + crisis_regime + low_sample"
    elif n_risk >= 3 and n_counter == 0:
        decision = "blocked_by_audit"
        note = "≥3 risk flags, no counter"

    downgrade = ""
    if n_counter >= config.counter_downgrade_at:
        if decision == "blocked_by_audit":
            decision = "soft_excluded"
            downgrade = "≥2 counter_flags → blocked 降级为 soft"
        elif decision == "soft_excluded":
            decision = "hard_excluded"
            downgrade = "≥2 counter_flags → soft 降级为 hard"

    if note and downgrade:
        return decision, f"{note}; {downgrade}"
    return decision, note or downgrade


def _decide_v5(
    risk_flags: list[str],
    counter_flags: list[str],
    auditor_scores: dict[str, int],
    config: AuditConfig,
) -> tuple[str, str]:
    """Task 084 v5 contradiction-detector decision matrix.

    Single-flag rule: any one risk flag → ``soft_excluded``. Old auxiliary
    flags (oversold / breakout) cannot single-handedly cause blocking;
    that constraint is implicit because the spec's blocked combos all
    name v5 core flags only.

    Blocked combos:
        * {macro_contradiction, earnings_post_window}
        * {macro_contradiction, sample_confidence_invalidation}
        * {earnings_post_window, sample_confidence_invalidation}
        * 3 core flags simultaneously (subsumed by pair combos)
        * macro_contradiction AND macro_contradiction_score ≥
          ``config.macro_score_for_block``
        * n_risk ≥ 3 AND n_counter == 0

    Counter ≥ 2 → blocked→soft, soft→hard.
    """
    n_risk = len(risk_flags)
    flags = set(risk_flags)
    n_counter = len(counter_flags)
    macro_score = auditor_scores.get("macro_contradiction", 0)

    if n_risk == 0:
        return "hard_excluded", ""

    # Default: any risk flag → soft. Specific blocked combos and the
    # single-macro-strong-score exception override below.
    decision = "soft_excluded"
    note = ""

    if {"macro_contradiction_softening", "earnings_post_window_softening"} <= flags:
        decision = "blocked_by_audit"
        note = "combo: macro + earnings"
    elif {"macro_contradiction_softening", "sample_confidence_invalidation"} <= flags:
        decision = "blocked_by_audit"
        note = "combo: macro + sample"
    elif {"earnings_post_window_softening", "sample_confidence_invalidation"} <= flags:
        decision = "blocked_by_audit"
        note = "combo: earnings + sample"
    elif (
        "macro_contradiction_softening" in flags
        and macro_score >= config.macro_score_for_block
    ):
        decision = "blocked_by_audit"
        note = f"macro_score={macro_score}≥{config.macro_score_for_block}"
    elif n_risk >= 3 and n_counter == 0:
        decision = "blocked_by_audit"
        note = "≥3 risk flags, no counter"

    downgrade = ""
    if n_counter >= config.counter_downgrade_at:
        if decision == "blocked_by_audit":
            decision = "soft_excluded"
            downgrade = "≥2 counter_flags → blocked 降级为 soft"
        elif decision == "soft_excluded":
            decision = "hard_excluded"
            downgrade = "≥2 counter_flags → soft 降级为 hard"

    if note and downgrade:
        return decision, f"{note}; {downgrade}"
    return decision, note or downgrade


# ── public API ────────────────────────────────────────────────────────────────

# Module-level constants kept for v1 backward-compatibility.
REBOUND_THRESHOLD = DEFAULT_V1_CONFIG.rebound_threshold
BREAKOUT_THRESHOLD = DEFAULT_V1_CONFIG.breakout_threshold
PEER_CATCHUP_THRESHOLD = DEFAULT_V1_CONFIG.peer_catchup_threshold
RISK_FLAG_BLOCK_AT = DEFAULT_V1_CONFIG.risk_flag_block_at
COUNTER_DOWNGRADE_AT = DEFAULT_V1_CONFIG.counter_downgrade_at


def audit_big_up_exclusion(
    row_or_context: dict[str, Any],
    *,
    config: AuditConfig | None = None,
) -> dict[str, Any]:
    """Audit one row's would-be 硬否定大涨 decision.

    See module docstring. ``config=None`` reproduces v1 behaviour exactly.
    Pass :data:`DEFAULT_V2_CONFIG` (or a custom :class:`AuditConfig`) for
    v2 behaviour (sweep target).
    """
    cfg = config or DEFAULT_V1_CONFIG
    row = dict(row_or_context or {})
    excluded_big_up = _excluded_contains_big_up(row)
    original_decision = "hard_excluded" if excluded_big_up else "not_excluded"

    if not excluded_big_up:
        return {
            "original_decision": original_decision,
            "final_decision": "not_excluded",
            "audit_score": 0,
            "blocked": False,
            "softened": False,
            "risk_flags": [],
            "counter_flags": [],
            "reason": "本行 forced_excluded_states 不包含 大涨；审核未触发。",
            "auditor_scores": {},
            "auditor_reasons": {},
            "config_label": cfg.label(),
        }

    # Always-on auditors (gated off in v5 if enable_old_signals=False).
    if cfg.decision_logic_version == 5 and not cfg.enable_old_signals:
        rebound_score, rebound_reasons = 0, ["disabled in v5_no_old_signals"]
        breakout_score, breakout_reasons = 0, ["disabled in v5_no_old_signals"]
    else:
        rebound_score, rebound_reasons = _audit_rebound_risk(row)
        breakout_score, breakout_reasons = _audit_breakout_continuation(row)

    # peer_catchup (v1/v2 only — v3 disables via enable_peer_catchup=False).
    if cfg.enable_peer_catchup:
        if cfg.peer_catchup_version == 2:
            peer_score, peer_reasons = _audit_peer_catchup_v2(row)
        else:
            peer_score, peer_reasons = _audit_peer_catchup_v1(row)
    else:
        peer_score, peer_reasons = 0, []

    # consolidation (v2 only).
    if cfg.enable_consolidation:
        consol_score, consol_reasons = _audit_consolidation_breakout(row)
    else:
        consol_score, consol_reasons = 0, []

    # v3 auditors.
    if cfg.enable_market_rebound:
        market_score, market_reasons = _audit_market_rebound_softening(row)
    else:
        market_score, market_reasons = 0, []
    if cfg.enable_crisis_regime:
        crisis_score, crisis_reasons = _audit_crisis_regime_softening(row)
    else:
        crisis_score, crisis_reasons = 0, []
    if cfg.enable_low_sample:
        low_sample_score, low_sample_reasons = _audit_low_sample_confidence_softening(row)
    else:
        low_sample_score, low_sample_reasons = 0, []

    # v5 auditors.
    if cfg.enable_macro_contradiction:
        macro_contra_score, macro_contra_reasons = _audit_macro_contradiction_softening(row)
    else:
        macro_contra_score, macro_contra_reasons = 0, []
    if cfg.enable_earnings_post_window:
        earnings_post_score, earnings_post_reasons = _audit_earnings_post_window_softening(row)
    else:
        earnings_post_score, earnings_post_reasons = 0, []
    if cfg.enable_sample_invalidation:
        sample_inv_score, sample_inv_reasons = _audit_sample_confidence_invalidation(row)
    else:
        sample_inv_score, sample_inv_reasons = 0, []

    risk_flags: list[str] = []
    if rebound_score >= cfg.rebound_threshold:
        risk_flags.append("oversold_rebound_risk")
    if breakout_score >= cfg.breakout_threshold:
        risk_flags.append("breakout_continuation_risk")
    if cfg.enable_peer_catchup and peer_score >= cfg.peer_catchup_threshold:
        risk_flags.append("peer_catchup_risk")
    if cfg.enable_consolidation and consol_score >= cfg.consolidation_threshold:
        risk_flags.append("consolidation_breakout_risk")
    if cfg.enable_market_rebound and market_score >= cfg.market_rebound_threshold:
        risk_flags.append("market_rebound_softening")
    if cfg.enable_crisis_regime and crisis_score >= cfg.crisis_regime_threshold:
        risk_flags.append("crisis_regime_softening")
    if cfg.enable_low_sample and low_sample_score >= cfg.low_sample_threshold:
        risk_flags.append("low_sample_confidence_softening")
    if cfg.enable_macro_contradiction and macro_contra_score >= cfg.macro_contradiction_threshold:
        risk_flags.append("macro_contradiction_softening")
    if cfg.enable_earnings_post_window and earnings_post_score >= cfg.earnings_post_window_threshold:
        risk_flags.append("earnings_post_window_softening")
    if cfg.enable_sample_invalidation and sample_inv_score >= cfg.sample_invalidation_threshold:
        risk_flags.append("sample_confidence_invalidation")

    counter_flags = _counter_flags(row)

    auditor_scores = {
        "rebound": rebound_score,
        "breakout": breakout_score,
    }
    if cfg.enable_peer_catchup:
        auditor_scores["peer_catchup"] = peer_score
    if cfg.enable_consolidation:
        auditor_scores["consolidation"] = consol_score
    if cfg.enable_market_rebound:
        auditor_scores["market_rebound"] = market_score
    if cfg.enable_crisis_regime:
        auditor_scores["crisis_regime"] = crisis_score
    if cfg.enable_low_sample:
        auditor_scores["low_sample"] = low_sample_score
    if cfg.enable_macro_contradiction:
        auditor_scores["macro_contradiction"] = macro_contra_score
    if cfg.enable_earnings_post_window:
        auditor_scores["earnings_post_window"] = earnings_post_score
    if cfg.enable_sample_invalidation:
        auditor_scores["sample_invalidation"] = sample_inv_score

    if cfg.decision_logic_version == 5:
        final_decision, note = _decide_v5(risk_flags, counter_flags, auditor_scores, cfg)
    elif cfg.decision_logic_version == 3:
        final_decision, note = _decide_v3(risk_flags, counter_flags, auditor_scores, cfg)
    elif cfg.decision_logic_version == 2:
        final_decision, note = _decide_v2(risk_flags, counter_flags, auditor_scores, cfg)
    else:
        final_decision, note = _decide_v1(risk_flags, counter_flags, auditor_scores, cfg)

    audit_score = len(risk_flags) - len(counter_flags)

    reason_parts: list[str] = []
    score_chunks = [f"rebound={rebound_score}", f"breakout={breakout_score}"]
    if cfg.enable_peer_catchup:
        score_chunks.append(f"peer_catchup={peer_score}")
    if cfg.enable_consolidation:
        score_chunks.append(f"consolidation={consol_score}")
    if cfg.enable_market_rebound:
        score_chunks.append(f"market_rebound={market_score}")
    if cfg.enable_crisis_regime:
        score_chunks.append(f"crisis_regime={crisis_score}")
    if cfg.enable_low_sample:
        score_chunks.append(f"low_sample={low_sample_score}")
    if cfg.enable_macro_contradiction:
        score_chunks.append(f"macro_contradiction={macro_contra_score}")
    if cfg.enable_earnings_post_window:
        score_chunks.append(f"earnings_post_window={earnings_post_score}")
    if cfg.enable_sample_invalidation:
        score_chunks.append(f"sample_invalidation={sample_inv_score}")
    score_repr = ", ".join(score_chunks)
    reason_parts.append(f"risk_flags={risk_flags or '∅'} ({score_repr})")
    reason_parts.append(f"counter_flags={counter_flags or '∅'}")
    reason_parts.append(
        "决策：" + {
            "hard_excluded": "审核同意硬否定 (0 risk flags 或被 counter 抵消)",
            "soft_excluded": "审核降级为 soft",
            "blocked_by_audit": "审核阻止硬否定",
        }[final_decision]
    )
    if note:
        reason_parts.append(note)

    auditor_reasons = {
        "rebound": rebound_reasons,
        "breakout": breakout_reasons,
    }
    if cfg.enable_peer_catchup:
        auditor_reasons["peer_catchup"] = peer_reasons
    if cfg.enable_consolidation:
        auditor_reasons["consolidation"] = consol_reasons
    if cfg.enable_market_rebound:
        auditor_reasons["market_rebound"] = market_reasons
    if cfg.enable_crisis_regime:
        auditor_reasons["crisis_regime"] = crisis_reasons
    if cfg.enable_low_sample:
        auditor_reasons["low_sample"] = low_sample_reasons
    if cfg.enable_macro_contradiction:
        auditor_reasons["macro_contradiction"] = macro_contra_reasons
    if cfg.enable_earnings_post_window:
        auditor_reasons["earnings_post_window"] = earnings_post_reasons
    if cfg.enable_sample_invalidation:
        auditor_reasons["sample_invalidation"] = sample_inv_reasons

    return {
        "original_decision": original_decision,
        "final_decision": final_decision,
        "audit_score": audit_score,
        "blocked": final_decision == "blocked_by_audit",
        "softened": final_decision == "soft_excluded",
        "risk_flags": risk_flags,
        "counter_flags": counter_flags,
        "reason": "; ".join(reason_parts),
        "auditor_scores": auditor_scores,
        "auditor_reasons": auditor_reasons,
        "config_label": cfg.label(),
    }


def audit_iterable(
    rows: Iterable[dict[str, Any]],
    *,
    config: AuditConfig | None = None,
) -> list[dict[str, Any]]:
    """Convenience: run :func:`audit_big_up_exclusion` over many rows."""
    return [audit_big_up_exclusion(row, config=config) for row in rows]


__all__ = (
    "AuditConfig",
    "DEFAULT_V1_CONFIG",
    "DEFAULT_V2_CONFIG",
    "DEFAULT_V3_CONFIG",
    "DEFAULT_V5_CONFIG",
    "audit_big_up_exclusion",
    "audit_iterable",
    "REBOUND_THRESHOLD",
    "BREAKOUT_THRESHOLD",
    "PEER_CATCHUP_THRESHOLD",
    "RISK_FLAG_BLOCK_AT",
    "COUNTER_DOWNGRADE_AT",
)
