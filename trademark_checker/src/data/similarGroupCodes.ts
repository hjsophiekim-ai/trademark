import type { SimilarGroupCode } from '../types'

// 주요 유사군 코드 (KIPO 기준, 상표 유사군 코드표)
// 판매업 연계 코드 포함
export const SIMILAR_GROUP_CODES: SimilarGroupCode[] = [
  // ===== 제25류 (의류, 신발, 모자) =====
  { code: 'G270101', class: 25, name: '의류(일반)', description: '일반 의류', examples: ['티셔츠', '바지', '재킷', '코트'] },
  { code: 'G430301', class: 25, name: '내의류', description: '속옷 등 내의', examples: ['속옷', '팬티', '브라'] },
  { code: 'G450101', class: 25, name: '신발', description: '일반 신발', examples: ['운동화', '구두', '슬리퍼'] },
  { code: 'G450102', class: 25, name: '특수신발', description: '특수 목적 신발', examples: ['등산화', '스키화'] },
  { code: 'G4502', class: 25, name: '모자류', description: '모자', examples: ['야구모자', '비니', '햇'] },
  { code: 'G4503', class: 25, name: '양말류', description: '양말, 스타킹', examples: ['양말', '스타킹', '타이즈'] },
  { code: 'G450401', class: 25, name: '장갑류', description: '의류용 장갑', examples: ['면장갑', '가죽장갑'] },
  { code: 'G4513', class: 25, name: '수영복', description: '수영복, 수영모', examples: ['수영복', '수영모자', '래시가드'] },
  { code: 'G450501', class: 25, name: '유아복', description: '유아 의류', examples: ['배내옷', '유아복'] },

  // ===== 제18류 (가죽, 가방) =====
  { code: 'G2501', class: 18, name: '가방류(일반)', description: '일반 가방', examples: ['핸드백', '백팩', '지갑'] },
  { code: 'G2703', class: 18, name: '여행용 가방', description: '여행 가방', examples: ['캐리어', '여행가방', '보스턴백'] },

  // ===== 제14류 (귀금속, 보석) =====
  { code: 'G3002', class: 14, name: '귀금속류', description: '귀금속 및 그 합금', examples: ['금', '은', '백금'] },
  { code: 'G3501', class: 14, name: '보석류', description: '보석, 귀석', examples: ['다이아몬드', '루비', '에메랄드'] },
  { code: 'G4509', class: 14, name: '반지', description: '반지류', examples: ['결혼반지', '약혼반지', '패션링'] },
  { code: 'G4401', class: 14, name: '목걸이', description: '목걸이류', examples: ['체인 목걸이', '펜던트'] },
  { code: 'G4510', class: 14, name: '귀걸이', description: '귀걸이류', examples: ['귀걸이', '이어링'] },
  { code: 'G3601', class: 14, name: '시계', description: '시계류', examples: ['손목시계', '회중시계'] },

  // ===== 소매업 유사군 (판매업) =====
  { code: 'S2027', class: 35, name: '의류 소매업', description: '의류, 신발 등 소매', examples: ['의류 소매점', '패션 쇼핑몰'] },
  { code: 'S2043', class: 35, name: '의류 도매업', description: '의류 도매', examples: ['의류 도매상'] },
  { code: 'S2045', class: 35, name: '속옷 소매업', description: '속옷 소매', examples: ['속옷 가게'] },
  { code: 'S2025', class: 35, name: '가방 소매업', description: '가방, 지갑 소매', examples: ['가방 가게'] },
  { code: 'S2030', class: 35, name: '귀금속 소매업', description: '귀금속, 보석 소매', examples: ['귀금속 상점'] },
  { code: 'S2035', class: 35, name: '시계 소매업', description: '시계 소매', examples: ['시계 판매점'] },
  { code: 'S2044', class: 35, name: '귀금속 도매업', description: '귀금속 도매', examples: ['귀금속 도매상'] },
  { code: 'S2012', class: 35, name: '온라인 쇼핑몰 운영업', description: '온라인 쇼핑몰', examples: ['온라인 쇼핑몰'] },

  // ===== 제3류 (화장품, 비누) =====
  { code: 'G0301', class: 3, name: '화장품류', description: '화장품', examples: ['로션', '크림', '파운데이션'] },
  { code: 'G0302', class: 3, name: '향수류', description: '향수', examples: ['향수', '오드퍼퓸'] },
  { code: 'G0303', class: 3, name: '두발 용품', description: '샴푸, 린스', examples: ['샴푸', '컨디셔너', '헤어팩'] },

  // ===== 제43류 (음식점, 숙박) =====
  { code: 'S4301', class: 43, name: '음식점업', description: '음식점, 카페', examples: ['음식점', '카페', '레스토랑'] },
  { code: 'S4302', class: 43, name: '숙박업', description: '호텔, 모텔', examples: ['호텔', '게스트하우스'] },

  // ===== 제9류 (전자, 소프트웨어) =====
  { code: 'G0901', class: 9, name: '컴퓨터', description: '컴퓨터 하드웨어', examples: ['컴퓨터', '노트북', '태블릿'] },
  { code: 'G0902', class: 9, name: '소프트웨어', description: '컴퓨터 소프트웨어', examples: ['앱', '프로그램', '게임'] },
  { code: 'G0903', class: 9, name: '스마트폰', description: '스마트폰, 휴대전화', examples: ['스마트폰', '휴대폰'] },

  // ===== 제41류 (교육, 엔터테인먼트) =====
  { code: 'S4101', class: 41, name: '교육업', description: '교육, 학원', examples: ['학원', '교육서비스'] },
  { code: 'S4102', class: 41, name: '엔터테인먼트업', description: '공연, 이벤트', examples: ['콘서트', '공연'] },

  // ===== 제42류 (IT 서비스) =====
  { code: 'S4201', class: 42, name: 'IT 서비스업', description: '소프트웨어 개발, SaaS', examples: ['소프트웨어 개발', 'IT 컨설팅'] },
  { code: 'S4202', class: 42, name: '플랫폼 서비스업', description: '온라인 플랫폼', examples: ['SNS 플랫폼', '앱 서비스'] },

  // ===== 제44류 (의료, 미용) =====
  { code: 'S4401', class: 44, name: '의료업', description: '의료, 병원', examples: ['병원', '의원', '치과'] },
  { code: 'S4402', class: 44, name: '미용업', description: '미용, 헤어', examples: ['미용실', '네일샵', '피부관리'] },
]

// 류별 코드 매핑
export const CODES_BY_CLASS: Record<number, SimilarGroupCode[]> = {}
SIMILAR_GROUP_CODES.forEach(code => {
  if (!CODES_BY_CLASS[code.class]) CODES_BY_CLASS[code.class] = []
  CODES_BY_CLASS[code.class].push(code)
})

// 판매업 연계 코드 (상품류 → 소매업 서비스류)
export const RETAIL_SERVICE_MAP: Record<string, string[]> = {
  'G270101': ['S2027'],           // 의류 → 의류 소매업
  'G430301': ['S2045'],           // 내의류 → 속옷 소매업
  'G450101': ['S2027'],           // 신발 → 의류(신발) 소매업
  'G4502': ['S2027'],             // 모자류 → 의류 소매업
  'G4503': ['S2027', 'S2045'],    // 양말류 → 의류/속옷 소매업
  'G2501': ['S2025'],             // 가방류 → 가방 소매업
  'G3501': ['S2030'],             // 보석류 → 귀금속 소매업
  'G4509': ['S2030'],             // 반지 → 귀금속/반지 소매업
  'G3601': ['S2035'],             // 시계 → 시계 소매업
}

// 류 이름 매핑
export const CLASS_NAMES: Record<number, string> = {
  1: '화학',
  2: '도료·안료',
  3: '세제·화장품',
  4: '산업용 오일·연료',
  5: '의약품',
  6: '금속재료',
  7: '기계·공구',
  8: '수동용 공구',
  9: '전기·전자제품',
  10: '의료기기',
  11: '냉난방기기',
  12: '수송기계',
  13: '화기·폭발물',
  14: '귀금속·보석·시계',
  15: '악기',
  16: '종이·인쇄물',
  17: '고무·플라스틱',
  18: '가죽·가방',
  19: '건축재료',
  20: '가구',
  21: '주방용품',
  22: '로프·범포·천막',
  23: '실·원사',
  24: '섬유·직물',
  25: '의류·신발·모자',
  26: '리본·레이스·바느질용품',
  27: '카펫·매트',
  28: '완구·스포츠용품',
  29: '식육·유제품·가공식품',
  30: '빵·과자·음료',
  31: '농수산물·식물',
  32: '맥주·음료',
  33: '주류',
  34: '담배',
  35: '광고·판매업',
  36: '금융·보험업',
  37: '건설·수리업',
  38: '통신업',
  39: '운수·여행업',
  40: '재료처리·가공업',
  41: '교육·엔터테인먼트업',
  42: 'IT·과학기술업',
  43: '음식점·숙박업',
  44: '의료·미용업',
  45: '법률·보안업',
}
