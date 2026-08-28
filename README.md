# Checklist Application — Python

Python/PySide6 version of the checklist app with a structure-first document scanner inspired by Padroniza.

## Features

- Uses the existing checklist JSON data file from the Electron app:
  `%APPDATA%\checklist-app\data\checklistTemplates.json`
- Opens existing checklists from the left sidebar.
- Creates empty checklists.
- Copies checklists.
- Adds sections and items.
- Edits checklist rows directly in the table.
- Scans DOCX, DOCM and PDF files into checklist sections/items.
- Extracts possible normatives such as Lei, Decreto, IN, Resolução, Portaria and Art.
- Saves automatically after table edits.
- Creates automatic backups before saving.
- Exports the selected checklist as a complete PDF.

## Install and run on Windows

```powershell
cd "C:\Users\ADM\Desktop\Codigos\Python\ChecklistPython"

py -m venv .venv

.\.venv\Scripts\python.exe -m pip install --upgrade pip

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe main.py
```

## Project structure

```text
ChecklistPython/
├── app/
│   ├── __init__.py
│   ├── main_window.py
│   ├── pdf_exporter.py
│   ├── scanner.py
│   └── storage.py
├── main.py
├── README.md
└── requirements.txt
```

## Notes

This is not Padroniza's full Scanner V6. It is a practical checklist scanner baseline that follows the same general direction: structure-first detection, review/edit before use, and no reliance on the visible screen for PDF export.
