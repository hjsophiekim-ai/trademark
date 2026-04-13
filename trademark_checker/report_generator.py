"""PDF 보고서를 생성한다."""

from __future__ import annotations

import datetime as dt
import os

from fpdf import FPDF


class KoreanPDF(FPDF):
    def __init__(self) -> None:
        super().__init__()
        self.font_family_name = "Helvetica"
        regular_font = "C:/Windows/Fonts/malgun.ttf"
        bold_font = "C:/Windows/Fonts/malgunbd.ttf"

        try:
            if os.path.exists(regular_font):
                self.add_font("Malgun", "", regular_font)
                self.font_family_name = "Malgun"
            if os.path.exists(bold_font):
                self.add_font("Malgun", "B", bold_font)
        except Exception:
            self.font_family_name = "Helvetica"

    def kfont(self, size: int = 11, bold: bool = False) -> None:
        style = "B" if bold and self.font_family_name == "Malgun" else ""
        self.set_font(self.font_family_name, style, size)


def _safe_text(value: str) -> str:
    return (
        value.replace("\n", " ")
        .replace("⛔", "불가")
        .replace("✅", "확인")
        .replace("⚠️", "주의")
        .replace("⚠", "주의")
        .replace("→", "->")
        .strip()
    )


def generate_report_pdf(payload: dict) -> bytes:
    pdf = KoreanPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    content_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.kfont(18, bold=True)
    pdf.cell(0, 12, "상표등록 가능성 검토 서비스", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    pdf.cell(0, 8, f"작성일: {dt.date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    summary_rows = [
        ("상표명", payload["trademark_name"]),
        ("상표 유형", payload["trademark_type"]),
        ("상품군", ", ".join(payload["selected_classes"]) or "-"),
        ("유사군 코드", ", ".join(payload["selected_codes"]) or "-"),
        ("등록 가능성", f'{payload["score"]}% - {payload["score_label"]}'),
        ("식별력", payload["distinctiveness"]),
        ("선행상표", f'{payload["prior_count"]}건'),
    ]

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "검토 요약", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    for label, value in summary_rows:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, _safe_text(f"{label}: {value}"))
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "주요 선행상표", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    if not payload["top_prior"]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, "확인된 주요 선행상표가 없습니다.")
    else:
        for index, item in enumerate(payload["top_prior"], start=1):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                content_width,
                7,
                _safe_text(
                    f"{index}. {item.get('trademarkName', '-')}"
                    f" | {item.get('registerStatus', '-')}"
                    f" | {item.get('classificationCode', '-')}"
                    f" | 유사도 {item.get('similarity', 0)}%"
                ),
            )
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(content_width, 7, _safe_text(f"출원인: {item.get('applicantName', '-')}"))
            pdf.ln(1)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "개선 방안", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    for option in payload["name_options"]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, _safe_text(f"상표명 대안: {option['name']} -> 예상 {option['expected_score']}%"))
    for option in payload["scope_options"]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            content_width,
            7,
            _safe_text(f"{option['title']}: {option['description']} (예상 {option['expected_score']}%)"),
        )
    for option in payload["class_options"]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            content_width,
            7,
            _safe_text(f"{option['title']}: {option['description']} (예상 {option['expected_score']}%)"),
        )

    pdf.ln(4)
    pdf.kfont(8)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(content_width, 5, "본 결과는 AI 분석 참고용이며 최종 판단은 변리사 상담을 권장합니다.")
    return bytes(pdf.output())
