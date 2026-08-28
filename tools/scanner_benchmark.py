from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scanner import analyze_document

FIXTURE = ROOT / "tests" / "fixtures" / "checklist_administrativo_lei_14133.pdf"
EXPECTED_NUMBERS = [
    "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "1.10", "1.11", "1.12", "1.13", "1.14", "1.15", "1.16", "1.17",
    "2.1", "2.2", "2.2.2", "2.3", "2.4",
    "3.1", "3.1.1", "3.1.2",
    "4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8", "4.9", "4.10", "4.11",
    "5.1", "5.2", "5.3", "5.4",
]


def main() -> int:
    if not FIXTURE.exists():
        print(f"fixture ausente: {FIXTURE}", file=sys.stderr)
        return 2
    result = analyze_document(FIXTURE)
    numbers = [item["number"] for item in result.candidates]
    failures: list[str] = []
    if result.report.structure_kind != "official_singra_checklist":
        failures.append(f"estrutura inesperada: {result.report.structure_kind}")
    if result.report.page_count != 8:
        failures.append(f"páginas: {result.report.page_count} != 8")
    if result.report.table_header_pages != 8:
        failures.append(f"cabeçalhos: {result.report.table_header_pages} != 8")
    if numbers != EXPECTED_NUMBERS:
        failures.append("sequência de itens divergiu do benchmark")
    if result.report.blocking_issue_count:
        failures.append(f"erros bloqueantes: {result.report.blocking_issue_count}")

    if failures:
        print("Scanner benchmark: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("Scanner benchmark: PASS")
    print(f" - páginas: {result.report.page_count}")
    print(f" - seções: {len(result.report.sections)}")
    print(f" - itens: {len(result.candidates)}")
    print(f" - pré-selecionados: {result.report.selected_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
