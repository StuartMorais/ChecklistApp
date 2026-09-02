# ChecklistPython

Python/PySide6 checklist application.

This project replaces the HTML/Electron prototype with a Windows desktop app that keeps the same local JSON data model and adds a structure-first scanner inspired by Padroniza.

## Features

- Reads and saves existing checklist data from `%APPDATA%\checklist-app\data\checklistTemplates.json`.
- Creates automatic backups before saving.
- Scans DOCX, DOCM, and PDF files into checklist sections/items.
- Detects numbered sections such as `1. DAS FORMALIDADES...`.
- Detects numbered items such as `1.1 Documento...`.
- Extracts likely normative references such as Lei, Decreto, IN, Resolução, Portaria, and Art.
- Lets the user review/edit scanned checklist rows in a table.
- Exports the full selected checklist to PDF.
- Includes a bundled application icon for the window, portable EXE, and installer.

## Local development

```powershell
cd "C:\Users\ADM\Desktop\Codigos\Python\ChecklistPython"

py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Build locally on Windows

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_github.ps1 -Version v1.0.0 -SkipInstaller
```

To build the installer too, install Inno Setup 6 and run:

```powershell
.\scripts\build_github.ps1 -Version v1.0.0
```

Build outputs are created in:

```text
dist\release\
```

## GitHub release workflow

The workflow is located at:

```text
.github\workflows\release-windows.yml
```

It works like the Padroniza release flow:

1. Go to **Actions**.
2. Open **Gerar release do ChecklistPython para Windows**.
3. Click **Run workflow**.
4. Choose `patch`, `minor`, or `major`.
5. The workflow resolves the next SemVer tag, builds the Windows portable EXE, builds the installer, calculates SHA-256 hashes, uploads the workflow artifact, and publishes the files directly to GitHub Releases.

The workflow also supports semantic tag pushes such as:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

## Release assets

A release publishes:

```text
ChecklistPython-vX.Y.Z.exe
ChecklistPython-Setup-vX.Y.Z.exe
SHA256SUMS.txt
```
