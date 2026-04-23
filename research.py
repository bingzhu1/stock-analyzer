# -*- coding: utf-8 -*-
"""
research.py - Minimal Research v1 layer for the AVGO analyzer.

Research v1 uses manually pasted headlines/snippets/notes plus the current
ScanResult. It does not scrape, call APIs, or replace Scan. It only comments on
whether the pasted narrative reinforces, weakens, or does not change Scan.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, TypedDict


class ResearchResult(TypedDict):
    symbol: str
    research_timestamp: str
    source_count: int
    source_types_summary: dict[str, int]
    topic_tags: list[str]
    sentiment_bias: str
    confidence: str
    catalyst_detected: bool
    catalyst_summary: str
    peer_context_summary: str
    market_narrative_summary: str
    research_bias_adjustment: str
    notes: str


_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "AI": ("ai", "artificial intelligence", "genai", "gpu", "accelerator"),
    "semis": ("semiconductor", "semis", "chip", "chips", "chipmaker"),
    "ASIC": ("asic", "custom silicon", "custom chip", "custom accelerator", "xpu"),
    "data_center": ("data center", "datacenter", "hyperscaler", "cloud capex"),
    "guidance": ("guidance", "outlook", "forecast", "raise", "raised", "lowered", "cut"),
    "earnings": ("earnings", "eps", "revenue", "margin", "beat", "miss"),
    "valuation": ("valuation", "multiple", "premium", "expensive", "cheap", "price target"),
    "export_controls": ("export control", "export ban", "china restriction", "restricted china"),
    "tariffs": ("tariff", "tariffs", "trade war", "duties"),
    "rates": ("rates", "yields", "fed", "inflation", "cpi", "bond yield"),
}

_BULLISH_KEYWORDS = (
    "beat",
    "beats",
    "raise",
    "raised",
    "upgrade",
    "upgraded",
    "strong demand",
    "accelerating",
    "record",
    "growth",
    "tailwind",
    "bullish",
    "positive",
    "outperform",
    "buy rating",
    "price target raised",
    "order growth",
    "backlog",
)

_BEARISH_KEYWORDS = (
    "miss",
    "misses",
    "cut",
    "lowered",
    "downgrade",
    "downgraded",
    "weak demand",
    "slowing",
    "margin pressure",
    "headwind",
    "bearish",
    "negative",
    "underperform",
    "sell rating",
    "price target cut",
    "expensive",
    "overvalued",
    "export control",
    "tariff",
    "tariffs",
)

_CATALYST_KEYWORDS = (
    "earnings",
    "guidance",
    "outlook",
    "upgrade",
    "downgrade",
    "price target",
    "export control",
    "tariff",
    "tariffs",
    "fed",
    "rates",
    "major customer",
    "hyperscaler",
    "new order",
    "large order",
    "order growth",
    "customer order",
    "backlog",
    "major deal",
    "customer deal",
    "supply deal",
)

_PEER_KEYWORDS = ("nvda", "nvidia", "amd", "soxx", "qqq", "semis", "semiconductor", "chips")


def _split_sources(text: str) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        source = line.strip()
        if not source:
            continue
        dedupe_key = source.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        sources.append(source)
    return sources


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(len(re.findall(_term_pattern(term), text)) for term in terms)


def _term_pattern(term: str) -> str:
    escaped = re.escape(term.strip())
    if term.strip().replace(" ", "").isalnum():
        return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return escaped


def _detect_topics(text: str) -> list[str]:
    tags = [
        topic
        for topic, keywords in _TOPIC_KEYWORDS.items()
        if any(re.search(_term_pattern(keyword), text) for keyword in keywords)
    ]
    return sorted(tags)


def _classify_sentiment(bullish_hits: int, bearish_hits: int) -> str:
    if bullish_hits >= bearish_hits + 2:
        return "bullish"
    if bearish_hits >= bullish_hits + 2:
        return "bearish"
    if bullish_hits > 0 and bearish_hits > 0:
        return "mixed"
    return "neutral"


def _classify_confidence(source_count: int, signal_count: int) -> str:
    if source_count >= 4 and signal_count >= 4:
        return "high"
    if source_count >= 2 and signal_count >= 2:
        return "medium"
    return "low"


def _bias_adjustment(scan_bias: str, sentiment_bias: str) -> str:
    if scan_bias == "bullish":
        if sentiment_bias == "bullish":
            return "reinforce_bullish"
        if sentiment_bias == "bearish":
            return "weaken_bullish"
    if scan_bias == "bearish":
        if sentiment_bias == "bearish":
            return "reinforce_bearish"
        if sentiment_bias == "bullish":
            return "weaken_bearish"
    return "no_change"


def _summarize_catalyst(catalyst_detected: bool, topic_tags: list[str]) -> str:
    if not catalyst_detected:
        return "No clear catalyst detected in the pasted text."
    catalyst_topics = [
        tag for tag in topic_tags
        if tag in {"guidance", "earnings", "export_controls", "tariffs", "rates", "data_center", "ASIC"}
    ]
    if catalyst_topics:
        return "Potential catalyst areas: " + ", ".join(catalyst_topics) + "."
    return "Potential catalyst language detected, but the topic is broad."


def _summarize_peer_context(text: str) -> str:
    peers = sorted({peer.upper() for peer in _PEER_KEYWORDS if peer in text})
    if not peers:
        return "No explicit peer or sector context found."
    return "Peer/sector context mentioned: " + ", ".join(peers) + "."


def _summarize_market_narrative(topic_tags: list[str], sentiment_bias: str) -> str:
    if not topic_tags:
        return "Narrative is sparse; no strong market theme detected."
    return f"Narrative is {sentiment_bias} with focus on " + ", ".join(topic_tags[:5]) + "."


def _build_notes(adjustment: str, sentiment_bias: str, scan_bias: str) -> str:
    if adjustment == "no_change":
        return f"Research is {sentiment_bias}; no clear adjustment to {scan_bias} Scan bias."
    return f"Research is {sentiment_bias}; adjustment is {adjustment} relative to {scan_bias} Scan bias."


def run_research(
    pasted_headlines: str = "",
    pasted_snippets: str = "",
    freeform_notes: str = "",
    scan_result: dict[str, Any] | None = None,
    symbol: str = "AVGO",
) -> ResearchResult:
    """Analyze manually pasted research text and comment on current Scan."""
    headline_sources = _split_sources(pasted_headlines)
    snippet_sources = _split_sources(pasted_snippets)
    note_sources = _split_sources(freeform_notes)
    source_count = len(headline_sources) + len(snippet_sources) + len(note_sources)

    combined_text = "\n".join(headline_sources + snippet_sources + note_sources).lower()
    topic_tags = _detect_topics(f" {combined_text} ")
    bullish_hits = _count_terms(combined_text, _BULLISH_KEYWORDS)
    bearish_hits = _count_terms(combined_text, _BEARISH_KEYWORDS)
    sentiment_bias = _classify_sentiment(bullish_hits, bearish_hits)
    catalyst_detected = any(re.search(_term_pattern(keyword), combined_text) for keyword in _CATALYST_KEYWORDS)
    signal_count = bullish_hits + bearish_hits + len(topic_tags) + (1 if catalyst_detected else 0)
    confidence = _classify_confidence(source_count, signal_count)

    scan_bias = str((scan_result or {}).get("scan_bias", "neutral"))
    adjustment = _bias_adjustment(scan_bias, sentiment_bias)

    return {
        "symbol": symbol,
        "research_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_count": source_count,
        "source_types_summary": {
            "headlines": len(headline_sources),
            "snippets": len(snippet_sources),
            "notes": len(note_sources),
        },
        "topic_tags": topic_tags,
        "sentiment_bias": sentiment_bias,
        "confidence": confidence,
        "catalyst_detected": catalyst_detected,
        "catalyst_summary": _summarize_catalyst(catalyst_detected, topic_tags),
        "peer_context_summary": _summarize_peer_context(combined_text),
        "market_narrative_summary": _summarize_market_narrative(topic_tags, sentiment_bias),
        "research_bias_adjustment": adjustment,
        "notes": _build_notes(adjustment, sentiment_bias, scan_bias),
    }
