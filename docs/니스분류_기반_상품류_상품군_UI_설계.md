# 니스분류 기반 상품류/상품군 UI 설계

## 1. 목적
Step 2 상품범위 선택 화면은 아래 사용자 흐름만 제공한다.

1. 분류 1 선택
2. 분류 2 선택
3. 구체상품군 선택
4. 검토 실행
5. 결과
6. 개선방안

사용자에게 유사군코드를 다시 고르게 하지 않는다. 유사군코드는 시스템 내부 파생값으로만 사용한다.

데이터 source of truth는 아래로 고정한다.

- 구체상품군/니스류: `docs/지식재산처_상품분류_니스분류.xlsx`
- 유사군코드: `docs/상품유사군코드.xlsx`

## 2. 상태 머신
- `step_main = 2`
- `step_scope_sub = "group" | "subgroup" | "review_ready"`

필수 상태값은 아래와 같다.

- `selected_kind`
- `selected_group_id`
- `selected_group_label`
- `selected_subgroup_ids`
- `selected_subgroup_labels`
- `derived_nice_classes`
- `derived_similarity_codes`
- `subgroup_keywords`

레거시 호환용으로 `selected_group`, `selected_groups`, `selected_subgroups`를 유지할 수는 있지만, Step 전환 판단의 기준은 아래 새 상태값이다.

## 3. 분류 2 저장 규칙
분류 2 카테고리 클릭 시 즉시 아래 값이 `session_state`에 저장되어야 한다.

- `selected_group_id`
- `selected_group_label`
- `step_scope_sub = "group"`

중요 규칙:

- 분류 2 선택 직후 rerun 되어도 `selected_group_id`는 지워지면 안 된다.
- 하위 `selected_subgroup_ids`를 비우더라도 `selected_group_id`는 유지해야 한다.
- `selected_group` 같은 레거시 키는 필요하면 alias로만 유지한다.

## 4. 버튼 활성화 조건
`구체상품군 선택 단계로 이동` 버튼 활성화 조건은 아래 두 가지만 본다.

- `selected_kind` 존재
- `selected_group_id` 존재

아래 값들은 이 버튼 활성화 조건에 사용하지 않는다.

- `selected_codes`
- `selected_fields`
- `field_inputs`
- 기타 레거시 유사군코드 관련 값

## 5. Step 3 렌더링 조건
Step 3은 별도 화면처럼 보이게 렌더링한다.

- 제목: `3. 구체상품군 선택`
- 설명: `선택한 카테고리에 해당하는 상품군을 1개 이상 선택하세요`

렌더링 조건:

- `step_scope_sub in {"subgroup", "review_ready"}`
- `selected_kind` 존재
- `selected_group_id` 존재

즉, `selected_codes`가 비어 있어도 Step 3 렌더링을 막지 않는다.

## 6. 구체상품군 선택 완료 규칙
Step 3에서 구체상품군을 1개 이상 선택하면 아래가 계산되어야 한다.

- `selected_subgroup_ids`
- `selected_subgroup_labels`
- `derived_nice_classes`
- `derived_similarity_codes`
- `subgroup_keywords`
- `step_scope_sub = "review_ready"`

검토 실행 가능 조건은 `selected_subgroup_ids`가 1개 이상 존재하는지로 판단한다.

## 7. 유사군코드 처리 원칙
유사군코드는 사용자 입력 단계가 아니다.

- 사용자 선택 기준: `selected_subgroup_ids`
- 시스템 파생 기준: `derived_similarity_codes`
- subgroup별 매핑은 `상품유사군코드.xlsx` 기준 실제 예규 코드만 사용한다.
- 가상코드(`S3601`, `S3602`, `S3603`)와 클래스 번호 문자열 조합식 코드는 금지한다.

자동 매핑 순서는 아래와 같다.

1. `exact_label_match`
2. `normalized_semantic_match`
3. `keyword_dictionary_match`
4. `same_class_fallback`

표시 원칙:

- Step 2/Step 3에서는 필요 시 `내부 도출 유사군코드`로만 참고 표시 가능
- 사용자-facing 단계명에 `유사군코드 선택`을 넣지 않음
- Step 3 완료 후에는 별도 코드 선택 화면 없이 바로 `검토 실행`으로 이동한다.

## 8. 디버그 표시
개발용 디버그 표시는 아래 값을 확인할 수 있어야 한다.

- `selected_kind`
- `selected_group_id`
- `step_scope_sub`
- `len(selected_subgroup_ids)`
- `selected_subgroups`
- `candidate_similarity_codes`
- `chosen_similarity_codes`
- `match_reason`
- `match_confidence`
- `fallback_used`

버그 수정 완료 후에도 숨김 expander 형태로 유지 가능하다.
