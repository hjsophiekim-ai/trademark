from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from goods_scope import normalize_selected_input
from kipris_api import build_kipris_search_plan, dedupe_search_candidates, search_all_pages
from nice_catalog import flatten_subgroups, load_nice_class_catalog, subgroup_to_field
from scoring import evaluate_registration, get_score_band


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _dedupe_ints(values: list[int]) -> list[int]:
    seen = set()
    out: list[int] = []
    for v in values:
        try:
            n = int(v)
        except Exception:
            continue
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return sorted(out)


def _pick_prior_summary(item: dict) -> dict:
    return {
        "trademarkName": item.get("trademarkName", ""),
        "applicationNumber": item.get("applicationNumber", ""),
        "registrationNumber": item.get("registrationNumber", ""),
        "registerStatus": item.get("registerStatus", ""),
        "survival_label": item.get("survival_label", ""),
        "counts_toward_final_score": bool(item.get("counts_toward_final_score", False)),
        "mark_similarity": item.get("mark_similarity", 0),
        "product_similarity_score": item.get("product_similarity_score", 0),
        "confusion_score": item.get("confusion_score", 0),
        "overlap_type": item.get("overlap_type", ""),
        "overlap_basis": item.get("overlap_basis", ""),
        "overlap_codes": item.get("overlap_codes", []) or [],
        "strongest_matching_prior_codes": item.get("strongest_matching_prior_codes", []) or [],
        "strongest_matching_prior_item": item.get("strongest_matching_prior_item", "") or "",
        "product_bucket": item.get("product_bucket", ""),
    }


_SUBGROUP_ROWS = {row.get("subgroup_id"): row for row in flatten_subgroups()}


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            return _json_response(self, 200, {"ok": True})
        if path == "/api/catalog":
            class_rows = load_nice_class_catalog()
            class_map = {
                int(row["nice_class_no"]): str(row.get("nice_class_name", "")).strip()
                for row in class_rows
            }

            groups: dict[tuple[str, str], dict] = {}
            for row in _SUBGROUP_ROWS.values():
                kind = row.get("kind")
                group_id = row.get("group_id")
                if kind not in {"goods", "services"} or not group_id:
                    continue
                key = (kind, group_id)
                group = groups.get(key)
                if not group:
                    group = {
                        "kind": kind,
                        "group_id": group_id,
                        "group_label": row.get("group_label", ""),
                        "group_hint": row.get("group_hint", ""),
                        "class_nos": [],
                        "classes": [],
                        "subgroups": [],
                    }
                    groups[key] = group

                group_classes = row.get("group_classes", []) or []
                subgroup_classes = row.get("nice_classes", []) or []
                group["class_nos"] = _dedupe_ints(
                    [*group.get("class_nos", []), *group_classes, *subgroup_classes]
                )

                keywords = row.get("keywords", []) or []
                examples = [str(v).strip() for v in keywords if str(v).strip()]
                subgroup_payload = {
                    "subgroup_id": row.get("subgroup_id"),
                    "subgroup_label": row.get("subgroup_label"),
                    "nice_classes": _dedupe_ints(subgroup_classes),
                    "similarity_codes": [str(v).strip() for v in (row.get("similarity_codes", []) or []) if str(v).strip()],
                    "examples": examples[:5],
                }
                if subgroup_payload["subgroup_id"]:
                    group["subgroups"].append(subgroup_payload)

            for group in groups.values():
                class_nos = group.get("class_nos", [])
                group["classes"] = [{"no": no, "name": class_map.get(no, "")} for no in class_nos]
                group["subgroups"].sort(key=lambda item: str(item.get("subgroup_label") or ""))

            payload = {
                "ok": True,
                "kinds": [
                    {"kind": "goods", "label": "상품"},
                    {"kind": "services", "label": "서비스"},
                ],
                "groups": sorted(groups.values(), key=lambda item: (item["kind"], str(item.get("group_label") or ""))),
            }
            return _json_response(self, 200, payload)
        return _json_response(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/analyze":
            return _json_response(self, 404, {"ok": False, "error": "not_found"})

        payload = _read_json(self)
        trademark_name = str(payload.get("trademark_name", "")).strip()
        trademark_type = str(payload.get("trademark_type", "word")).strip() or "word"
        is_coined = bool(payload.get("is_coined", False))
        selected_kind = payload.get("selected_kind")
        selected_kind = selected_kind if selected_kind in {"goods", "services"} else None
        selected_group_id = str(payload.get("selected_group_id", "")).strip()
        selected_subgroup_ids = payload.get("selected_subgroup_ids") or []
        selected_subgroup_ids = [str(v).strip() for v in selected_subgroup_ids if str(v).strip()]
        selected_subgroup_ids = list(dict.fromkeys(selected_subgroup_ids))

        if not trademark_name:
            return _json_response(self, 400, {"ok": False, "error": "trademark_name_required"})
        if not selected_subgroup_ids:
            return _json_response(self, 400, {"ok": False, "error": "selected_subgroup_ids_required"})

        selected_fields: list[dict] = []
        for subgroup_id in selected_subgroup_ids:
            row = _SUBGROUP_ROWS.get(subgroup_id)
            if not row:
                continue
            selected_fields.append(subgroup_to_field(row))

        if not selected_fields:
            return _json_response(self, 400, {"ok": False, "error": "invalid_subgroup_selection"})

        derived_classes_from_fields = _dedupe_ints(
            [c for field in selected_fields for c in (field.get("nice_classes") or [])]
        )
        derived_classes = derived_classes_from_fields
        if selected_group_id:
            group_classes_raw: list[int] = []
            for row in _SUBGROUP_ROWS.values():
                if row.get("group_id") != selected_group_id:
                    continue
                if selected_kind and row.get("kind") != selected_kind:
                    continue
                group_classes_raw.extend(row.get("group_classes", []) or [])
            group_class_nos = _dedupe_ints(group_classes_raw)
            derived_classes = _dedupe_ints([*derived_classes, *group_class_nos])
        derived_codes = list(
            dict.fromkeys(
                [
                    str(code).strip().upper()
                    for field in selected_fields
                    for code in (field.get("similarity_codes") or [])
                    if str(code).strip()
                ]
            )
        )

        overlap_context = normalize_selected_input(
            selected_kind=selected_kind or selected_fields[0].get("kind"),
            selected_classes=derived_classes,
            selected_codes=derived_codes,
            selected_fields=selected_fields,
            specific_product_text="",
        )
        primary_codes = overlap_context.get("selected_primary_codes", [])
        related_codes = overlap_context.get("selected_related_codes", [])
        retail_codes = overlap_context.get("selected_retail_codes", [])

        search_plan = build_kipris_search_plan(
            trademark_name,
            derived_classes,
            primary_codes,
            related_codes=related_codes,
            retail_codes=retail_codes,
        )

        all_results: list[dict] = []
        any_search_failed = False
        last_error_msg = ""

        for step in search_plan:
            codes = step.get("codes") or [""]
            for code in codes:
                result = search_all_pages(
                    trademark_name,
                    similar_goods_code=code,
                    class_no=step.get("class_no"),
                    max_pages=step.get("max_pages", 3),
                    query_mode=step.get("query_mode", ""),
                )
                search_status = result.get("search_status", "unknown")
                is_success = result.get("success", False)
                if not is_success or search_status in {
                    "transport_error",
                    "parse_error",
                    "detail_parse_error",
                    "blocked_or_unexpected_page",
                }:
                    any_search_failed = True
                    last_error_msg = result.get("result_msg", "Unknown error")
                if result and result.get("items"):
                    all_results.extend(result["items"])

        all_results = dedupe_search_candidates(all_results)

        analysis = evaluate_registration(
            trademark_name=trademark_name,
            trademark_type=trademark_type,
            is_coined=is_coined,
            selected_classes=derived_classes,
            selected_codes=derived_codes,
            prior_items=all_results,
            selected_fields=selected_fields,
            specific_product="",
        )

        if any_search_failed:
            analysis["search_failed"] = True
            analysis["search_error_msg"] = last_error_msg
            if int(analysis.get("score", 0) or 0) > 50:
                analysis["score"] = 50
                analysis["final_registration_probability"] = 50
                analysis["band"] = get_score_band(50)

        stage1 = analysis.get("absolute_refusal_analysis", {}) or {}
        stage2 = {
            "strongest_overlap_type": analysis.get("strongest_overlap_type", ""),
            "strongest_matching_prior_item": analysis.get("strongest_matching_prior_item", ""),
            "strongest_matching_prior_codes": analysis.get("strongest_matching_prior_codes", []) or [],
            "scope_counts": analysis.get("scope_counts", {}) or {},
            "live_blockers": [_pick_prior_summary(row) for row in (analysis.get("live_blockers", []) or [])],
            "historical_references": [_pick_prior_summary(row) for row in (analysis.get("historical_references", []) or [])],
            "search_failed": bool(analysis.get("search_failed", False)),
            "search_error_msg": str(analysis.get("search_error_msg", "")).strip(),
        }

        result_payload = {
            "score": analysis.get("score", 0),
            "final_registration_probability": analysis.get("final_registration_probability", analysis.get("score", 0)),
            "stage1": {
                "summary": stage1.get("summary", "-"),
                "risk_level": stage1.get("risk_level", "none"),
                "probability_cap": int(stage1.get("probability_cap", analysis.get("stage1_absolute_cap", 95)) or 95),
                "refusal_bases": stage1.get("refusal_bases", []) or [],
                "acquired_distinctiveness_needed": bool(stage1.get("acquired_distinctiveness_needed", False)),
            },
            "stage2": stage2,
        }

        return _json_response(self, 200, {"ok": True, "result": result_payload})


def main() -> None:
    host = os.getenv("TRADEMARK_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("TRADEMARK_API_PORT", "8001") or "8001")
    server = HTTPServer((host, port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()

