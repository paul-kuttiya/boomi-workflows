#!/usr/bin/env python3
"""
CI validator for Boomi process XMLs.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any

# Blocklisted component IDs that must not appear in production XMLs
BLOCKLIST = {
    "ab12cd34-5678-90ef-ghij-klmnopqrstuv",
    "ff00aa11-2233-4455-6677-889900bbccdd",
    "151411ac-6724-21ae-giz-00000000azz1a",
    "12345678-9abc-def0-1234-56789abcdef0",
}


def parse_xml(path: str) -> ET.Element:
    # Parse an XML file and return the root element
    tree = ET.parse(path)
    return tree.getroot()


def rule_error_handling(root: ET.Element) -> Tuple[bool, str]:
    # Check for a returndocuments shape with a label containing "Error"
    for elem in root.iter():
        if (elem.attrib.get("shapetype") or "").strip() == "returndocuments":
            label = elem.attrib.get("label") or ""
            if "error" in label.lower():
                return True, f'✅ Rule 1 OK: found returndocuments shape with label "{label}".'
    return False, "❌ Rule 1 FAIL: missing returndocuments shape with 'Error' label."


def rule_no_blocklisted_components(root: ET.Element) -> Tuple[bool, str]:
    # Detect any blocklisted componentId values in the XML
    found = []
    for elem in root.iter():
        cid = elem.attrib.get("componentId")
        if cid and cid in BLOCKLIST:
            found.append((elem.tag, cid))

    if not found:
        return True, "✅ Rule 2 OK: no blocklisted componentId values found."

    uniq = list(dict.fromkeys(found))
    sample = ", ".join([f"{tag}({cid})" for tag, cid in uniq[:5]])
    more = "" if len(uniq) <= 5 else f" (+{len(uniq) - 5} more)"
    return False, f"❌ Rule 2 FAIL: blocklisted componentId(s): {sample}{more}."


def validate_file(path: str) -> Dict[str, Any]:
    # Run all validation rules against a single XML file
    try:
        root = parse_xml(path)
    except Exception as e:
        return {
            "path": path,
            "passed": False,
            "messages": [f"❌ XML parse error: {e}"],
        }

    r1_ok, r1_msg = rule_error_handling(root)
    r2_ok, r2_msg = rule_no_blocklisted_components(root)

    return {
        "path": path,
        "passed": r1_ok and r2_ok,
        "messages": [r1_msg, r2_msg],
    }


def render_markdown(results: List[Dict[str, Any]]) -> str:
    # Render validation results as markdown for PR comments and summaries
    lines = ["## 🍫 Boomi XML Validation Results", ""]

    passed = sum(1 for r in results if r["passed"])
    lines.append(f"**Summary:** {passed}/{len(results)} file(s) passed.\n")

    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        lines.append(f"### {status}: `{r['path']}`")
        for m in r["messages"]:
            lines.append(f"- {m}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        return 2

    results = [validate_file(p) for p in argv[1:]]
    md = render_markdown(results)

    with open("boomi-xml-validation-results.md", "w", encoding="utf-8") as f:
        f.write(md)

    print(md)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(md + "\n")

    return 1 if any(not r["passed"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
