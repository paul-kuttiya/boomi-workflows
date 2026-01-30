#!/usr/bin/env python3
"""
CI validator for Boomi process XMLs.
"""

from __future__ import annotations

import os
import sys
from typing import List, Tuple, Dict, Any

from lxml import etree

BLOCKLIST = {
    "ab12cd34-5678-90ef-ghij-klmnopqrstuv",
    "ff00aa11-2233-4455-6677-889900bbccdd",
    "151411ac-6724-21ae-giz-00000000azz1a",
    "12345678-9abc-def0-1234-56789abcdef0",
}


def parse_xml(path: str) -> etree._Element:
    # Parse XML with recovery for minor formatting issues.
    parser = etree.XMLParser(
        recover=True,
        resolve_entities=False,
        no_network=True,
        huge_tree=False,
        remove_comments=False,
    )
    with open(path, "rb") as f:
        return etree.fromstring(f.read(), parser=parser)


def shape_label(shape: etree._Element) -> str:
    # Boomi commonly uses userlabel; label is a fallback.
    return (shape.get("userlabel") or shape.get("label") or "").strip()


def rule_error_handling(root: etree._Element) -> Tuple[bool, str]:
    # Must have a returndocuments shape whose label contains "Error" (case-insensitive).
    candidates: List[str] = []
    for shape in root.xpath(".//shape[@shapetype='returndocuments']"):
        lbl = shape_label(shape)
        candidates.append(lbl or "(no label)")
        if "error" in (lbl or "").lower():
            return True, f'✅ Rule 1 OK: found returndocuments shape labeled "{lbl}".'

    if candidates:
        return False, (
            "❌ Rule 1 FAIL: returndocuments shape found, but none labeled with 'Error'. "
            f"Found labels: {', '.join(candidates)}"
        )

    return False, "❌ Rule 1 FAIL: no returndocuments shape found."


def rule_no_blocklisted_components(root: etree._Element) -> Tuple[bool, str]:
    # No shape may contain a blocklisted componentId.
    hits: List[Tuple[str, str]] = []
    for shape in root.xpath(".//shape[@componentId]"):
        cid = (shape.get("componentId") or "").strip()
        if cid in BLOCKLIST:
            hits.append((cid, shape_label(shape)))

    if not hits:
        return True, "✅ Rule 2 OK: no blocklisted componentId values found in shapes."

    # Deduplicate while preserving order
    seen = set()
    uniq: List[Tuple[str, str]] = []
    for cid, lbl in hits:
        key = (cid, lbl)
        if key not in seen:
            seen.add(key)
            uniq.append((cid, lbl))

    formatted = ", ".join([f'{cid} ("{lbl}")' if lbl else cid for cid, lbl in uniq[:5]])
    more = "" if len(uniq) <= 5 else f" (+{len(uniq) - 5} more)"
    return False, f"❌ Rule 2 FAIL: blocklisted componentId(s) found in shapes: {formatted}{more}"


def validate_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"path": path, "passed": False, "messages": ["❌ File not found."]}

    try:
        root = parse_xml(path)
    except Exception as e:
        return {"path": path, "passed": False, "messages": [f"❌ XML parse error: {e}"]}

    r1_ok, r1_msg = rule_error_handling(root)
    r2_ok, r2_msg = rule_no_blocklisted_components(root)

    return {"path": path, "passed": bool(r1_ok and r2_ok), "messages": [r1_msg, r2_msg]}


def render_markdown(results: List[Dict[str, Any]]) -> str:
    lines = ["## 🍫 Boomi XML Validation Results", ""]
    passed = sum(1 for r in results if r["passed"])
    lines.append(f"**Summary:** {passed}/{len(results)} file(s) passed.")
    lines.append("")
    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        lines.append(f"### {status}: `{r['path']}`")
        for m in r["messages"]:
            lines.append(f"- {m}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_step_summary(md: str) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    try:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(md + "\n")
    except Exception:
        pass


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        md = "## 🍫 Boomi XML Validation Results\n\n❌ No XML files provided.\n"
        with open("boomi-xml-validation-results.md", "w", encoding="utf-8") as f:
            f.write(md)
        print("Usage: validate_boomi_xml.py <file1.xml> [file2.xml ...]", file=sys.stderr)
        print(md)
        write_step_summary(md)
        return 2

    results = [validate_file(p) for p in argv[1:]]
    md = render_markdown(results)

    with open("boomi-xml-validation-results.md", "w", encoding="utf-8") as f:
        f.write(md)

    print(md)
    write_step_summary(md)

    return 1 if any(not r["passed"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
