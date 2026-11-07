"""Deterministic, attributed parsing. No scientific interpretation or AI-generated cells."""

import re
from dataclasses import dataclass

from defusedxml import ElementTree as ET


@dataclass
class IngestionError(Exception):
    code: str
    message: str


def normalize_doi(value: str) -> str:
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I)
    if not re.fullmatch(r"10\.\d{4,9}/[^\s<>?#]+", value, re.I) or len(value) > 255:
        raise IngestionError("invalid_doi", "Introduce un DOI válido, por ejemplo 10.1234/articulo")
    return value.lower()


def text(element) -> str:
    if element is None:
        return ""

    def rendered(node):
        result = node.text or ""
        for child in node:
            result += rendered(child)
            if child.tag.split("}")[-1] in {"p", "list-item", "break", "br", "disp-formula"}:
                result += " "
            result += child.tail or ""
        return result

    return " ".join(rendered(element).split())


def license_policy(value: str | None) -> tuple[str, bool]:
    raw = (value or "").lower().replace("http://", "https://").strip()
    patterns = [
        ("creativecommons.org/licenses/by-nc-nd/", "CC BY-NC-ND"),
        ("creativecommons.org/licenses/by-nc-sa/", "CC BY-NC-SA"),
        ("creativecommons.org/licenses/by-nc/", "CC BY-NC"),
        ("creativecommons.org/licenses/by-nd/", "CC BY-ND"),
        ("creativecommons.org/licenses/by-sa/", "CC BY-SA"),
        ("creativecommons.org/licenses/by/", "CC BY"),
        ("creativecommons.org/publicdomain/zero/", "CC0"),
    ]
    for url, name in patterns:
        if raw.startswith("https://" + url) or raw.replace("-", " ") == name.lower().replace(
            "-", " "
        ):
            return name, "NC" in name or "ND" in name
    raise IngestionError(
        "license_unknown",
        "No pudimos comprobar una licencia compatible. "
        "No se procesará el texto sin verificar sus permisos de uso",
    )


def jats_license(data: bytes) -> str | None:
    root = ET.fromstring(data)
    for license_node in root.findall(".//permissions/license"):
        for node in license_node.iter():
            href = node.get("{http://www.w3.org/1999/xlink}href")
            candidate = href or (text(node) if node.tag.split("}")[-1] == "license_ref" else None)
            if candidate and "creativecommons.org/" in candidate:
                return candidate.strip()
        if text(license_node):
            return text(license_node)
    return None


def parse_jats(data: bytes) -> dict:
    root = ET.fromstring(data)
    if root.tag != "article":
        raise IngestionError("invalid_xml", "La fuente no entregó el texto completo del artículo")
    sections = []
    for index, section in enumerate(root.findall(".//body//sec"), 1):
        paragraphs = [
            {"text": text(p), "location": f"Sección {index}, párrafo {i}", "page": None}
            for i, p in enumerate(section.findall("p"), 1)
            if text(p)
        ]
        if paragraphs:
            sections.append(
                {
                    "title": text(section.find("title")) or f"Sección {index}",
                    "paragraphs": paragraphs,
                }
            )
    if not sections:
        sections = [
            {
                "title": "Texto completo",
                "paragraphs": [
                    {"text": text(p), "location": f"Párrafo {i}", "page": None}
                    for i, p in enumerate(root.findall(".//body/p"), 1)
                    if text(p)
                ],
            }
        ]
    tables = []
    for i, table in enumerate(root.findall(".//table-wrap"), 1):
        header = [[text(c) for c in row] for row in table.findall(".//thead/tr")]
        rows = [
            [
                {
                    "text": text(c),
                    "rowspan": c.get("rowspan", "1"),
                    "colspan": c.get("colspan", "1"),
                }
                for c in row
            ]
            for row in table.findall(".//tbody/tr")
        ]
        if not rows:
            rows = [
                [
                    {
                        "text": text(c),
                        "rowspan": c.get("rowspan", "1"),
                        "colspan": c.get("colspan", "1"),
                    }
                    for c in row
                ]
                for row in table.findall(".//table/tr")
            ]
        tables.append(
            {
                "caption": text(table.find("label")) + " " + text(table.find("caption")),
                "location": f"Tabla {i}",
                "page": None,
                "header": header,
                "header_cells": [
                    [
                        {
                            "text": text(c),
                            "rowspan": c.get("rowspan", "1"),
                            "colspan": c.get("colspan", "1"),
                        }
                        for c in row
                    ]
                    for row in table.findall(".//thead/tr")
                ],
                "footnotes": [text(n) for n in table.findall(".//table-wrap-foot")],
                "rows": rows,
                "needs_review": any(
                    c["rowspan"] != "1" or c["colspan"] != "1" for row in rows for c in row
                )
                or any(
                    c.get("rowspan", "1") != "1" or c.get("colspan", "1") != "1"
                    for row in table.findall(".//thead/tr")
                    for c in row
                ),
            }
        )
    references = [
        {
            "text": " ".join(" ".join(ref.itertext()).split()),
            "source_text": text(ref),
            "location": f"Referencia {i}",
            "doi": next(
                (text(x) for x in ref.findall(".//pub-id") if x.get("pub-id-type") == "doi"), None
            ),
        }
        for i, ref in enumerate(root.findall(".//ref-list/ref"), 1)
    ]
    return {
        "parser": "jats-v2",
        "sections": sections,
        "tables": tables,
        "references": references,
        "warnings": [],
    }


def validate_pdf(data: bytes):
    import pymupdf

    if not data.startswith(b"%PDF-"):
        raise IngestionError("invalid_pdf", "El archivo no es un PDF válido")
    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass or pdf.page_count < 1 or pdf.page_count > 1500:
                raise ValueError()
    except Exception:
        raise IngestionError(
            "invalid_pdf", "El PDF está dañado, protegido o excede 1500 páginas"
        ) from None


def parse_pdf(data: bytes) -> dict:
    import pymupdf

    validate_pdf(data)
    sections, tables = [], []
    references: list[dict] = []
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        for index, page in enumerate(pdf, 1):
            paragraphs = [
                {"text": p.strip(), "page": index, "location": f"Página {index}, párrafo {i}"}
                for i, p in enumerate(page.get_text().split("\n\n"), 1)
                if p.strip()
            ]
            sections.append({"title": f"Página {index}", "paragraphs": paragraphs})
            for i, table in enumerate(page.find_tables().tables, 1):
                extracted = table.extract()
                tables.append(
                    {
                        "caption": f"Tabla de la página {index} ({i})",
                        "page": index,
                        "location": f"Página {index}, tabla {i}",
                        "header": [],
                        "rows": [
                            [{"text": c or "", "rowspan": "1", "colspan": "1"} for c in row]
                            for row in extracted
                        ],
                        "needs_review": True,
                    }
                )
    if not any(s["paragraphs"] for s in sections):
        raise IngestionError(
            "scanned_pdf",
            "El PDF no contiene texto seleccionable. "
            "Sube una versión con texto o prueba la búsqueda por DOI",
        )
    return {
        "parser": "pymupdf-v1",
        "sections": sections,
        "tables": tables,
        "references": references,
        "warnings": ["La estructura del PDF requiere revisión manual"],
    }


def enrich_pdf(data: bytes, document: dict) -> dict:
    """GROBID supplies section boundaries and references; cells remain parser-derived."""
    import httpx

    from app.config import get_settings

    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(
                get_settings().grobid_url + "/api/processFulltextDocument",
                files={"input": ("review.pdf", data, "application/pdf")},
                data={"includeRawCitations": "1"},
            )
            response.raise_for_status()
        root = ET.fromstring(response.content)
        ns = {"t": "http://www.tei-c.org/ns/1.0"}
        sections = []
        for i, section in enumerate(root.findall(".//t:body//t:div", ns), 1):
            paragraphs = [
                {"text": text(p), "page": None, "location": f"Sección {i}, párrafo {j}"}
                for j, p in enumerate(section.findall("t:p", ns), 1)
            ]
            if paragraphs:
                sections.append(
                    {
                        "title": text(section.find("t:head", ns)) or f"Sección {i}",
                        "paragraphs": paragraphs,
                    }
                )
        references = [
            {
                "text": text(ref),
                "location": f"Referencia {i}",
                "doi": next(
                    (text(x) for x in ref.findall(".//t:idno", ns) if x.get("type") == "DOI"), None
                ),
            }
            for i, ref in enumerate(root.findall(".//t:listBibl/t:biblStruct", ns), 1)
        ]
        if sections:
            document["sections"] = sections
        document["references"] = references
        document["parser"] = "grobid+pymupdf-v1"
    except (httpx.HTTPError, ET.ParseError):
        document["warnings"].append(
            "La lectura detallada no estuvo disponible; "
            "se muestra el texto por páginas. Las referencias requieren revisión"
        )
    return document
