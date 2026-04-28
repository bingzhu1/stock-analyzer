"""Independent AVGO recent-window primary analysis layer.

This module only analyzes the target symbol's own recent data. It does not use
peer, historical probability, memory, or AI inputs.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from services.data_query import load_symbol_data


_REQUIRED_COLUMNS = ("Date", "High", "Low", "Close", "Volume")
_ANALYSIS_FIELDS = ["Open", "High", "Low", "Close", "Volume", "Ret5", "Pos30", "PosLabel", "StageLabel"]


def _unknown_result(
    *,
    symbol: str,
    lookback_days: int,
    target_date: str | None,
    warnings: list[str],
    summary: str,
    days_used: int = 0,
) -> dict[str, Any]:
    return {
        "kind": "primary_20day_analysis",
        "symbol": symbol,
        "lookback_days": lookback_days,
        "target_date": target_date,
        "ready": False,
        "direction": "unknown",
        "confidence": "unknown",
        "position_label": "unknown",
        "stage_label": "unknown",
        "volume_state": "unknown",
        "summary": summary,
        "basis": ["最近20天主分析不可用。"],
        "warnings": warnings,
        "features": {
            "latest_close": None,
            "ret_5d": None,
            "ret_10d": None,
            "pos_20d": None,
            "high_20d": None,
            "low_20d": None,
            "vol_ratio_5d": None,
            "days_used": days_used,
        },
    }


def _safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


def _position_label(pos_20d: float | None, fallback: Any = None) -> str:
    text = str(fallback).strip() if fallback is not None and not pd.isna(fallback) else ""
    if text and text != "—":
        return text
    if pos_20d is None:
        return "unknown"
    if pos_20d >= 67:
        return "高位"
    if pos_20d < 33:
        return "低位"
    return "中位"


def _volume_state(vol_ratio_5d: float | None) -> str:
    if vol_ratio_5d is None:
        return "unknown"
    if vol_ratio_5d >= 1.15:
        return "放量"
    if vol_ratio_5d <= 0.85:
        return "缩量"
    return "正常"


def _stage_label(row: pd.Series, ret_5d: float | None, pos_20d: float | None, volume_state: str) -> str:
    stage = row.get("StageLabel")
    if stage is not None and not pd.isna(stage) and str(stage).strip() not in {"", "—"}:
        return str(stage).strip()
    if ret_5d is None or pos_20d is None:
        return "unknown"
    if pos_20d >= 75 and ret_5d < -1.5:
        return "衰竭风险"
    if ret_5d >= 4 and volume_state == "放量":
        return "启动"
    if ret_5d >= 2:
        return "延续"
    if abs(ret_5d) < 2:
        return "整理"
    return "分歧"


def _direction(ret_5d: float | None, ret_10d: float | None, pos_20d: float | None, stage_label: str) -> str:
    score = 0
    if ret_5d is not None:
        if ret_5d >= 2:
            score += 1
        elif ret_5d <= -2:
            score -= 1
    if ret_10d is not None:
        if ret_10d >= 3:
            score += 1
        elif ret_10d <= -3:
            score -= 1
    if pos_20d is not None:
        if pos_20d >= 67:
            score += 1
        elif pos_20d < 33:
            score -= 1
    if stage_label in {"启动", "延续", "加速"}:
        score += 1
    elif stage_label == "衰竭风险":
        score -= 1

    if score >= 2:
        return "偏多"
    if score <= -2:
        return "偏空"
    return "中性"


def _confidence(direction: str, days_used: int, ret_5d: float | None, ret_10d: float | None) -> str:
    if direction == "unknown":
        return "unknown"
    if days_used < 20:
        return "low"
    strength = 0.0
    if ret_5d is not None:
        strength += abs(ret_5d)
    if ret_10d is not None:
        strength += abs(ret_10d) / 2
    if direction != "中性" and strength >= 7:
        return "high"
    if direction != "中性" and strength >= 3:
        return "medium"
    return "low"


def _build_basis(
    *,
    ret_5d: float | None,
    ret_10d: float | None,
    pos_20d: float | None,
    volume_state: str,
    vol_ratio_5d: float | None,
    stage_label: str,
    direction: str,
) -> list[str]:
    basis: list[str] = []
    if ret_5d is not None:
        basis.append(f"最近5日收益为 {ret_5d:+.2f}%。")
    if ret_10d is not None:
        basis.append(f"最近10日收益为 {ret_10d:+.2f}%。")
    if pos_20d is not None:
        basis.append(f"当前价格位于20日区间约 {pos_20d:.1f}% 位置。")
    if vol_ratio_5d is not None:
        basis.append(f"当前量能约为5日均量的 {vol_ratio_5d:.2f} 倍，状态为{volume_state}。")
    basis.append(f"简化阶段标签为{stage_label}。")
    basis.append(f"主分析方向信号归纳为{direction}。")
    return basis[:5]


def build_primary_20day_analysis(
    *,
    symbol: str = "AVGO",
    lookback_days: int = 20,
    target_date: str | None = None,
    data: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Build a stable primary analysis from one symbol's recent data."""
    clean_symbol = str(symbol or "AVGO").strip().upper() or "AVGO"
    warnings: list[str] = []

    try:
        if data is not None:
            df = data.copy()
        elif target_date:
            # When target_date is provided, load all rows and slice below;
            # the live "latest N rows" path would skip past target_date.
            df = load_symbol_data(
                clean_symbol,
                window=0,
                fields=_ANALYSIS_FIELDS,
            )
        else:
            df = load_symbol_data(
                clean_symbol,
                window=lookback_days,
                fields=_ANALYSIS_FIELDS,
            )
    except Exception as exc:
        return _unknown_result(
            symbol=clean_symbol,
            lookback_days=lookback_days,
            target_date=target_date,
            warnings=[f"最近20天主分析不可用：{exc}"],
            summary="最近20天主分析不可用，数据加载失败。",
        )

    if df is None or df.empty:
        return _unknown_result(
            symbol=clean_symbol,
            lookback_days=lookback_days,
            target_date=target_date,
            warnings=["最近20天主分析不可用：输入数据为空。"],
            summary="最近20天主分析不可用，输入数据为空。",
        )

    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return _unknown_result(
            symbol=clean_symbol,
            lookback_days=lookback_days,
            target_date=target_date,
            warnings=[f"最近20天主分析缺少关键字段：{', '.join(missing)}。"],
            summary="最近20天主分析不可用，关键字段缺失。",
            days_used=int(len(df)),
        )

    # When target_date is provided, restrict to rows on/before that date so the
    # analysis sees only data available as-of that date. Live behaviour (no
    # filter) is preserved when target_date is None.
    if target_date and "Date" in df.columns:
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"] <= pd.to_datetime(target_date)].reset_index(drop=True)
        if df.empty:
            return _unknown_result(
                symbol=clean_symbol,
                lookback_days=lookback_days,
                target_date=target_date,
                warnings=[f"最近20天主分析不可用：{target_date} 之前没有可用数据。"],
                summary="最近20天主分析不可用，as-of 日期之前没有数据。",
            )

    df = df.copy().tail(max(int(lookback_days or 20), 1)).reset_index(drop=True)
    days_used = int(len(df))
    if days_used < lookback_days:
        warnings.append(f"最近20天主分析样本不足：仅使用 {days_used}/{lookback_days} 天。")

    latest = df.iloc[-1]
    close = pd.to_numeric(df["Close"], errors="coerce")
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    volume = pd.to_numeric(df["Volume"], errors="coerce")

    latest_close = _safe_float(close.iloc[-1])
    high_20d = _safe_float(high.max())
    low_20d = _safe_float(low.min())
    ret_5d = None
    ret_10d = None
    if latest_close is not None and days_used > 5:
        base = _safe_float(close.iloc[-6])
        if base:
            ret_5d = (latest_close / base - 1) * 100
    if latest_close is not None and days_used > 10:
        base = _safe_float(close.iloc[-11])
        if base:
            ret_10d = (latest_close / base - 1) * 100

    pos_20d = None
    if latest_close is not None and high_20d is not None and low_20d is not None and high_20d > low_20d:
        pos_20d = (latest_close - low_20d) / (high_20d - low_20d) * 100

    vol_ratio_5d = None
    latest_volume = _safe_float(volume.iloc[-1])
    vol5 = volume.tail(5).dropna()
    if latest_volume is not None and len(vol5) > 0:
        avg = _safe_float(vol5.mean())
        if avg:
            vol_ratio_5d = latest_volume / avg

    if not any(value is not None for value in (latest_close, high_20d, low_20d, ret_5d, ret_10d, vol_ratio_5d)):
        return _unknown_result(
            symbol=clean_symbol,
            lookback_days=lookback_days,
            target_date=target_date,
            warnings=["最近20天主分析不可用：High/Low/Close/Volume 数值字段不可用，无法形成主分析。"],
            summary="最近20天主分析不可用，数值字段不可用。",
            days_used=days_used,
        )

    position_label = _position_label(pos_20d, latest.get("PosLabel"))
    volume_state = _volume_state(vol_ratio_5d)
    stage_label = _stage_label(latest, ret_5d, pos_20d, volume_state)
    direction = _direction(ret_5d, ret_10d, pos_20d, stage_label)
    confidence = _confidence(direction, days_used, ret_5d, ret_10d)
    features = {
        "latest_close": _round(latest_close),
        "ret_5d": _round(ret_5d),
        "ret_10d": _round(ret_10d),
        "pos_20d": _round(pos_20d, 1),
        "high_20d": _round(high_20d),
        "low_20d": _round(low_20d),
        "vol_ratio_5d": _round(vol_ratio_5d, 2),
        "days_used": days_used,
    }
    basis = _build_basis(
        ret_5d=features["ret_5d"],
        ret_10d=features["ret_10d"],
        pos_20d=features["pos_20d"],
        volume_state=volume_state,
        vol_ratio_5d=features["vol_ratio_5d"],
        stage_label=stage_label,
        direction=direction,
    )
    resolved_target_date = target_date
    if not resolved_target_date and "Date" in df.columns:
        resolved_target_date = str(latest.get("Date"))
    summary = (
        f"{clean_symbol} 最近{days_used}天主分析：方向{direction}，"
        f"置信度{confidence}，位置{position_label}，阶段{stage_label}，量能{volume_state}。"
    )
    return {
        "kind": "primary_20day_analysis",
        "symbol": clean_symbol,
        "lookback_days": lookback_days,
        "target_date": resolved_target_date,
        "ready": True,
        "direction": direction,
        "confidence": confidence,
        "position_label": position_label,
        "stage_label": stage_label,
        "volume_state": volume_state,
        "summary": summary,
        "basis": basis,
        "warnings": warnings,
        "features": features,
    }
