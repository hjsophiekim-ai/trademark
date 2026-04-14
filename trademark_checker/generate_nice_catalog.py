from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "data"


NICE_CLASSES = [
    {"nice_class_no": 1, "kind": "goods", "nice_class_label": "제1류", "class_heading": "공업용·과학용·농업용 화학품, 비료, 조성물"},
    {"nice_class_no": 2, "kind": "goods", "nice_class_label": "제2류", "class_heading": "페인트, 바니시, 도료, 안료, 방청제"},
    {"nice_class_no": 3, "kind": "goods", "nice_class_label": "제3류", "class_heading": "화장품, 세제, 세탁용 제제, 향료, 방향제"},
    {"nice_class_no": 4, "kind": "goods", "nice_class_label": "제4류", "class_heading": "산업용 오일, 윤활유, 연료, 왁스, 촛불"},
    {"nice_class_no": 5, "kind": "goods", "nice_class_label": "제5류", "class_heading": "약제, 의료용 제제, 건강기능식품, 위생용품"},
    {"nice_class_no": 6, "kind": "goods", "nice_class_label": "제6류", "class_heading": "일반금속 및 그 합금, 금속제 건축재료, 철물"},
    {"nice_class_no": 7, "kind": "goods", "nice_class_label": "제7류", "class_heading": "기계, 모터, 엔진, 산업장비"},
    {"nice_class_no": 8, "kind": "goods", "nice_class_label": "제8류", "class_heading": "수공구, 절삭도구, 면도기"},
    {"nice_class_no": 9, "kind": "goods", "nice_class_label": "제9류", "class_heading": "전자기기, 소프트웨어, 컴퓨터, 카메라, 측정기기"},
    {"nice_class_no": 10, "kind": "goods", "nice_class_label": "제10류", "class_heading": "의료기기, 진단기기, 수술기구"},
    {"nice_class_no": 11, "kind": "goods", "nice_class_label": "제11류", "class_heading": "조명기구, 난방기구, 조리기구, 위생설비"},
    {"nice_class_no": 12, "kind": "goods", "nice_class_label": "제12류", "class_heading": "자동차, 이동수단, 운송기기 및 부품"},
    {"nice_class_no": 13, "kind": "goods", "nice_class_label": "제13류", "class_heading": "화기, 폭발물, 불꽃놀이용품"},
    {"nice_class_no": 14, "kind": "goods", "nice_class_label": "제14류", "class_heading": "귀금속, 보석, 시계, 장신구"},
    {"nice_class_no": 15, "kind": "goods", "nice_class_label": "제15류", "class_heading": "악기 및 그 부속품"},
    {"nice_class_no": 16, "kind": "goods", "nice_class_label": "제16류", "class_heading": "종이, 문구, 인쇄물, 출판물, 포장재"},
    {"nice_class_no": 17, "kind": "goods", "nice_class_label": "제17류", "class_heading": "고무, 플라스틱, 절연재, 충전재"},
    {"nice_class_no": 18, "kind": "goods", "nice_class_label": "제18류", "class_heading": "가죽, 인조가죽, 가방, 지갑, 우산"},
    {"nice_class_no": 19, "kind": "goods", "nice_class_label": "제19류", "class_heading": "비금속 건축재료, 목재, 타일, 아스팔트"},
    {"nice_class_no": 20, "kind": "goods", "nice_class_label": "제20류", "class_heading": "가구, 거울, 액자, 비금속 용기"},
    {"nice_class_no": 21, "kind": "goods", "nice_class_label": "제21류", "class_heading": "주방용기구, 가정용품, 청소도구, 유리제품"},
    {"nice_class_no": 22, "kind": "goods", "nice_class_label": "제22류", "class_heading": "로프, 천막, 텐트, 포장용 섬유원료"},
    {"nice_class_no": 23, "kind": "goods", "nice_class_label": "제23류", "class_heading": "실, 원사, 재봉용 실"},
    {"nice_class_no": 24, "kind": "goods", "nice_class_label": "제24류", "class_heading": "직물, 침구, 커튼, 직물제 덮개"},
    {"nice_class_no": 25, "kind": "goods", "nice_class_label": "제25류", "class_heading": "의류, 신발, 모자"},
    {"nice_class_no": 26, "kind": "goods", "nice_class_label": "제26류", "class_heading": "레이스, 자수포, 리본, 단추, 장식품"},
    {"nice_class_no": 27, "kind": "goods", "nice_class_label": "제27류", "class_heading": "카펫, 매트, 벽지, 바닥재"},
    {"nice_class_no": 28, "kind": "goods", "nice_class_label": "제28류", "class_heading": "장난감, 게임기, 스포츠용품, 놀이용품"},
    {"nice_class_no": 29, "kind": "goods", "nice_class_label": "제29류", "class_heading": "육류, 수산물, 가공식품, 유제품"},
    {"nice_class_no": 30, "kind": "goods", "nice_class_label": "제30류", "class_heading": "커피, 차, 제과, 제빵, 조미료"},
    {"nice_class_no": 31, "kind": "goods", "nice_class_label": "제31류", "class_heading": "농산물, 곡물, 신선식품, 생화, 동물사료"},
    {"nice_class_no": 32, "kind": "goods", "nice_class_label": "제32류", "class_heading": "맥주, 무알코올 음료, 주스, 탄산음료"},
    {"nice_class_no": 33, "kind": "goods", "nice_class_label": "제33류", "class_heading": "알코올음료(맥주 제외)"},
    {"nice_class_no": 34, "kind": "goods", "nice_class_label": "제34류", "class_heading": "담배, 전자담배, 흡연용품"},
    {"nice_class_no": 35, "kind": "services", "nice_class_label": "제35류", "class_heading": "광고업, 사업관리업, 도소매업, 사무처리업"},
    {"nice_class_no": 36, "kind": "services", "nice_class_label": "제36류", "class_heading": "금융업, 보험업, 부동산업"},
    {"nice_class_no": 37, "kind": "services", "nice_class_label": "제37류", "class_heading": "건설업, 설치업, 수리업, 유지보수업"},
    {"nice_class_no": 38, "kind": "services", "nice_class_label": "제38류", "class_heading": "통신업, 데이터 전송업, 방송업"},
    {"nice_class_no": 39, "kind": "services", "nice_class_label": "제39류", "class_heading": "운송업, 물류업, 여행예약업, 창고업"},
    {"nice_class_no": 40, "kind": "services", "nice_class_label": "제40류", "class_heading": "재료처리업, 가공업, 맞춤제작업"},
    {"nice_class_no": 41, "kind": "services", "nice_class_label": "제41류", "class_heading": "교육업, 훈련업, 오락업, 문화활동업"},
    {"nice_class_no": 42, "kind": "services", "nice_class_label": "제42류", "class_heading": "과학기술 서비스업, 연구개발업, 소프트웨어 서비스업"},
    {"nice_class_no": 43, "kind": "services", "nice_class_label": "제43류", "class_heading": "음식점업, 카페업, 숙박업"},
    {"nice_class_no": 44, "kind": "services", "nice_class_label": "제44류", "class_heading": "의료업, 미용업, 동물관리업, 농업서비스업"},
    {"nice_class_no": 45, "kind": "services", "nice_class_label": "제45류", "class_heading": "법률업, 지식재산업, 보안업, 개인·사회서비스업"},
]


GROUPS = {
    "goods": [
        {
            "group_id": "fashion_beauty_luxury",
            "group_label": "패션/뷰티/럭셔리",
            "icon": "👜",
            "classes": [3, 14, 18, 25, 26],
            "subgroups": [
                {"subgroup_id": "beauty_cosmetics", "subgroup_label": "화장품/미용", "nice_classes": [3], "keywords": ["화장품", "미용", "스킨케어", "향수"], "similarity_codes": ["G1201", "G1202"]},
                {"subgroup_id": "jewelry_watch", "subgroup_label": "주얼리/시계", "nice_classes": [14], "keywords": ["주얼리", "귀금속", "보석", "시계"], "similarity_codes": []},
                {"subgroup_id": "bags_leather", "subgroup_label": "가방/가죽제품", "nice_classes": [18], "keywords": ["가방", "지갑", "가죽", "우산"], "similarity_codes": []},
                {"subgroup_id": "clothing_fashion", "subgroup_label": "의류/신발/모자", "nice_classes": [25], "keywords": ["의류", "패션", "신발", "모자"], "similarity_codes": ["G4503", "G450101", "G450601"]},
                {"subgroup_id": "fashion_accessories", "subgroup_label": "패션부자재/장식", "nice_classes": [26], "keywords": ["레이스", "리본", "단추", "장식"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "living_health",
            "group_label": "생활/건강",
            "icon": "🧼",
            "classes": [5, 10, 21],
            "subgroups": [
                {"subgroup_id": "health_food_pharma", "subgroup_label": "건강기능식품/의약품", "nice_classes": [5], "keywords": ["건강기능식품", "영양제", "의약품", "위생용품"], "similarity_codes": []},
                {"subgroup_id": "medical_devices", "subgroup_label": "의료기기", "nice_classes": [10], "keywords": ["의료기기", "진단기기", "수술기구"], "similarity_codes": []},
                {"subgroup_id": "household_cleaning", "subgroup_label": "주방/생활/청소용품", "nice_classes": [21], "keywords": ["주방용품", "생활용품", "청소용품", "세탁용품"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "home_interior",
            "group_label": "가구/인테리어",
            "icon": "🛋️",
            "classes": [19, 20, 24, 27],
            "subgroups": [
                {"subgroup_id": "furniture_interior", "subgroup_label": "가구/인테리어", "nice_classes": [20], "keywords": ["가구", "소파", "책상", "의자"], "similarity_codes": ["G2001", "G2002"]},
                {"subgroup_id": "building_materials", "subgroup_label": "건축자재", "nice_classes": [19], "keywords": ["건축자재", "비금속재료", "타일", "목재"], "similarity_codes": []},
                {"subgroup_id": "textile_home", "subgroup_label": "침구/직물", "nice_classes": [24], "keywords": ["침구", "직물", "커튼", "패브릭"], "similarity_codes": []},
                {"subgroup_id": "carpets_mats", "subgroup_label": "카펫/매트/벽지", "nice_classes": [27], "keywords": ["카펫", "매트", "벽지", "바닥재"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "electronics_it",
            "group_label": "전자/IT",
            "icon": "💻",
            "classes": [9, 11],
            "subgroups": [
                {"subgroup_id": "software_apps", "subgroup_label": "소프트웨어/앱", "nice_classes": [9], "keywords": ["소프트웨어", "앱", "SaaS", "AI"], "similarity_codes": ["G0901", "G0903"]},
                {"subgroup_id": "electronic_devices", "subgroup_label": "전자기기/센서", "nice_classes": [9], "keywords": ["전자기기", "카메라", "센서", "컴퓨터"], "similarity_codes": ["G0901"]},
                {"subgroup_id": "smart_home_appliances", "subgroup_label": "조명/가전/공조기기", "nice_classes": [11], "keywords": ["조명", "난방기", "주방기기", "공기조절"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "machines_mobility",
            "group_label": "기계/이동수단",
            "icon": "🚗",
            "classes": [7, 8, 12, 13],
            "subgroups": [
                {"subgroup_id": "industrial_machines", "subgroup_label": "산업기계", "nice_classes": [7], "keywords": ["기계", "모터", "산업장비"], "similarity_codes": []},
                {"subgroup_id": "hand_tools", "subgroup_label": "수공구", "nice_classes": [8], "keywords": ["수공구", "절삭도구", "농기구"], "similarity_codes": []},
                {"subgroup_id": "vehicles_parts", "subgroup_label": "자동차/부품", "nice_classes": [12], "keywords": ["자동차", "이동수단", "부품", "자전거"], "similarity_codes": []},
                {"subgroup_id": "safety_firearms", "subgroup_label": "총포/폭죽/특수안전용품", "nice_classes": [13], "keywords": ["총포", "폭죽", "보안장비"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "materials_chemicals",
            "group_label": "화학/소재",
            "icon": "🧪",
            "classes": [1, 2, 4, 6, 17],
            "subgroups": [
                {"subgroup_id": "industrial_chemicals", "subgroup_label": "산업용 화학품", "nice_classes": [1], "keywords": ["화학품", "비료", "산업용화학"], "similarity_codes": []},
                {"subgroup_id": "paints_coatings", "subgroup_label": "도료/코팅", "nice_classes": [2], "keywords": ["도료", "페인트", "안료", "코팅"], "similarity_codes": []},
                {"subgroup_id": "oils_fuels", "subgroup_label": "오일/연료", "nice_classes": [4], "keywords": ["오일", "윤활유", "연료", "왁스"], "similarity_codes": []},
                {"subgroup_id": "metal_materials", "subgroup_label": "금속자재/철물", "nice_classes": [6], "keywords": ["금속", "철물", "건축금속"], "similarity_codes": []},
                {"subgroup_id": "rubber_plastic", "subgroup_label": "고무/플라스틱", "nice_classes": [17], "keywords": ["고무", "플라스틱", "절연재"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "culture_stationery_music",
            "group_label": "문구/출판/악기",
            "icon": "📚",
            "classes": [15, 16],
            "subgroups": [
                {"subgroup_id": "musical_instruments", "subgroup_label": "악기", "nice_classes": [15], "keywords": ["악기", "피아노", "기타"], "similarity_codes": []},
                {"subgroup_id": "paper_printed", "subgroup_label": "문구/출판물", "nice_classes": [16], "keywords": ["문구", "출판", "인쇄물", "포장재"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "food_beverage",
            "group_label": "식품/음료",
            "icon": "☕",
            "classes": [29, 30, 31, 32, 33, 34],
            "subgroups": [
                {"subgroup_id": "processed_food", "subgroup_label": "가공식품", "nice_classes": [29], "keywords": ["가공식품", "유제품", "육류", "김치"], "similarity_codes": []},
                {"subgroup_id": "coffee_bakery", "subgroup_label": "커피/차/제과", "nice_classes": [30], "keywords": ["커피", "차", "제과", "면류"], "similarity_codes": ["G3001"]},
                {"subgroup_id": "fresh_agri_petfood", "subgroup_label": "농산물/신선식품/반려동물사료", "nice_classes": [31], "keywords": ["농산물", "신선식품", "사료", "생화"], "similarity_codes": []},
                {"subgroup_id": "beverages_non_alcoholic", "subgroup_label": "음료/맥주", "nice_classes": [32], "keywords": ["음료", "주스", "맥주", "탄산음료"], "similarity_codes": []},
                {"subgroup_id": "alcohol", "subgroup_label": "주류", "nice_classes": [33], "keywords": ["주류", "와인", "소주", "위스키"], "similarity_codes": []},
                {"subgroup_id": "tobacco_smokers", "subgroup_label": "담배/흡연용품", "nice_classes": [34], "keywords": ["담배", "전자담배", "흡연용품"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "sports_toys_outdoor",
            "group_label": "스포츠/레저/아웃도어",
            "icon": "🏕️",
            "classes": [22, 28],
            "subgroups": [
                {"subgroup_id": "outdoor_rope_tents", "subgroup_label": "로프/텐트/캠핑소재", "nice_classes": [22], "keywords": ["로프", "텐트", "천막", "섬유원료"], "similarity_codes": []},
                {"subgroup_id": "toys_games_sports", "subgroup_label": "장난감/게임기/스포츠용품", "nice_classes": [28], "keywords": ["장난감", "게임기", "스포츠용품", "피규어"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "yarn_fiber_craft",
            "group_label": "실/원사/공예소재",
            "icon": "🧵",
            "classes": [23],
            "subgroups": [
                {"subgroup_id": "yarn_thread", "subgroup_label": "실/원사", "nice_classes": [23], "keywords": ["실", "원사", "재봉용실", "자수실"], "similarity_codes": []},
            ],
        },
    ],
    "services": [
        {
            "group_id": "retail_business",
            "group_label": "유통/비즈니스",
            "icon": "🛍️",
            "classes": [35],
            "subgroups": [
                {"subgroup_id": "retail_wholesale", "subgroup_label": "도소매/온라인쇼핑몰", "nice_classes": [35], "keywords": ["소매업", "도매업", "쇼핑몰", "유통"], "similarity_codes": ["S2021", "S2027", "S2045", "S120907"]},
                {"subgroup_id": "advertising_marketing", "subgroup_label": "광고/마케팅", "nice_classes": [35], "keywords": ["광고", "마케팅", "브랜딩"], "similarity_codes": []},
                {"subgroup_id": "business_management", "subgroup_label": "사업관리/사무처리", "nice_classes": [35], "keywords": ["사업관리", "프랜차이즈", "사무처리"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "finance_real_estate",
            "group_label": "금융/부동산",
            "icon": "💰",
            "classes": [36],
            "subgroups": [
                {"subgroup_id": "finance_insurance", "subgroup_label": "금융/보험", "nice_classes": [36], "keywords": ["금융", "보험", "결제", "투자"], "similarity_codes": []},
                {"subgroup_id": "real_estate", "subgroup_label": "부동산/임대", "nice_classes": [36], "keywords": ["부동산", "임대", "중개"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "construction_repair",
            "group_label": "건설/수리",
            "icon": "🛠️",
            "classes": [37],
            "subgroups": [
                {"subgroup_id": "construction_installation", "subgroup_label": "건설/시공/설치", "nice_classes": [37], "keywords": ["건설", "시공", "설치", "인테리어"], "similarity_codes": []},
                {"subgroup_id": "repair_maintenance", "subgroup_label": "수리/유지보수", "nice_classes": [37], "keywords": ["수리", "정비", "유지보수"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "telecom_media",
            "group_label": "통신/미디어",
            "icon": "📡",
            "classes": [38],
            "subgroups": [
                {"subgroup_id": "telecommunications", "subgroup_label": "통신/데이터전송", "nice_classes": [38], "keywords": ["통신", "메신저", "데이터전송", "방송"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "travel_logistics",
            "group_label": "여행/물류",
            "icon": "🚚",
            "classes": [39],
            "subgroups": [
                {"subgroup_id": "transport_delivery", "subgroup_label": "운송/배송/물류", "nice_classes": [39], "keywords": ["운송", "배송", "택배", "물류"], "similarity_codes": []},
                {"subgroup_id": "travel_tour", "subgroup_label": "여행/관광/예약", "nice_classes": [39], "keywords": ["여행", "관광", "예약"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "manufacturing_custom",
            "group_label": "가공/맞춤제작",
            "icon": "🏭",
            "classes": [40],
            "subgroups": [
                {"subgroup_id": "custom_manufacturing", "subgroup_label": "가공/맞춤제작", "nice_classes": [40], "keywords": ["제조대행", "가공", "인쇄", "맞춤제작"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "education_entertainment",
            "group_label": "교육/엔터테인먼트",
            "icon": "🎓",
            "classes": [41],
            "subgroups": [
                {"subgroup_id": "education_training", "subgroup_label": "교육/훈련", "nice_classes": [41], "keywords": ["교육", "학원", "강의", "자격교육"], "similarity_codes": []},
                {"subgroup_id": "entertainment_events", "subgroup_label": "공연/오락/행사", "nice_classes": [41], "keywords": ["공연", "엔터테인먼트", "게임서비스", "행사"], "similarity_codes": []},
                {"subgroup_id": "publishing_media", "subgroup_label": "출판/콘텐츠제공", "nice_classes": [41], "keywords": ["출판", "전자출판", "콘텐츠제공"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "it_science",
            "group_label": "IT/과학기술",
            "icon": "🧠",
            "classes": [42],
            "subgroups": [
                {"subgroup_id": "software_platform", "subgroup_label": "소프트웨어서비스/SaaS/플랫폼", "nice_classes": [42], "keywords": ["소프트웨어서비스", "SaaS", "플랫폼", "호스팅"], "similarity_codes": []},
                {"subgroup_id": "research_design", "subgroup_label": "연구개발/디자인/기술자문", "nice_classes": [42], "keywords": ["연구개발", "디자인", "기술자문"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "food_hospitality",
            "group_label": "식음/숙박",
            "icon": "🍽️",
            "classes": [43],
            "subgroups": [
                {"subgroup_id": "restaurant_cafe", "subgroup_label": "카페/음식점", "nice_classes": [43], "keywords": ["카페", "식당", "음식점"], "similarity_codes": ["S4301"]},
                {"subgroup_id": "lodging", "subgroup_label": "호텔/숙박", "nice_classes": [43], "keywords": ["호텔", "숙박", "게스트하우스"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "medical_beauty_pet",
            "group_label": "의료/미용/반려동물",
            "icon": "🏥",
            "classes": [44],
            "subgroups": [
                {"subgroup_id": "medical_beauty", "subgroup_label": "병원/의료/미용", "nice_classes": [44], "keywords": ["병원", "의료서비스", "미용", "피부관리"], "similarity_codes": []},
                {"subgroup_id": "pet_agriculture", "subgroup_label": "동물병원/반려동물관리/원예", "nice_classes": [44], "keywords": ["동물병원", "반려동물관리", "원예"], "similarity_codes": []},
            ],
        },
        {
            "group_id": "legal_security_personal",
            "group_label": "법률/보안/개인서비스",
            "icon": "⚖️",
            "classes": [45],
            "subgroups": [
                {"subgroup_id": "legal_ip", "subgroup_label": "법률/지식재산", "nice_classes": [45], "keywords": ["법률", "변리", "지식재산", "라이선스"], "similarity_codes": []},
                {"subgroup_id": "security_personal", "subgroup_label": "보안/개인·사회서비스", "nice_classes": [45], "keywords": ["보안", "경호", "개인소개", "사회서비스"], "similarity_codes": []},
            ],
        },
    ],
}


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "nice_class_catalog.json").write_text(
        json.dumps(NICE_CLASSES, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (ROOT / "nice_group_catalog.json").write_text(
        json.dumps(GROUPS, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
