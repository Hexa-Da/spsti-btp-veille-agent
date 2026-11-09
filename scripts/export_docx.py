#!/usr/bin/env python3
"""Met en forme rapport.md (+ liste retenus) en .docx OOXML sans dépendance."""

from __future__ import annotations

import re
import sys
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import EXPORTS, RAPPORT_PATH, selected_items

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>
"""


def _p(text: str, *, bold: bool = False) -> str:
    if not text.strip():
        return '<w:p><w:r><w:t></w:t></w:r></w:p>'
    run = escape(text)
    if bold:
        return (
            f'<w:p><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{run}</w:t></w:r></w:p>'
        )
    return f'<w:p><w:r><w:t xml:space="preserve">{run}</w:t></w:r></w:p>'


_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def _plain(line: str) -> str:
    # [libellé](url) → url (ou libellé s'il diffère et n'est pas l'url)
    def repl(m: re.Match[str]) -> str:
        label, url = m.group(1).strip(), m.group(2).strip()
        return url if (not label or label == url) else label

    return _MD_LINK.sub(repl, re.sub(r"[*_`]", "", line))


def md_to_paragraphs(md: str) -> list[str]:
    paras: list[str] = []
    for line in md.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        # titres markdown → gras
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            paras.append(_p(_plain(m.group(2).strip()), bold=True))
            continue
        # listes
        if re.match(r"^[-*]\s+", line):
            paras.append(_p("• " + _plain(re.sub(r"^[-*]\s+", "", line))))
            continue
        paras.append(_p(_plain(line)))
    return paras


def build_document_xml(md: str, items: list[dict] | None) -> str:
    parts = md_to_paragraphs(md)
    if items:
        parts.append(_p("Liste des liens retenus", bold=True))
        for it in items:
            titre = it.get("titre") or "(sans titre)"
            url = it.get("url") or ""
            parts.append(_p(f"{titre} — {url}"))
    body = "\n".join(parts) if parts else _p("(Rapport vide)")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr/>
  </w:body>
</w:document>
"""


def main() -> None:
    if not RAPPORT_PATH.is_file():
        raise SystemExit(f"Pas de rapport : {RAPPORT_PATH} (lancez rapport.py)")
    md = RAPPORT_PATH.read_text(encoding="utf-8")
    items = selected_items()
    EXPORTS.mkdir(parents=True, exist_ok=True)
    out = EXPORTS / f"veille-{date.today().isoformat()}.docx"
    document_xml = build_document_xml(md, items)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
    print(f"Word → {out}")


if __name__ == "__main__":
    main()
