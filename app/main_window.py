from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .pdf_exporter import export_checklist_pdf
from .scanner import scan_document_to_template
from .storage import DATA_FILE, load_templates, new_id, save_templates


class ChecklistMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Checklist Application — Python")
        self.resize(1400, 850)

        self.templates: list[dict[str, Any]] = []
        self.active_checklist_id: str | None = None
        self.row_map: list[dict[str, int | str]] = []
        self.loading_table = False
        self.pending_delete_key: str | None = None

        self.load_data()
        self.build_ui()
        self.refresh_checklist_list()

        if self.templates:
            self.select_checklist(str(self.templates[0]["id"]))
        else:
            self.render_empty_table()
            self.show_status("Nenhum checklist encontrado. Use Escanear DOCX/PDF para criar um checklist.")

    def load_data(self) -> None:
        try:
            self.templates = load_templates()
        except Exception as error:
            self.templates = []
            self.show_startup_error = str(error)
        else:
            self.show_startup_error = ""

    def build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.btn_scan = QPushButton("Escanear DOCX/PDF")
        self.btn_new = QPushButton("Novo vazio")
        self.btn_save = QPushButton("Salvar")
        self.btn_copy = QPushButton("Copiar checklist")
        self.btn_delete = QPushButton("Excluir selecionado")
        self.btn_add_section = QPushButton("Adicionar seção")
        self.btn_add_item = QPushButton("Adicionar item")
        self.btn_export_pdf = QPushButton("Exportar PDF completo")

        for button in [
            self.btn_scan,
            self.btn_new,
            self.btn_save,
            self.btn_copy,
            self.btn_delete,
            self.btn_add_section,
            self.btn_add_item,
            self.btn_export_pdf,
        ]:
            toolbar.addWidget(button)

        toolbar.addStretch(1)
        root_layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.build_sidebar())
        splitter.addWidget(self.build_content())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 1080])

        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(root)

        self.btn_scan.clicked.connect(self.scan_file)
        self.btn_new.clicked.connect(self.create_empty_checklist)
        self.btn_save.clicked.connect(self.save_now)
        self.btn_copy.clicked.connect(self.copy_active_checklist)
        self.btn_delete.clicked.connect(self.delete_selected_row_or_checklist)
        self.btn_add_section.clicked.connect(self.add_section)
        self.btn_add_item.clicked.connect(self.add_item)
        self.btn_export_pdf.clicked.connect(self.export_pdf)

        if self.show_startup_error:
            self.show_status(f"Erro ao carregar JSON: {self.show_startup_error}")

    def build_sidebar(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(8)

        title = QLabel("Checklists")
        title.setStyleSheet("font-weight: 800; font-size: 16px;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar checklist...")
        self.search_input.textChanged.connect(self.refresh_checklist_list)

        self.checklist_list = QListWidget()
        self.checklist_list.currentItemChanged.connect(self.on_checklist_selection_changed)

        path_label = QLabel(f"Arquivo local:\n{DATA_FILE}")
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #6b7280; font-size: 11px;")

        layout.addWidget(title)
        layout.addWidget(self.search_input)
        layout.addWidget(self.checklist_list, 1)
        layout.addWidget(path_label)

        return widget

    def build_content(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.title_label = QLabel("Checklist")
        self.title_label.setStyleSheet("font-weight: 900; font-size: 22px;")

        self.subtitle_label = QLabel("Selecione um checklist")
        self.subtitle_label.setStyleSheet("color: #4b5563;")
        self.subtitle_label.setWordWrap(True)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "Seção",
                "Item",
                "Documentos / Informações constantes do processo",
                "Normativos",
                "Situação",
                "Folha",
                "Observação",
            ]
        )

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setWordWrap(True)
        self.table.itemChanged.connect(self.on_table_item_changed)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.table, 1)

        return widget

    def refresh_checklist_list(self) -> None:
        if not hasattr(self, "checklist_list"):
            return

        search = normalize_text(self.search_input.text() if hasattr(self, "search_input") else "")

        self.checklist_list.blockSignals(True)
        self.checklist_list.clear()

        for template in self.templates:
            searchable = normalize_text(
                " ".join(
                    [
                        str(template.get("title") or ""),
                        str(template.get("subtitle") or ""),
                        str(template.get("baseLegal") or ""),
                    ]
                )
            )

            if search and search not in searchable:
                continue

            item = QListWidgetItem(str(template.get("title") or "Checklist sem nome"))
            item.setData(Qt.ItemDataRole.UserRole, str(template.get("id")))
            self.checklist_list.addItem(item)

            if template.get("id") == self.active_checklist_id:
                self.checklist_list.setCurrentItem(item)

        self.checklist_list.blockSignals(False)

    def on_checklist_selection_changed(self, current: QListWidgetItem | None) -> None:
        if current is None:
            return

        checklist_id = current.data(Qt.ItemDataRole.UserRole)

        if checklist_id:
            self.select_checklist(str(checklist_id))

    def select_checklist(self, checklist_id: str) -> None:
        template = self.get_template(checklist_id)

        if not template:
            return

        self.active_checklist_id = checklist_id
        self.pending_delete_key = None

        self.title_label.setText(str(template.get("title") or "Checklist"))
        self.subtitle_label.setText(format_subtitle(template))

        self.render_active_table()
        self.refresh_checklist_list()
        self.show_status(f"Checklist ativo: {template.get('title')}")

    def render_empty_table(self) -> None:
        self.loading_table = True
        self.row_map = []
        self.table.setRowCount(0)
        self.loading_table = False

    def render_active_table(self) -> None:
        template = self.get_active_template()

        if not template:
            self.render_empty_table()
            return

        self.loading_table = True
        self.row_map = []
        self.table.setRowCount(0)

        sections = template.get("sections") if isinstance(template.get("sections"), list) else []

        for section_index, section in enumerate(sections):
            section_row = self.table.rowCount()
            self.table.insertRow(section_row)

            self.row_map.append(
                {
                    "type": "section",
                    "section_index": section_index,
                }
            )

            self.table.setItem(section_row, 0, make_cell(section.get("number"), editable=True, bold=True, background="#E5E7EB"))
            self.table.setItem(section_row, 1, make_cell("", editable=False, background="#E5E7EB"))
            self.table.setItem(section_row, 2, make_cell(section.get("title"), editable=True, bold=True, background="#E5E7EB"))

            for column in range(3, 7):
                self.table.setItem(section_row, column, make_cell("", editable=False, background="#E5E7EB"))

            items = section.get("items") if isinstance(section.get("items"), list) else []

            for item_index, item in enumerate(items):
                item_row = self.table.rowCount()
                self.table.insertRow(item_row)

                self.row_map.append(
                    {
                        "type": "item",
                        "section_index": section_index,
                        "item_index": item_index,
                    }
                )

                self.table.setItem(item_row, 0, make_cell(section.get("number"), editable=False))
                self.table.setItem(item_row, 1, make_cell(item.get("number"), editable=True))
                self.table.setItem(item_row, 2, make_cell(item.get("documento"), editable=True))
                self.table.setItem(item_row, 3, make_cell(item.get("normativo"), editable=True))
                self.table.setItem(item_row, 4, make_cell(item.get("situacao") or "N/A", editable=True))
                self.table.setItem(item_row, 5, make_cell(item.get("folha"), editable=True))
                self.table.setItem(item_row, 6, make_cell(item.get("observacao"), editable=True))

        self.table.resizeRowsToContents()
        self.loading_table = False

    def on_table_item_changed(self, table_item: QTableWidgetItem) -> None:
        if self.loading_table:
            return

        row = table_item.row()
        column = table_item.column()

        if row < 0 or row >= len(self.row_map):
            return

        template = self.get_active_template()

        if not template:
            return

        row_info = self.row_map[row]
        sections = template.get("sections", [])
        section_index = int(row_info["section_index"])

        if section_index < 0 or section_index >= len(sections):
            return

        if row_info["type"] == "section":
            section = sections[section_index]

            if column == 0:
                section["number"] = table_item.text().strip()
            elif column == 2:
                section["title"] = table_item.text().strip()
            else:
                return

        elif row_info["type"] == "item":
            item_index = int(row_info["item_index"])
            items = sections[section_index].get("items", [])

            if item_index < 0 or item_index >= len(items):
                return

            item = items[item_index]

            field_by_column = {
                1: "number",
                2: "documento",
                3: "normativo",
                4: "situacao",
                5: "folha",
                6: "observacao",
            }

            field_name = field_by_column.get(column)

            if not field_name:
                return

            item[field_name] = table_item.text()

        self.save_now(silent=True)

    def scan_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Escanear documento",
            "",
            "Documentos (*.docx *.docm *.pdf)",
        )

        if not file_path:
            self.show_status("Scanner cancelado.")
            return

        try:
            template = scan_document_to_template(file_path)
            template["title"] = self.create_unique_title(str(template.get("title") or Path(file_path).stem))

            self.templates.append(template)
            save_templates(self.templates)

            self.refresh_checklist_list()
            self.select_checklist(str(template["id"]))
            self.show_status(f"Checklist criado pelo scanner: {template['title']}")
        except Exception as error:
            self.show_status(f"Erro no scanner: {error}")

    def create_empty_checklist(self) -> None:
        title = self.create_unique_title("Novo Checklist")

        template = {
            "id": new_id("checklist"),
            "title": title,
            "subtitle": "",
            "baseLegal": "",
            "description": "",
            "sections": [
                {
                    "id": new_id("section"),
                    "number": "1",
                    "title": "NOVA SEÇÃO",
                    "items": [],
                }
            ],
        }

        self.templates.append(template)
        self.save_now(silent=True)
        self.refresh_checklist_list()
        self.select_checklist(str(template["id"]))
        self.show_status("Checklist vazio criado. Edite os campos diretamente na tabela.")

    def copy_active_checklist(self) -> None:
        template = self.get_active_template()

        if not template:
            self.show_status("Selecione um checklist para copiar.")
            return

        copied = copy.deepcopy(template)
        copied["id"] = new_id("checklist")
        copied["title"] = self.create_unique_title(f"{template.get('title', 'Checklist')} - Cópia")

        for section in copied.get("sections", []):
            section["id"] = new_id("section")

            for item in section.get("items", []):
                item["id"] = new_id("item")

        self.templates.append(copied)
        self.save_now(silent=True)
        self.refresh_checklist_list()
        self.select_checklist(str(copied["id"]))
        self.show_status(f"Checklist copiado: {copied['title']}")

    def add_section(self) -> None:
        template = self.get_active_template()

        if not template:
            self.show_status("Selecione um checklist primeiro.")
            return

        sections = template.setdefault("sections", [])
        section_number = str(len(sections) + 1)

        sections.append(
            {
                "id": new_id("section"),
                "number": section_number,
                "title": "NOVA SEÇÃO",
                "items": [],
            }
        )

        self.save_now(silent=True)
        self.render_active_table()
        self.show_status("Seção adicionada.")

    def add_item(self) -> None:
        template = self.get_active_template()

        if not template:
            self.show_status("Selecione um checklist primeiro.")
            return

        sections = template.setdefault("sections", [])

        if not sections:
            self.add_section()
            sections = template.setdefault("sections", [])

        section_index = self.get_current_section_index()
        section = sections[section_index]
        items = section.setdefault("items", [])
        item_number = f"{section.get('number')}.{len(items) + 1}"

        items.append(
            {
                "id": new_id("item"),
                "number": item_number,
                "documento": "Novo documento / informação",
                "normativo": "",
                "situacao": "N/A",
                "folha": "",
                "observacao": "",
                "description": "",
                "requiredDocuments": [],
                "notes": [],
            }
        )

        self.save_now(silent=True)
        self.render_active_table()
        self.show_status("Item adicionado.")

    def get_current_section_index(self) -> int:
        row = self.table.currentRow()
        template = self.get_active_template()
        section_count = len(template.get("sections", [])) if template else 0

        if row >= 0 and row < len(self.row_map):
            index = int(self.row_map[row]["section_index"])

            if 0 <= index < section_count:
                return index

        return max(0, section_count - 1)

    def delete_selected_row_or_checklist(self) -> None:
        template = self.get_active_template()

        if not template:
            self.show_status("Nenhum checklist selecionado para excluir.")
            return

        row = self.table.currentRow()

        if row < 0 or row >= len(self.row_map):
            key = f"checklist:{template['id']}"

            if self.pending_delete_key != key:
                self.pending_delete_key = key
                self.show_status("Clique em Excluir selecionado novamente para excluir o checklist inteiro.")
                return

            self.templates = [item for item in self.templates if item.get("id") != template.get("id")]
            self.active_checklist_id = None

            self.save_now(silent=True)
            self.refresh_checklist_list()

            if self.templates:
                self.select_checklist(str(self.templates[0]["id"]))
            else:
                self.render_empty_table()

            self.show_status("Checklist excluído.")
            return

        row_info = self.row_map[row]
        section_index = int(row_info["section_index"])
        sections = template.get("sections", [])

        if row_info["type"] == "section":
            key = f"section:{section_index}"

            if self.pending_delete_key != key:
                self.pending_delete_key = key
                self.show_status("Clique novamente para excluir esta seção e todos os itens dentro dela.")
                return

            if 0 <= section_index < len(sections):
                del sections[section_index]
                self.pending_delete_key = None
                self.save_now(silent=True)
                self.render_active_table()
                self.show_status("Seção excluída.")

            return

        if row_info["type"] == "item":
            item_index = int(row_info["item_index"])
            key = f"item:{section_index}:{item_index}"

            if self.pending_delete_key != key:
                self.pending_delete_key = key
                self.show_status("Clique novamente para excluir este item.")
                return

            items = sections[section_index].get("items", [])

            if 0 <= item_index < len(items):
                del items[item_index]
                self.pending_delete_key = None
                self.save_now(silent=True)
                self.render_active_table()
                self.show_status("Item excluído.")

    def export_pdf(self) -> None:
        template = self.get_active_template()

        if not template:
            self.show_status("Selecione um checklist para exportar.")
            return

        suggested_name = sanitize_filename(str(template.get("title") or "checklist")) + ".pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar PDF completo",
            suggested_name,
            "PDF (*.pdf)",
        )

        if not file_path:
            self.show_status("Exportação PDF cancelada.")
            return

        try:
            output_path = export_checklist_pdf(template, file_path)
            self.show_status(f"PDF exportado: {output_path}")
        except Exception as error:
            self.show_status(f"Erro ao exportar PDF: {error}")

    def save_now(self, silent: bool = False) -> None:
        try:
            path = save_templates(self.templates)

            if not silent:
                self.show_status(f"Dados salvos em: {path}")
        except Exception as error:
            self.show_status(f"Erro ao salvar: {error}")

    def get_template(self, checklist_id: str) -> dict[str, Any] | None:
        for template in self.templates:
            if str(template.get("id")) == checklist_id:
                return template

        return None

    def get_active_template(self) -> dict[str, Any] | None:
        if not self.active_checklist_id:
            return None

        return self.get_template(self.active_checklist_id)

    def create_unique_title(self, desired_title: str) -> str:
        existing = {normalize_text(str(template.get("title") or "")) for template in self.templates}
        base = desired_title.strip() or "Checklist"

        if normalize_text(base) not in existing:
            return base

        counter = 2

        while normalize_text(f"{base} {counter}") in existing:
            counter += 1

        return f"{base} {counter}"

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 10000)


def make_cell(
    value: Any,
    editable: bool = True,
    bold: bool = False,
    background: str | None = None,
) -> QTableWidgetItem:
    item = QTableWidgetItem(str(value or ""))

    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

    if bold:
        font = item.font()
        font.setBold(True)
        item.setFont(font)

    if background:
        item.setBackground(QColor(background))

    return item


def format_subtitle(template: dict[str, Any]) -> str:
    parts = []

    if template.get("subtitle"):
        parts.append(str(template.get("subtitle")))

    if template.get("baseLegal"):
        parts.append(f"Base legal: {template.get('baseLegal')}")

    if not parts:
        parts.append("Sem subtítulo / base legal")

    return " | ".join(parts)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def sanitize_filename(value: str) -> str:
    safe = re.sub(r"[<>:\"/\\|?*\x00-\x1F]", " ", value)
    safe = re.sub(r"\s+", " ", safe).strip()

    return safe[:120] or "checklist"
