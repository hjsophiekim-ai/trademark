// 키프리스 검색식 자동 생성 유틸
// 이미지 자료 (3-1. 등록가능성 검토 방법) 기반

// 유사 음소 변환 맵
const PHONEME_MAP: Record<string, string[]> = {
  // 모음 변형
  'oo': ['u', 'ou', 'ew'],
  'ee': ['i', 'y', 'ie', 'ea'],
  'a': ['ah', 'aa'],
  'o': ['oh', 'oo'],

  // 자음 변형
  'c': ['k', 'ck'],
  'k': ['c', 'ck'],
  'f': ['ph'],
  'ph': ['f'],
  's': ['z', 'c'],
  'z': ['s'],
  'ie': ['y', 'i'],
  'y': ['ie', 'i'],
  'or': ['ore', 'oar'],
  'er': ['or', 'ar', 're'],
}

// 영문 → 한글 음역 맵
const EN_TO_KO_MAP: Record<string, string> = {
  'a': '에이',
  'b': '비',
  'c': '씨',
  'd': '디',
  'e': '이',
  'f': '에프',
  'g': '지',
  'h': '에이치',
  'i': '아이',
  'j': '제이',
  'k': '케이',
  'l': '엘',
  'm': '엠',
  'n': '엔',
  'o': '오',
  'p': '피',
  'q': '큐',
  'r': '알',
  's': '에스',
  't': '티',
  'u': '유',
  'v': '브이',
  'w': '더블유',
  'x': '엑스',
  'y': '와이',
  'z': '지',
}

// 음소 유사 변형 생성
function generatePhonemeVariants(word: string): string[] {
  const variants: Set<string> = new Set([word])
  const lower = word.toLowerCase()

  // 기본 변형 (대소문자)
  variants.add(lower)
  variants.add(word.toUpperCase())

  // 모음 교체 규칙
  const vowelSubs: [string, string][] = [
    ['oo', 'u'], ['u', 'oo'],
    ['ee', 'i'], ['i', 'ee'],
    ['ie', 'y'], ['y', 'ie'],
    ['oo', 'o'], ['o', 'oo'],
    ['ie', 'iy'], ['y', 'ie'],
    ['ky', 'ki'], ['ki', 'ky'],
    ['kie', 'ky'],
    ['ie', 'ie'],
  ]

  for (const [from, to] of vowelSubs) {
    if (lower.includes(from)) {
      variants.add(lower.replace(new RegExp(from, 'g'), to))
    }
  }

  // 초성 변형 (p↔f, c↔k, s↔z)
  const consonantSubs: [string, string][] = [
    ['ph', 'f'], ['f', 'ph'],
    ['c', 'k'], ['k', 'c'],
    ['s', 'z'], ['z', 's'],
  ]
  for (const [from, to] of consonantSubs) {
    if (lower.startsWith(from)) {
      variants.add(lower.replace(from, to))
    }
  }

  return Array.from(variants).filter(v => v.length > 0)
}

// 와일드카드 검색식 생성 (예: pook? 형태)
function generateWildcards(word: string): string[] {
  const wildcards: string[] = []
  if (word.length >= 4) {
    wildcards.push(word.slice(0, Math.ceil(word.length * 0.7)) + '?')
    wildcards.push(word.slice(0, 3) + '?')
  }
  return wildcards
}

// 한글 표기 생성 (단순 음역)
function generateKoreanTranslit(word: string): string {
  // 간단한 규칙 기반 음역 (실제로는 더 정교한 로직 필요)
  const commonMap: Record<string, string> = {
    'STYLE': '스타일',
    'FASHION': '패션',
    'BRAND': '브랜드',
    'DESIGN': '디자인',
    'BEAUTY': '뷰티',
    'LIFE': '라이프',
    'TECH': '테크',
    'LOVE': '러브',
    'STAR': '스타',
    'PLUS': '플러스',
    'PRO': '프로',
    'MAX': '맥스',
    'KING': '킹',
    'QUEEN': '퀸',
    'SHOP': '샵',
    'MARKET': '마켓',
    'WORLD': '월드',
    'GLOBAL': '글로벌',
    'CREATIVE': '크리에이티브',
    'SMART': '스마트',
    'BLUE': '블루',
    'RED': '레드',
    'GREEN': '그린',
    'GOLD': '골드',
    'SILVER': '실버',
  }

  const upper = word.toUpperCase()
  return commonMap[upper] || word
}

// 메인 검색식 생성 함수
export function generateSearchFormula(
  trademarkName: string,
  similarGroupCodes: string[],
  options: { includeWildcard?: boolean; includeKorean?: boolean } = {}
): string {
  const { includeWildcard = true, includeKorean = true } = options

  // 상표명에서 단어 추출
  const words = trademarkName.trim().split(/[\s\-_]+/).filter(w => w.length > 0)

  const allVariants: string[] = []

  for (const word of words) {
    const variants = generatePhonemeVariants(word)
    allVariants.push(...variants)

    if (includeWildcard) {
      allVariants.push(...generateWildcards(word.toLowerCase()))
    }

    if (includeKorean) {
      const ko = generateKoreanTranslit(word)
      if (ko !== word) allVariants.push(ko)
    }
  }

  // 중복 제거 및 정렬
  const uniqueVariants = Array.from(new Set(allVariants)).filter(v => v.length > 0)

  // 키프리스 검색식 포맷: TN=[variant1+variant2+...] SC=CODE1+CODE2
  const tnPart = `TN=[${uniqueVariants.join('+')}]`
  const scPart = similarGroupCodes.length > 0
    ? ` SC=${similarGroupCodes.join('+')}`
    : ''

  return tnPart + scPart
}

// 검색식 분리 분석
export function parseSearchFormula(formula: string): {
  trademarkVariants: string[]
  similarGroupCodes: string[]
} {
  const tnMatch = formula.match(/TN=\[([^\]]+)\]/)
  const scMatch = formula.match(/SC=([^\s]+)/)

  return {
    trademarkVariants: tnMatch ? tnMatch[1].split('+') : [],
    similarGroupCodes: scMatch ? scMatch[1].split('+') : [],
  }
}
