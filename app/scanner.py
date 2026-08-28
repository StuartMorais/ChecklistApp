from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .storage import new_id

SECTION_RE = re.compile(r"^\s*(\d{1,2})\.\s+(.{4,})\s*$")
ITEM_RE = re.compile(r"^\s*(\d+(?:\.\d+)+)\s*(?:[-–.)|:]|\s)\s*(.+?)\s*$")

NORMATIVE_RE = re.compile(
    r"\b(?:Lei|Decreto|Instrução\s+Normativa|IN|Resolução|Portaria|Acórdão|Art\.?|art\.?)\b[^.;\n]*",
    re.IGNORECASE,
)

DOCUMENT_WORD_RE = re.compile(
    r"\b(?:documento|informação|informacoes|comprovante|declaração|declaracao|certidão|certidao|termo|ata|estudo|justificativa|parecer|contrato|processo|relatório|relatorio|autorização|autorizacao)\b",
    re.IGNORECASE,
)


def scan_document_to_template(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".docx", ".docm"}:
        lines = extract_docx_lines(path)
    elif suffix == ".pdf":
        lines = extract_pdf_lines(path)
    else:
        raise ValueError("Formato não suportado. Use DOCX, DOCM ou PDF.")

    return build_template_from_lines(path, lines)


def extract_docx_lines(path: Path) -> list[str]:
    try:
        from docx import Document
        from docx.document import Document as DocxDocument
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError as error:
        raise RuntimeError("Instale python-docx para escanear DOCX/DOCM.") from error

    document = Document(str(path))
    lines: list[str] = []

    def iter_blocks(parent: DocxDocument):
        for child in parent.element.body.iterchildren():
            if isinstance(child, CT_P):
                yield Paragraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield Table(child, parent)

    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            text = clean_text(block.text)
            if text:
                lines.append(text)
        else:
            for row in block.rows:
                cells = [clean_text(cell.text) for cell in row.cells]
                cells = [cell for cell in cells if cell]

                if cells:
                    lines.append(" | ".join(cells))

    return lines


def extract_pdf_lines(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Instale pypdf para escanear PDF.") from error

    reader = PdfReader(str(path))
    lines: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""

        for raw_line in page_text.splitlines():
            line = clean_text(raw_line)

            if line:
                lines.append(line)

    return lines


def build_template_from_lines(path: Path, lines: list[str]) -> dict[str, Any]:
    template = {
        "id": new_id("checklist"),
        "title": path.stem,
        "subtitle": f"Importado por scanner de {path.suffix.upper().replace('.', '')}",
        "baseLegal": "",
        "description": f"Checklist criado automaticamente a partir de: {path.name}",
        "sections": [],
    }

    current_section: dict[str, Any] | None = None
    current_item: dict[str, Any] | None = None

    def ensure_section() -> dict[str, Any]:
        nonlocal current_section

        if current_section is None:
            current_section = make_section("1", "DOCUMENTOS / ITENS IDENTIFICADOS")
            template["sections"].append(current_section)

        return current_section

    for raw_line in lines:
        line = clean_text(raw_line)

        if not line or is_noise_line(line):
            continue

        section_match = SECTION_RE.match(line)

        if section_match and looks_like_section_title(section_match.group(2)):
            current_section = make_section(section_match.group(1), section_match.group(2))
            template["sections"].append(current_section)
            current_item = None
            continue

        item_match = ITEM_RE.match(line)

        if item_match:
            section = ensure_section()

            current_item = make_item(
                number=item_match.group(1),
                text=item_match.group(2),
                confidence="high",
                evidence="Número de item identificado no documento.",
            )

            section["items"].append(current_item)
            continue

        if current_item and should_attach_to_previous_item(line):
            append_to_item(current_item, line)
            continue

        if DOCUMENT_WORD_RE.search(line) and len(line) >= 25:
            section = ensure_section()
            item_number = f"{section['number']}.{len(section['items']) + 1}"

            current_item = make_item(
                number=item_number,
                text=line,
                confidence="medium",
                evidence="Linha sem numeração, mas com vocabulário típico de documento/informação.",
            )

            section["items"].append(current_item)
            continue

        current_item = None

    if not template["sections"]:
        template["sections"].append(make_section("1", "DOCUMENTOS / ITENS IDENTIFICADOS"))

    return template


def make_section(number: str, title: str) -> dict[str, Any]:
    return {
        "id": new_id("section"),
        "number": clean_text(number),
        "title": clean_text(title).upper(),
        "items": [],
    }


def make_item(number: str, text: str, confidence: str, evidence: str) -> dict[str, Any]:
    text = clean_text(text)
    normatives = extract_normatives(text)

    return {
        "id": new_id("item"),
        "number": clean_text(number),
        "documento": text,
        "normativo": normatives,
        "situacao": "N/A",
        "folha": "",
        "observacao": "",
        "description": "",
        "requiredDocuments": [],
        "notes": [],
        "scanConfidence": confidence,
        "scanEvidence": [evidence],
    }


def append_to_item(item: dict[str, Any], line: str) -> None:
    normatives = extract_normatives(line)

    if normatives:
        existing = str(item.get("normativo") or "").strip()
        item["normativo"] = f"{existing}\n{normatives}".strip()
    else:
        existing = str(item.get("documento") or "").strip()
        item["documento"] = f"{existing}\n{line}".strip()


def extract_normatives(text: str) -> str:
    matches = [clean_text(match.group(0)) for match in NORMATIVE_RE.finditer(text)]
    seen: set[str] = set()
    unique_matches: list[str] = []

    for match in matches:
        key = match.lower()

        if key not in seen:
            seen.add(key)
            unique_matches.append(match)

    return "\n".join(unique_matches)


def looks_like_section_title(text: str) -> bool:
    text = clean_text(text)

    if not text:
        return False

    letters = [char for char in text if char.isalpha()]

    if not letters:
        return False

    uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)

    keywords = (
        "DA ",
        "DO ",
        "DAS ",
        "DOS ",
        "DE ",
        "PLANEJAMENTO",
        "FORMALIDADE",
        "ESTIMATIVA",
        "PREÇO",
        "DOCUMENTAÇÃO",
    )

    return uppercase_ratio >= 0.55 or any(keyword in text.upper() for keyword in keywords)


def should_attach_to_previous_item(line: str) -> bool:
    if len(line) < 8:
        return False

    if SECTION_RE.match(line) or ITEM_RE.match(line):
        return False

    if line.isupper() and len(line.split()) <= 8:
        return False

    return True


def is_noise_line(line: str) -> bool:
    value = clean_text(line)

    if not value:
        return True

    if re.fullmatch(r"\d+", value):
        return True

    if re.fullmatch(r"p[aá]gina\s+\d+(?:\s+de\s+\d+)?", value, flags=re.IGNORECASE):
        return True

    return False


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()
