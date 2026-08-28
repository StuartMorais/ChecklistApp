from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
DATA_DIR = APPDATA_DIR / "checklist-app" / "data"
DATA_FILE = DATA_DIR / "checklistTemplates.json"
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 20


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def load_templates() -> list[dict[str, Any]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("O arquivo checklistTemplates.json deve conter uma lista.")

    return [normalize_template(template) for template in data]


def save_templates(templates: list[dict[str, Any]]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if DATA_FILE.exists():
        create_backup()

    normalized = [normalize_template(template) for template in templates]

    temporary_file = DATA_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)

    temporary_file.replace(DATA_FILE)
    prune_backups()

    return DATA_FILE


def create_backup() -> Path | None:
    if not DATA_FILE.exists():
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = BACKUP_DIR / f"checklistTemplates-backup-{timestamp}-python.json"

    shutil.copy2(DATA_FILE, backup_path)

    return backup_path


def prune_backups() -> None:
    if not BACKUP_DIR.exists():
        return

    backups = sorted(
        BACKUP_DIR.glob("checklistTemplates-backup-*.json"),
        key=lambda path: path.name,
        reverse=True,
    )

    for old_backup in backups[MAX_BACKUPS:]:
        old_backup.unlink(missing_ok=True)


def normalize_template(template: Any) -> dict[str, Any]:
    if not isinstance(template, dict):
        template = {}

    normalized = {
        "id": str(template.get("id") or new_id("checklist")),
        "title": str(template.get("title") or "Checklist sem nome"),
        "subtitle": str(template.get("subtitle") or ""),
        "baseLegal": str(template.get("baseLegal") or ""),
        "description": str(template.get("description") or ""),
        "sections": [],
    }

    raw_sections = template.get("sections")

    if isinstance(raw_sections, list):
        normalized["sections"] = [
            normalize_section(section, index + 1)
            for index, section in enumerate(raw_sections)
        ]
    elif isinstance(template.get("items"), list):
        normalized["sections"] = [
            {
                "id": new_id("section"),
                "number": "1",
                "title": "DOCUMENTOS / ITENS",
                "items": [
                    normalize_item(item, index + 1)
                    for index, item in enumerate(template.get("items", []))
                ],
            }
        ]

    return normalized


def normalize_section(section: Any, fallback_number: int) -> dict[str, Any]:
    if not isinstance(section, dict):
        section = {}

    raw_items = section.get("items")

    return {
        "id": str(section.get("id") or new_id("section")),
        "number": str(section.get("number") or fallback_number),
        "title": str(section.get("title") or "SEÇÃO SEM TÍTULO"),
        "items": [
            normalize_item(item, index + 1)
            for index, item in enumerate(raw_items if isinstance(raw_items, list) else [])
        ],
    }


def normalize_item(item: Any, fallback_number: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}

    return {
        "id": str(item.get("id") or new_id("item")),
        "number": str(item.get("number") or fallback_number),
        "documento": str(item.get("documento") or ""),
        "normativo": str(item.get("normativo") or ""),
        "situacao": str(item.get("situacao") or "N/A"),
        "folha": str(item.get("folha") or ""),
        "observacao": str(item.get("observacao") or ""),
        "description": str(item.get("description") or ""),
        "requiredDocuments": normalize_text_list(item.get("requiredDocuments")),
        "notes": normalize_text_list(item.get("notes")),
        "scanConfidence": str(item.get("scanConfidence") or ""),
        "scanEvidence": normalize_text_list(item.get("scanEvidence")),
    }


def normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]
