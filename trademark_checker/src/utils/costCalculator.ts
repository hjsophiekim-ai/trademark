import type { FilingCostInput, FilingCostResult, FilingCostBreakdown } from '../types'

// ===== KIPO 공식 수수료 (2024년 기준, 전자출원) =====
// 출처: 특허청 수수료 규정
const FEES = {
  // 출원료 (전자출원)
  APPLICATION_BASE: 62_000,          // 1류 기본 출원료
  APPLICATION_PER_EXCESS_GOOD: 2_000, // 지정상품 6개 초과 시 1개당 추가

  // 등록료
  REGISTRATION_10Y: 211_000,         // 10년 일시납 (1류)
  REGISTRATION_5Y_FIRST: 106_000,    // 5년 전기 납부
  REGISTRATION_5Y_SECOND: 106_000,   // 5년 후기 납부

  // 종이출원 가산 (전자출원 아닐 경우 20% 추가)
  PAPER_SURCHARGE_RATE: 0.20,

  // 변리사 수임료 (기본, 1류 기준)
  ATTORNEY_BASE_PER_CLASS: 330_000,  // 1류당 기본 수임료
  ATTORNEY_DISCOUNT_ADDITIONAL: 0.9, // 추가 류 10% 할인

  // 소상공인/중소기업 감면 (출원료)
  SMALL_BUSINESS_DISCOUNT: 0.50,     // 소상공인: 50% 감면
  SME_DISCOUNT: 0.30,                // 중소기업: 30% 감면
} as const

export function calculateFilingCost(input: FilingCostInput): FilingCostResult {
  const breakdown: FilingCostBreakdown[] = []
  const notes: string[] = []

  // ── 1. 출원료 계산 ──
  let applicationFee = 0
  for (let i = 0; i < input.classes; i++) {
    const goodsCount = input.goodsPerClass[i] ?? 1
    let classFee = FEES.APPLICATION_BASE

    // 지정상품 6개 초과분 추가
    const excessGoods = Math.max(0, goodsCount - 6)
    classFee += excessGoods * FEES.APPLICATION_PER_EXCESS_GOOD

    applicationFee += classFee

    breakdown.push({
      label: `출원료 (제${i + 1}번째 류)`,
      amount: classFee,
      unit: '원',
      detail: goodsCount > 6
        ? `기본 ${FEES.APPLICATION_BASE.toLocaleString()}원 + 초과상품 ${excessGoods}개 × ${FEES.APPLICATION_PER_EXCESS_GOOD.toLocaleString()}원`
        : `기본 출원료 (지정상품 ${goodsCount}개)`,
    })
  }

  // 종이출원 가산
  if (!input.isOnline) {
    const surcharge = Math.ceil(applicationFee * FEES.PAPER_SURCHARGE_RATE)
    applicationFee += surcharge
    breakdown.push({
      label: '종이출원 가산금 (20%)',
      amount: surcharge,
      unit: '원',
      detail: '전자출원 시 면제',
    })
    notes.push('전자출원 이용 시 종이출원 가산금 (20%) 면제')
  }

  // 감면 적용
  let discountRate = 0
  let discountLabel = ''
  if (input.applicantType === '소상공인') {
    discountRate = FEES.SMALL_BUSINESS_DISCOUNT
    discountLabel = '소상공인 출원료 50% 감면'
  } else if (input.applicantType === '중소기업') {
    discountRate = FEES.SME_DISCOUNT
    discountLabel = '중소기업 출원료 30% 감면'
  }

  if (discountRate > 0) {
    const discount = Math.ceil(applicationFee * discountRate)
    applicationFee -= discount
    breakdown.push({
      label: discountLabel,
      amount: -discount,
      unit: '원',
      detail: '특허법 시행규칙에 따른 수수료 감면',
    })
    notes.push(`${discountLabel} 적용 (전자출원 + 요건 충족 시)`)
  }

  // ── 2. 등록료 계산 ──
  let registrationFee = 0
  if (input.registrationTerm === 10) {
    registrationFee = FEES.REGISTRATION_10Y * input.classes
    breakdown.push({
      label: `등록료 10년 일시납 (${input.classes}류)`,
      amount: registrationFee,
      unit: '원',
      detail: `${FEES.REGISTRATION_10Y.toLocaleString()}원 × ${input.classes}류`,
    })
  } else {
    const firstHalf = FEES.REGISTRATION_5Y_FIRST * input.classes
    const secondHalf = FEES.REGISTRATION_5Y_SECOND * input.classes
    registrationFee = firstHalf + secondHalf
    breakdown.push({
      label: `등록료 5년 전기납 (${input.classes}류)`,
      amount: firstHalf,
      unit: '원',
      detail: `${FEES.REGISTRATION_5Y_FIRST.toLocaleString()}원 × ${input.classes}류`,
    })
    breakdown.push({
      label: `등록료 5년 후기납 (${input.classes}류)`,
      amount: secondHalf,
      unit: '원',
      detail: `5년 후 납부 예정`,
    })
    notes.push('5년 분납 선택 시 후기납(5년 후)은 별도 납부 필요')
  }

  // ── 3. 변리사 수임료 ──
  let attorneyFee = 0
  if (input.includeAttorneyFee) {
    if (input.customAttorneyFeePerClass) {
      attorneyFee = input.customAttorneyFeePerClass * input.classes
      breakdown.push({
        label: `변리사 수임료 (${input.classes}류)`,
        amount: attorneyFee,
        unit: '원',
        detail: `${input.customAttorneyFeePerClass.toLocaleString()}원/류 × ${input.classes}류`,
      })
    } else {
      // 기본 수임료: 1류 기본, 추가 류는 10% 할인
      if (input.classes >= 1) {
        attorneyFee += FEES.ATTORNEY_BASE_PER_CLASS
      }
      for (let i = 1; i < input.classes; i++) {
        attorneyFee += Math.ceil(FEES.ATTORNEY_BASE_PER_CLASS * FEES.ATTORNEY_DISCOUNT_ADDITIONAL)
      }
      breakdown.push({
        label: `변리사 수임료 (${input.classes}류)`,
        amount: attorneyFee,
        unit: '원',
        detail: input.classes > 1
          ? `1류 ${FEES.ATTORNEY_BASE_PER_CLASS.toLocaleString()}원 + 추가 ${input.classes - 1}류 (10% 할인)`
          : `기본 수임료`,
      })
    }
    notes.push('변리사 수임료는 사무소별 상이할 수 있음')
  }

  const totalFee = applicationFee + registrationFee + attorneyFee
  notes.push('위 금액은 예상 비용이며, 실제 청구 금액과 다를 수 있습니다.')
  notes.push('부가세(VAT) 별도')

  return {
    applicationFee,
    registrationFee,
    attorneyFee,
    totalFee,
    breakdown,
    discountInfo: discountRate > 0 ? discountLabel : undefined,
    notes,
  }
}

// 기본 계산 (빠른 견적)
export function quickEstimate(classes: number, applicantType: string): number {
  const base = FEES.APPLICATION_BASE + FEES.REGISTRATION_10Y
  let total = base * classes
  if (applicantType === '소상공인') total *= (1 - FEES.SMALL_BUSINESS_DISCOUNT)
  else if (applicantType === '중소기업') total *= (1 - FEES.SME_DISCOUNT)
  return Math.ceil(total)
}

// 비용 포맷 유틸
export function formatKRW(amount: number): string {
  return amount.toLocaleString('ko-KR') + '원'
}
