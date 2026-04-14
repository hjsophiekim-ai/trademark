# 니스분류 기반 상품류/상품군 UI 설계

## 1. 문서 목적
이 문서는 상품 선택 UI와 내부 저장 구조의 source of truth다.
사용자는 제품/서비스를 먼저 고르고, 그 다음 대분류와 상품군을 선택하지만, 실제 분석 엔진은 니스류 번호와 유사군코드를 기준으로 판단한다.

## 2. 기본 UX

### 2-1. 분류 1
사용자는 먼저 아래 중 하나를 선택한다.
- 제품(제품, 브랜드)
- 서비스(상호, 서비스)

### 2-2. 분류 2
- 분류 1이 goods면 goods용 대분류만 보여준다.
- 분류 1이 services면 services용 대분류만 보여준다.
- 대분류는 여러 니스류를 묶어 보여주는 UX 레이어다.

### 2-3. 상품군
- 대분류를 고르면 하위 상품군 버튼 목록을 보여준다.
- 상품군은 다중 선택 가능하다.
- 중복 니스류와 유사군코드는 자동 dedupe 한다.

### 2-4. 선택 결과 요약
화면에는 최소 아래를 보여준다.
- 선택한 분류 1
- 선택한 분류 2
- 선택한 상품군
- 연결 니스류
- 연결 유사군코드

예시:
- 선택 상품군: 세탁/청소용품, 방향/탈취제
- 연결 니스류: 제3류, 제21류

## 3. 데이터 구조

### 3-1. `nice_class_catalog.json`
- 제1류~제45류 전체를 포함한다.
- 각 항목은 최소 아래 필드를 가진다.
  - `nice_class_no`
  - `kind`: `goods` 또는 `services`
  - `nice_class_label`
  - `class_heading`

### 3-2. `nice_group_catalog.json`
- goods/services 각각에 대해 대분류와 하위 상품군을 정의한다.
- 각 대분류는 최소 아래 필드를 가진다.
  - `group_id`
  - `group_label`
  - `classes`
  - `subgroups`
- 각 `subgroup`는 최소 아래 필드를 가진다.
  - `subgroup_id`
  - `subgroup_label`
  - `nice_classes`
  - `keywords`
  - `similarity_codes`

## 4. 내부 저장 필드
선택 결과는 아래 구조로 정규화한다.
- `selected_kind`
- `selected_groups`
- `selected_subgroups`
- `selected_nice_classes`
- `selected_similarity_codes`
- `selected_keywords`
- `specific_product_text`

## 5. 니스류와 유사군코드의 관계
- 니스류는 goods(1~34류), services(35~45류) 구분과 범위 구조화에 사용한다.
- 유사군코드는 지정상품의 동일·유사 판단의 우선 기준이다.
- 같은 니스류 안에서도 유사군코드가 다르면 보조 검토군으로 남긴다.
- 다른 니스류라도 유사군코드와 상품 문맥이 강하게 맞닿으면 예외 검토군이 될 수 있다.

## 6. 분석 엔진 연결 방식
선택한 상품군은 이후 분석에서 다음처럼 사용된다.
- `selected_nice_classes` -> 상품 유사성 1차 필터
- `selected_subgroups` -> 구체 상품군 문맥
- `selected_similarity_codes` -> 유사군코드 기반 필터
- `selected_kind` -> goods/services 구분
- `selected_keywords` -> 상품군 키워드 기반 보조 추천과 예외 검토
- `specific_product_text` -> 사용자가 직접 적은 세부 상품/서비스 맥락

## 7. 우선순위
검색/추천 입력의 우선순위는 아래와 같다.
1. 사용자가 명시적으로 선택한 니스류/상품군
2. 선택 상품군의 `keywords` / `similarity_codes`
3. 기존 자유검색 매핑
4. 기존 alias 추천

즉 사용자가 UI에서 선택한 니스류와 상품군이 가장 강한 입력값이다.

## 8. 권리범위 판단과 연결
- 선택한 니스류와 상품군은 선행상표의 상품 유사성 필터를 먼저 거른다.
- 동일 유사군코드는 `exact_scope_candidates`로 본다.
- 동일 니스류이나 다른 유사군코드는 `same_class_candidates`로 본다.
- 상품-서비스업 또는 타 류 예외는 `related_market_candidates`로 본다.
- 무관한 후보는 `irrelevant_candidates`로 분리하고 최종 점수에는 직접 반영하지 않는다.

## 9. 구현 체크리스트
- 제품 선택 시 goods 대분류만 노출된다.
- 서비스 선택 시 services 대분류만 노출된다.
- 각 대분류 아래에 상품군이 노출된다.
- 모든 니스류(제1류~제45류)가 데이터에 존재한다.
- 상품군 선택 결과가 실제 니스류 번호로 저장된다.
- 이후 분석 단계에서 이 값이 실제 필터 입력으로 사용된다.

기존 표장 유사성 판단 로직은 유지하되, 최종 충돌 판단은 사용자가 선택한 니스분류, 상품군, 유사군코드 및 선행상표 상태를 종합하여 판단한다.
