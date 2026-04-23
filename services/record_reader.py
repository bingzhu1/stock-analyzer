"""
Record reader: look up system design records by number or keyword.
Usage: get_record("01") or get_record("系统设计")
"""

from pathlib import Path

_RECORDS_DIR = Path(__file__).parent.parent / "records"

# Map canonical keys → record filename (without directory).
# Each record can have multiple aliases pointing to the same file.
RECORD_MAP: dict[str, str] = {
    "01": "01_system_design.md",
    "系统设计": "01_system_design.md",
    "system_design": "01_system_design.md",
}


def get_record(query: str) -> str:
    """Return the full text of the record matching *query*.

    *query* can be a record number ("01") or a keyword ("系统设计").
    Returns an error string (never raises) when no match is found.
    """
    key = query.strip()
    filename = RECORD_MAP.get(key)
    if filename is None:
        available = ", ".join(sorted({v.split("_")[0] for v in RECORD_MAP.values()}))
        return f"[record_reader] 未找到记录：\"{key}\"。可用编号：{available}"

    path = _RECORDS_DIR / filename
    if not path.exists():
        return f"[record_reader] 记录文件缺失：{path}"

    return path.read_text(encoding="utf-8")


def list_records() -> list[dict]:
    """Return a summary list of all registered records."""
    seen: dict[str, dict] = {}
    for alias, filename in RECORD_MAP.items():
        if filename not in seen:
            seen[filename] = {"file": filename, "aliases": []}
        seen[filename]["aliases"].append(alias)
    return list(seen.values())


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "01"
    print(get_record(query))
