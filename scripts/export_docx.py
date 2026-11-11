#!/usr/bin/env python3
"""Injecte rapport.md dans le template Word officiel (header/footer/logo)."""

import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import EXPORTS, RAPPORT_PATH, TEMPLATE_DOCX, veille_title

_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_URL = re.compile(r"https?://[^\s<>\"']+")
_SECTPR = re.compile(r"(<w:body[^>]*>)[\s\S]*?(<w:sectPr)")
_REL_CLOSE = re.compile(r"</Relationships>\s*$")

_RPR = (
    '<w:rFonts w:ascii="Calibri" w:eastAsia="Times New Roman" '
    'w:hAnsi="Calibri" w:cs="Calibri"/><w:lang w:eastAsia="fr-FR"/>'
)
_RPR_LINK = (
    f"{_RPR}"
    '<w:rStyle w:val="Lienhypertexte"/>'
    '<w:color w:val="0563C1"/><w:u w:val="single"/>'
)


def _plain_no_url(line: str) -> str:
    """Enlève le markdown inline, laisse les URL intactes."""
    def repl(m: re.Match) -> str:
        label, url = m.group(1).strip(), m.group(2).strip()
        if not label or label == url:
            return url
        return f"{label} {url}"

    return _MD_LINK.sub(repl, re.sub(r"[*_`]", "", line))


def _add_hyperlink(rels: list[str], url: str) -> str:
    rid = f"rId{100 + len(rels)}"
    target = escape(url, {"\"": "&quot;"})
    rels.append(
        f'<Relationship Id="{rid}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
        f'Target="{target}" TargetMode="External"/>'
    )
    return rid


def _run(text: str, rpr: str) -> str:
    return (
        f"<w:r><w:rPr>{rpr}</w:rPr>"
        f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
    )


def _run_link(text: str, rid: str) -> str:
    return (
        f'<w:hyperlink r:id="{rid}">'
        f"{_run(text, _RPR_LINK)}"
        f"</w:hyperlink>"
    )


def _p_runs(runs_xml: str) -> str:
    align = '<w:jc w:val="both"/>'
    return f"<w:p><w:pPr>{align}</w:pPr>{runs_xml}</w:p>"


def _p_empty() -> str:
    return _p_runs("")


def _p_text(text: str, *, kind: str, rels: list[str]) -> str:
    """kind: title | body | ref."""
    rpr = _RPR
    if kind == "title":
        rpr = f"{_RPR}<w:b/><w:bCs/>"
    elif kind == "ref":
        rpr = f"{_RPR}<w:i/><w:iCs/>"
    plain = _plain_no_url(text).strip()
    if not plain:
        return _p_empty()
    # ligne = URL seule → lien cliquable
    if _URL.fullmatch(plain):
        rid = _add_hyperlink(rels, plain)
        return _p_runs(_run_link(plain, rid))
    parts: list[str] = []
    pos = 0
    for m in _URL.finditer(plain):
        if m.start() > pos:
            parts.append(_run(plain[pos : m.start()], rpr))
        rid = _add_hyperlink(rels, m.group(0))
        parts.append(_run_link(m.group(0), rid))
        pos = m.end()
    if pos < len(plain):
        parts.append(_run(plain[pos:], rpr))
    if not parts:
        parts.append(_run(plain, rpr))
    return _p_runs("".join(parts))


def md_to_paragraphs(md: str, rels: list[str]) -> list[str]:
    paras: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith("# "):
        i += 1
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        if not line.strip():
            paras.append(_p_empty())
            continue
        # ignore anciennes rubriques ## (plus de sections colorées)
        if re.match(r"^##\s+", line) and not re.match(r"^###\s+", line):
            continue
        if re.match(r"^###\s+", line):
            paras.append(
                _p_text(re.sub(r"^###\s+", "", line), kind="title", rels=rels)
            )
            continue
        if re.match(r"^[-*]\s+", line):
            paras.append(
                _p_text("– " + re.sub(r"^[-*]\s+", "", line), kind="body", rels=rels)
            )
            continue
        plain = _plain_no_url(line).strip()
        if re.match(
            r"^(Cass\.|CA |Cour |D\. |LOI |Arr\.|LFSS|CSS|INRS|Assurance|"
            r"Instruction|Avis |https?://)",
            plain,
            re.I,
        ):
            paras.append(_p_text(plain, kind="ref", rels=rels))
            continue
        paras.append(_p_text(plain, kind="body", rels=rels))
    while paras and paras[0] == _p_empty():
        paras.pop(0)
    while paras and paras[-1] == _p_empty():
        paras.pop()
    # espace entre en-tête et première ligne
    return [_p_empty(), _p_empty()] + paras


def inject_body(template_xml: str, paras: list[str]) -> str:
    body = "\n".join(paras) if paras else _p_empty()
    out, n = _SECTPR.subn(r"\1" + body + r"\2", template_xml, count=1)
    if n != 1:
        raise SystemExit("Template Word invalide : <w:body>/<w:sectPr> introuvable.")
    return out


def patch_header(header_xml: str, title: str) -> str:
    new, n = re.subn(
        r"(<w:t[^>]*>)Veille juridique(?:[^<]*)(</w:t>)",
        r"\1" + escape(title) + r"\2",
        header_xml,
        count=1,
    )
    if n != 1:
        raise SystemExit("Template Word invalide : titre d'en-tête introuvable.")
    return new


def patch_rels(rels_xml: str, extra: list[str]) -> str:
    if not extra:
        return rels_xml
    out, n = _REL_CLOSE.subn("".join(extra) + "</Relationships>", rels_xml, count=1)
    if n != 1:
        raise SystemExit("Template Word invalide : document.xml.rels.")
    return out


def safe_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', " ", title).strip()
    return f"{name}.docx"


def build_docx(md: str, out_path: str, title: str | None = None) -> None:
    if not os.path.isfile(TEMPLATE_DOCX):
        raise SystemExit(f"Template manquant : {TEMPLATE_DOCX}")
    title = title or veille_title()
    rels: list[str] = []
    paras = md_to_paragraphs(md, rels)
    with zipfile.ZipFile(TEMPLATE_DOCX, "r") as zin:
        doc_xml = inject_body(zin.read("word/document.xml").decode("utf-8"), paras)
        hdr_xml = patch_header(zin.read("word/header1.xml").decode("utf-8"), title)
        rels_xml = patch_rels(
            zin.read("word/_rels/document.xml.rels").decode("utf-8"), rels
        )
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                if info.filename == "word/document.xml":
                    data = doc_xml.encode("utf-8")
                elif info.filename == "word/header1.xml":
                    data = hdr_xml.encode("utf-8")
                elif info.filename == "word/_rels/document.xml.rels":
                    data = rels_xml.encode("utf-8")
                else:
                    data = zin.read(info.filename)
                zout.writestr(info, data)


def main() -> None:
    if not os.path.isfile(RAPPORT_PATH):
        raise SystemExit(f"Pas de rapport : {RAPPORT_PATH} (lancez rapport.py)")
    with open(RAPPORT_PATH, encoding="utf-8") as f:
        md = f.read()
    os.makedirs(EXPORTS, exist_ok=True)
    title = veille_title()
    out = os.path.join(EXPORTS, safe_filename(title))
    build_docx(md, out, title=title)
    print(f"Word → {out}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        from datetime import date

        sample = """# Veille juridique du 1 au 7 novembre 2026

### Titre test
Synthèse courte avec https://example.org/inline
Cass. soc., 1 nov. 2026, n°24-00.001

### Autre titre
Texte.
https://example.org/a
"""
        os.makedirs(EXPORTS, exist_ok=True)
        out = os.path.join(EXPORTS, "_self-check.docx")
        today = veille_title(date(2026, 11, 11))
        build_docx(sample, out, title=today)
        with zipfile.ZipFile(out) as z:
            assert "word/media/image1.png" in z.namelist()
            hdr = z.read("word/header1.xml").decode("utf-8")
            assert today in hdr
            assert "1 au 7 novembre" not in hdr
            doc = z.read("word/document.xml").decode("utf-8")
            assert "FF0000" not in doc
            assert "w:hyperlink" in doc
            assert "headerReference" in doc and "footerReference" in doc
            rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
            assert "example.org/a" in rels and "TargetMode=\"External\"" in rels
            body = re.search(r"<w:body[^>]*>([\s\S]*?)<w:sectPr", doc).group(1)
            assert body.count("<w:p>") >= 3
        os.remove(out)
        assert veille_title(date(2026, 11, 11)) == "Veille juridique du 11 novembre 2026"
        print("self-check ok")
        raise SystemExit(0)
    main()
