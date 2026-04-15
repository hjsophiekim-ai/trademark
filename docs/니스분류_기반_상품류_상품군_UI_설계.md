# 니스분류 기반 상품류/상품군 UI 설계

## 1. 문서 목적
이 문서는 상품 선택 UI와 내부 저장 구조의 source of truth다.
상품류/상품군 데이터의 최상위 기준은 `docs/지식재산처_상품분류_니스분류.xlsx`다.
`nice_class_catalog.json`, `nice_group_catalog.json`은 이 엑셀을 기반으로 생성되는 캐시다.

## 2. 기본 UX

### 2-1. 분류 1
사용자는 먼저 아래 중 하나를 선택한다.
- 제품(제품, 브랜드)
- 서비스(상호, 서비스)

### 2-2. 분류 2
- 분류 2는 요약형 UI 카테고리다.
- 이 단계에서는 짧은 카테고리명만 보여준다.
- 긴 니스류 설명, class_heading 전문, 상품군 전체 목록은 이 화면에 노출하지 않는다.
- 카드에는 아래만 보여준다.
- `group_label`
- `group_hint`
- `연결 니스류: 제OO류`

예시:
- 제품: 패션의류/잡화, 뷰티, 식품, 가구/인테리어, 생활/건강, 소프트웨어
- 서비스: 요식업/식품, 뷰티/미용, 교육/유아/반려동물, IT/플랫폼/APP, 기타 서비스

### 2-3. 구체상품군 선택
- 분류 2를 선택한 뒤 `구체상품군 선택 단계로 이동` 버튼을 눌러 별도 단계로 들어간다.
- 이 단계의 제목은 `3. 구체상품군 선택`을 사용한다.
- 설명 문구는 `선택한 카테고리에 해당하는 상품군을 선택하세요`를 사용한다.
- 여기서만 실제 `subgroup_label` 목록을 보여준다.
- 상품군은 복수 선택 가능하다.

### 2-4. 다음 버튼 활성화 조건
- 분류 1 선택 전: 다음 버튼 비활성화
- 분류 2 선택 전: `구체상품군 선택 단계로 이동` 버튼 비활성화
- 분류 2 선택 완료 후: `구체상품군 선택 단계로 이동` 버튼 활성화
- 구체상품군 미선택 상태: `다음 단계: 구체 상품/서비스의 유사군코드 선택` 버튼 비활성화
- 구체상품군 1개 이상 선택 후: 위 버튼 활성화

## 3. 데이터 구조

### 3-1. `nice_class_catalog.json`
`docs/지식재산처_상품분류_니스분류.xlsx` 기반으로 제1류~제45류 전체를 포함한다.
각 항목은 최소 아래 필드를 가진다.
- `kind`
- `nice_class_no`
- `nice_class_label`
- `class_heading`
- `source: excel`

### 3-2. `nice_group_catalog.json`
goods/services 각각에 대해 요약형 UI 카테고리와 하위 상품군을 정의한다.
각 그룹은 최소 아래 필드를 가진다.
- `kind`
- `group_id`
- `group_label`
- `group_hint`
- `classes`
- `subgroups`
- `source: excel`

각 `subgroup`는 최소 아래 필드를 가진다.
- `kind`
- `group_id`
- `group_label`
- `subgroup_id`
- `subgroup_label`
- `nice_classes`
- `keywords`
- `similarity_codes`
- `class_heading`
- `source: excel`

## 4. 내부 저장 필드
선택 결과는 아래 구조로 정규화한다.
- `selected_kind`
- `selected_group`
- `selected_groups`
- `selected_subgroups`
- `selected_nice_classes`
- `selected_similarity_codes`
- `recommended_similarity_codes`
- `selected_keywords`
- `specific_product_text`

저장 원칙은 아래와 같다.
- `selected_group`은 현재 화면에서 열어둔 요약형 카테고리다.
- `selected_groups`는 실제로 선택한 subgroup가 속한 UI 카테고리 라벨 목록이다.
- `selected_subgroups`는 실제로 선택한 구체상품군 라벨 목록이다.
- `selected_nice_classes`는 subgroup에 연결된 실제 니스류 번호 목록이다.
- `selected_similarity_codes`는 Step 3에서 사용자가 확정한 유사군코드 목록이다.

## 5. 모바일 우선 UX 원칙
- 한 단계에 한 종류의 선택만 하게 한다.
- 카드/칩 간격을 일정하게 유지한다.
- 긴 문단을 카드 안에 넣지 않는다.
- 선택 시 버튼과 카드 상태를 명확히 구분한다.
- 2~3열 grid는 허용하지만 카드 높이는 가급적 균일하게 유지한다.
- 선택 요약은 별도 영역으로 분리한다.

## 6. 분석 엔진 연결 방식
화면은 요약형이지만 내부 판단 입력은 정교하게 유지한다.
- `selected_subgroups` -> 구체 상품군 문맥
- `selected_nice_classes` -> 상품 유사성 1차 필터
- `selected_similarity_codes` -> 유사군코드 기반 필터
- `selected_kind` -> goods/services 구분
- `selected_keywords` -> 보조 추천과 예외 검토

즉 분류 2는 UI 카테고리일 뿐이고, 실제 판단의 시작점은 subgroup/nice class/similarity code다.
