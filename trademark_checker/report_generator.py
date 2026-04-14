"""PDF 보고서를 생성한다."""

from __future__ import annotations

import datetime as dt
import os

from fpdf import FPDF

from nice_catalog import format_nice_classes


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
    return str(value or "").replace("\n", " ").strip()


def _write_lines(pdf: KoreanPDF, content_width: float, lines: list[str]) -> None:
    for line in lines:
        if not line:
            continue
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, _safe_text(line))


def _kind_label(kind: str | None) -> str:
    if kind == "goods":
        return "제품(goods)"
    if kind == "services":
        return "서비스(services)"
    return "-"


def _render_single_report(pdf: KoreanPDF, content_width: float, payload: dict, title: str | None = None) -> None:
    if title:
        pdf.kfont(13, bold=True)
        pdf.cell(0, 8, _safe_text(title), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    summary_rows = [
        ("구체 상품", payload.get("specific_product", "-") or "-"),
        ("분류 1", _kind_label(payload.get("selected_kind"))),
        ("분류 2", ", ".join(payload.get("selected_groups", [])) or "-"),
        ("상품군", ", ".join(payload.get("selected_subgroups", [])) or "-"),
        ("연결 니스류", format_nice_classes(payload.get("selected_nice_classes", [])) or "-"),
        ("연결 유사군코드", ", ".join(payload.get("selected_similarity_codes", payload.get("selected_codes", []))) or "-"),
        ("등록 가능성", f'{payload.get("score", 0)}% - {payload.get("score_label", "-")}'),
        ("식별력", payload.get("distinctiveness", "-")),
        (
            "검색/필터",
            f'전체 {payload.get("total_prior_count", payload.get("prior_count", 0))}건 / '
            f'필터 통과 {payload.get("filtered_prior_count", payload.get("prior_count", 0))}건 / '
            f'제외 {payload.get("excluded_prior_count", 0)}건',
        ),
        (
            "실질 충돌/참고",
            f'실질 장애물 {payload.get("direct_score_prior_count", 0)}건 / '
            f'역사적 참고자료 {payload.get("historical_reference_count", 0)}건',
        ),
    ]

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "검토 요약", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    for label, value in summary_rows:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, _safe_text(f"{label}: {value}"))
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "식별력 판단", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    distinctiveness = payload.get("distinctiveness_analysis", {})
    _write_lines(
        pdf,
        content_width,
        [distinctiveness.get("summary", payload.get("distinctiveness", "-"))]
        + [f"- {reason}" for reason in distinctiveness.get("reasons", [])],
    )
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "점수 설명", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    score_explanation = payload.get("score_explanation", {})
    _write_lines(
        pdf,
        content_width,
        [
            f"최종 점수 {payload.get('score', 0)}% (보정 전 {score_explanation.get('raw_score', payload.get('score', 0))}%)",
            score_explanation.get("summary", "최종 점수는 실질 장애물만 직접 반영했습니다."),
        ]
        + [f"- {note}" for note in score_explanation.get("notes", [])],
    )
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "상품 유사성 필터", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    product_analysis = payload.get("product_similarity_analysis", {})
    scope_counts = product_analysis.get("scope_counts", {})
    _write_lines(
        pdf,
        content_width,
        [
            product_analysis.get("summary", "-"),
            (
                f"실질 충돌 후보 {scope_counts.get('exact_scope_candidates', 0)}건 / "
                f"동일 니스류 보조 검토군 {scope_counts.get('same_class_candidates', 0)}건 / "
                f"상품-서비스업 예외 검토군 {scope_counts.get('related_market_candidates', 0)}건 / "
                f"제외 후보 {scope_counts.get('irrelevant_candidates', 0)}건"
            ),
        ],
    )
    if product_analysis.get("exclusion_reason_summary"):
        _write_lines(pdf, content_width, [product_analysis["exclusion_reason_summary"]])
    if product_analysis.get("reference_summary"):
        _write_lines(pdf, content_width, [product_analysis["reference_summary"]])
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "표장 유사성 판단", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    _write_lines(
        pdf,
        content_width,
        [
            payload.get("mark_similarity_analysis", {}).get("summary", "-"),
            "완전 동일한 선행상표가 있으나 현재 상태가 거절/취하/포기/소멸인 경우, 원칙적으로 직접 장애물로 보지 않고 참고자료로만 봅니다.",
            "등록 또는 출원 상태의 동일/유사 상표는 실질 장애물로 평가합니다.",
            "거절 상표는 거절이유의 핵심이 현재 상표와 직접 관련되는 경우에만 보조 경고로 반영합니다.",
        ],
    )
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "혼동 가능성 종합", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    _write_lines(
        pdf,
        content_width,
        [
            payload.get("confusion_analysis", {}).get("summary", "-"),
            (
                f"실질 장애물 {payload.get('direct_score_prior_count', 0)}건 / "
                f"역사적 참고자료 {payload.get('historical_reference_count', 0)}건"
            ),
        ],
    )
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "주요 선행상표", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    top_prior = payload.get("top_prior", [])
    if not top_prior:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, "상품 유사성 필터를 통과한 주요 선행상표가 없습니다.")
    else:
        for index, item in enumerate(top_prior, start=1):
            _write_lines(
                pdf,
                content_width,
                [
                    (
                        f"{index}. {item.get('trademarkName', '-')} | 상태 {item.get('status_normalized', item.get('registerStatus', '-'))} "
                        f"| {item.get('survival_label', '-')} | 류 {item.get('classificationCode', '-')} "
                        f"| 상태 반영 후 혼동위험 {item.get('confusion_score', 0)}%"
                    ),
                    (
                        f"점수 반영 여부: {item.get('score_reflection_label', '-')} | "
                        f"상품 유사도: {item.get('product_similarity_score', 0)}% ({item.get('product_similarity_label', '-')}) | "
                        f"표장 유사도: {item.get('mark_similarity', item.get('similarity', 0))}%"
                    ),
                    f"출원인: {item.get('applicantName', '-')}",
                    f"상품 범위 판단: {item.get('product_reason', '-')}",
                ],
            )
            refusal = item.get("refusal_analysis", {})
            if refusal.get("reason_summary"):
                _write_lines(
                    pdf,
                    content_width,
                    [
                        f"거절이유 요약: {refusal.get('reason_summary')} (현재 상표 관련성: {refusal.get('current_mark_relevance_label', '-')})"
                    ],
                )
            if refusal.get("cited_marks"):
                _write_lines(pdf, content_width, [f"인용상표: {', '.join(refusal.get('cited_marks', []))}"])
            if refusal.get("weak_elements") or refusal.get("refusal_core"):
                _write_lines(
                    pdf,
                    content_width,
                    [
                        f"약한 요소: {', '.join(refusal.get('weak_elements', [])) or '-'} / 거절 핵심 요부: {refusal.get('refusal_core', '-') or '-'}"
                    ],
                )
            pdf.ln(1)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "개선 방안", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    for option in payload.get("name_options", []):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, _safe_text(f"상표명 대안: {option['name']} -> 예상 {option['expected_score']}%"))
    for option in payload.get("scope_options", []):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            content_width,
            7,
            _safe_text(f"{option['title']}: {option['description']} (예상 {option['expected_score']}%)"),
        )
    for option in payload.get("class_options", []):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            content_width,
            7,
            _safe_text(f"{option['title']}: {option['description']} (예상 {option['expected_score']}%)"),
        )
    pdf.ln(4)


def generate_report_pdf(payload: dict) -> bytes:
    pdf = KoreanPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    content_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.kfont(18, bold=True)
    pdf.cell(0, 12, "상표등록 가능성 검토 보고서", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    pdf.cell(0, 8, f"작성일: {dt.date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "기본 정보", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    for label, value in [
        ("상표명", payload.get("trademark_name", "-")),
        ("상표 유형", payload.get("trademark_type", "-")),
        ("분류 1", _kind_label(payload.get("selected_kind"))),
        ("분류 2", ", ".join(payload.get("selected_groups", [])) or "-"),
        ("상품군", ", ".join(payload.get("selected_subgroups", [])) or "-"),
        ("연결 니스류", format_nice_classes(payload.get("selected_nice_classes", [])) or "-"),
        ("연결 유사군코드", ", ".join(payload.get("selected_similarity_codes", [])) or "-"),
    ]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(content_width, 7, _safe_text(f"{label}: {value}"))
    pdf.ln(2)

    field_reports = payload.get("field_reports")
    if field_reports:
        pdf.kfont(12, bold=True)
        pdf.cell(0, 8, f"상품군별 판단 결과: {len(field_reports)}건", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for index, report in enumerate(field_reports, start=1):
            _render_single_report(pdf, content_width, report, title=f"{index}. {report.get('field_label', '상품군')}")
            if index < len(field_reports):
                pdf.add_page()
    else:
        _render_single_report(pdf, content_width, payload)

    pdf.kfont(8)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(content_width, 5, "본 결과는 AI 분석 참고용이며 최종 판단은 변리사 상담을 권장합니다.")
    return bytes(pdf.output())
