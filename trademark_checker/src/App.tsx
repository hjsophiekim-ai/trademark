import { useEffect, useMemo, useState } from 'react'

export type Page =
  | 'dashboard'
  | 'filings'
  | 'clients'
  | 'similarity'
  | 'similar-codes'
  | 'cost-calculator'
  | 'settings'

type Kind = 'goods' | 'services'

type CatalogSubgroup = {
  subgroup_id: string
  subgroup_label: string
  nice_classes: number[]
  similarity_codes: string[]
  examples: string[]
}

type CatalogGroup = {
  kind: Kind
  group_id: string
  group_label: string
  group_hint?: string
  class_nos: number[]
  classes: Array<{ no: number; name: string }>
  subgroups: CatalogSubgroup[]
}

type CatalogResponse = {
  ok: boolean
  kinds: Array<{ kind: Kind; label: string }>
  groups: CatalogGroup[]
}

type AnalyzeRequest = {
  trademark_name: string
  trademark_type: string
  is_coined: boolean
  selected_kind: Kind | null
  selected_group_id: string
  selected_subgroup_ids: string[]
}

type PriorItemSummary = {
  trademarkName: string
  applicationNumber: string
  registrationNumber: string
  registerStatus: string
  survival_label?: string
  counts_toward_final_score?: boolean
  mark_similarity?: number
  product_similarity_score?: number
  confusion_score?: number
  overlap_type?: string
  overlap_basis?: string
  overlap_codes?: string[]
  strongest_matching_prior_codes?: string[]
  strongest_matching_prior_item?: string
  product_bucket?: string
}

type AnalyzeResponse = {
  ok: boolean
  error?: string
  result?: {
    score: number
    final_registration_probability: number
    stage1: {
      summary: string
      risk_level: string
      probability_cap: number
      refusal_bases: string[]
      acquired_distinctiveness_needed: boolean
    }
    stage2: {
      strongest_overlap_type: string
      strongest_matching_prior_item: string
      strongest_matching_prior_codes: string[]
      scope_counts: {
        exact_scope_candidates: number
        same_class_candidates: number
        related_market_candidates: number
        irrelevant_candidates: number
      }
      live_blockers: PriorItemSummary[]
      historical_references: PriorItemSummary[]
      search_failed: boolean
      search_error_msg: string
    }
  }
}

const API_BASE = (import.meta as any).env?.VITE_TRADEMARK_API_BASE || 'http://127.0.0.1:8001'

function clampInt(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, Math.floor(value)))
}

function formatPercent(value: number) {
  return `${clampInt(value, 0, 100)}%`
}

function classLabel(no: number, name?: string) {
  return name ? `${no}류 · ${name}` : `${no}류`
}

function Stepper({ step }: { step: number }) {
  const items = [
    { n: 1, label: '상표명' },
    { n: 2, label: '상품 선택' },
    { n: 3, label: '상품군' },
    { n: 4, label: '결과' },
  ]
  return (
    <div className="flex items-center gap-2 text-sm">
      {items.map((item, idx) => (
        <div key={item.n} className="flex items-center gap-2">
          <div className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold ${
            step >= item.n ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
          }`}>
            {item.n}
          </div>
          <div className={`${step === item.n ? 'text-gray-900 font-semibold' : 'text-gray-500'}`}>
            {item.label}
          </div>
          {idx < items.length - 1 && <div className="w-6 h-px bg-gray-200" />}
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [step, setStep] = useState(1)
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null)
  const [catalogError, setCatalogError] = useState<string>('')

  const [trademarkName, setTrademarkName] = useState('')
  const [trademarkType, setTrademarkType] = useState('word')
  const [isCoined, setIsCoined] = useState(false)
  const [selectedKind, setSelectedKind] = useState<Kind | null>(null)
  const [groupQuery, setGroupQuery] = useState('')
  const [selectedGroupId, setSelectedGroupId] = useState('')
  const [subgroupQuery, setSubgroupQuery] = useState('')
  const [selectedSubgroupIds, setSelectedSubgroupIds] = useState<string[]>([])

  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState<string>('')
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        setCatalogError('')
        const resp = await fetch(`${API_BASE}/api/catalog`)
        const json = (await resp.json()) as CatalogResponse
        if (!resp.ok || !json?.ok) {
          throw new Error('catalog fetch failed')
        }
        if (!cancelled) setCatalog(json)
      } catch {
        if (!cancelled) setCatalogError(`로컬 분석 서버에 연결할 수 없습니다. (${API_BASE})`)
      }
    }
    run()
    return () => { cancelled = true }
  }, [])

  const classNameMap = useMemo(() => {
    const map = new Map<number, string>()
    if (!catalog) return map
    for (const group of catalog.groups) {
      for (const cls of group.classes || []) {
        if (!cls?.no) continue
        if (!map.has(cls.no)) map.set(cls.no, cls.name || '')
      }
    }
    return map
  }, [catalog])

  const groupOptions = useMemo(() => {
    if (!catalog) return []
    const q = groupQuery.trim().toLowerCase()
    return catalog.groups
      .filter(g => !selectedKind || g.kind === selectedKind)
      .filter(g => !q || g.group_label.toLowerCase().includes(q))
  }, [catalog, selectedKind, groupQuery])

  const selectedGroup = useMemo(() => {
    if (!catalog || !selectedGroupId) return null
    return catalog.groups.find(g => g.group_id === selectedGroupId) || null
  }, [catalog, selectedGroupId])

  const subgroupOptions = useMemo(() => {
    const base = selectedGroup?.subgroups || []
    const q = subgroupQuery.trim().toLowerCase()
    if (!q) return base
    return base.filter(sg => sg.subgroup_label.toLowerCase().includes(q) || (sg.examples || []).some(ex => ex.toLowerCase().includes(q)))
  }, [selectedGroup, subgroupQuery])

  const toggleSubgroup = (id: string) => {
    setSelectedSubgroupIds(prev => prev.includes(id) ? prev.filter(v => v !== id) : [...prev, id])
  }

  const canGoNext = () => {
    if (step === 1) return trademarkName.trim().length > 0
    if (step === 2) return !!selectedKind && selectedGroupId.length > 0
    if (step === 3) return selectedSubgroupIds.length > 0
    return false
  }

  const next = () => {
    if (!canGoNext()) return
    setStep(s => Math.min(4, s + 1))
  }

  const back = () => setStep(s => Math.max(1, s - 1))

  const reset = () => {
    setStep(1)
    setAnalysis(null)
    setAnalysisError('')
    setIsAnalyzing(false)
    setTrademarkName('')
    setTrademarkType('word')
    setIsCoined(false)
    setSelectedKind(null)
    setGroupQuery('')
    setSelectedGroupId('')
    setSubgroupQuery('')
    setSelectedSubgroupIds([])
  }

  const runAnalyze = async () => {
    setIsAnalyzing(true)
    setAnalysisError('')
    setAnalysis(null)
    try {
      const payload: AnalyzeRequest = {
        trademark_name: trademarkName.trim(),
        trademark_type: trademarkType,
        is_coined: isCoined,
        selected_kind: selectedKind,
        selected_group_id: selectedGroupId,
        selected_subgroup_ids: selectedSubgroupIds,
      }
      const resp = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = (await resp.json()) as AnalyzeResponse
      if (!resp.ok || !json?.ok || !json.result) {
        throw new Error(json?.error || 'analyze failed')
      }
      setAnalysis(json)
    } catch (err: any) {
      setAnalysisError(String(err?.message || err || '분석에 실패했습니다.'))
    } finally {
      setIsAnalyzing(false)
    }
  }

  useEffect(() => {
    if (step === 4 && !analysis && !isAnalyzing) runAnalyze()
  }, [step])

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 py-10">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200">
          <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between">
            <div>
              <div className="text-xl font-bold text-slate-900">상표 등록 가능성 간편 검토</div>
              <div className="text-sm text-slate-500 mt-1">Step-by-Step로 입력하면 Stage 1/Stage 2 결과를 리포트로 보여줍니다.</div>
            </div>
            <div className="hidden sm:block">
              <Stepper step={step} />
            </div>
          </div>

          {catalogError && (
            <div className="px-6 py-4 border-b border-slate-200 bg-amber-50 text-amber-900 text-sm">
              {catalogError}
            </div>
          )}

          <div className="p-6">
            {step === 1 && (
              <div className="space-y-4">
                <div className="text-lg font-semibold text-slate-900">1단계: 어떤 상표를 등록하시겠어요?</div>
                <div>
                  <label className="text-sm font-medium text-slate-700">상표명</label>
                  <input
                    value={trademarkName}
                    onChange={e => setTrademarkName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="예: G트리"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-slate-700">상표 유형</label>
                    <select
                      value={trademarkType}
                      onChange={e => setTrademarkType(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 bg-white"
                    >
                      <option value="word">문자상표</option>
                      <option value="logo">도형/로고</option>
                      <option value="mixed">복합</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={isCoined}
                        onChange={e => setIsCoined(e.target.checked)}
                        className="h-4 w-4"
                      />
                      신조어(조어)입니다
                    </label>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-2">
                  <div className="text-xs text-slate-500">로컬 분석 서버: {API_BASE}</div>
                  <div className="flex gap-2">
                    <button
                      onClick={next}
                      disabled={!canGoNext()}
                      className={`px-4 py-2 rounded-lg text-sm font-semibold ${canGoNext() ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-400'}`}
                    >
                      다음
                    </button>
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="text-lg font-semibold text-slate-900">2단계: 상품/서비스를 고르고, 해당 상품을 선택해 주세요</div>
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium text-slate-700">구분</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setSelectedKind('goods'); setSelectedGroupId(''); setSelectedSubgroupIds([]) }}
                      className={`px-3 py-1.5 rounded-lg text-sm ${selectedKind === 'goods' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}
                    >
                      상품
                    </button>
                    <button
                      onClick={() => { setSelectedKind('services'); setSelectedGroupId(''); setSelectedSubgroupIds([]) }}
                      className={`px-3 py-1.5 rounded-lg text-sm ${selectedKind === 'services' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700'}`}
                    >
                      서비스
                    </button>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700">검색</label>
                  <input
                    value={groupQuery}
                    onChange={e => setGroupQuery(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                    placeholder="예: 금융, 부동산, 소프트웨어"
                  />
                </div>
                {selectedKind === null ? (
                  <div className="p-4 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-700">
                    먼저 “상품” 또는 “서비스”를 선택해 주세요.
                  </div>
                ) : (
                  <div className="max-h-[460px] overflow-auto border border-slate-200 rounded-xl divide-y">
                    {groupOptions.length === 0 ? (
                      <div className="p-4 text-sm text-slate-500">선택 가능한 항목이 없습니다.</div>
                    ) : (
                      groupOptions.map(group => {
                        const isSelected = group.group_id === selectedGroupId
                        return (
                          <button
                            key={group.group_id}
                            onClick={() => { setSelectedGroupId(group.group_id); setSelectedSubgroupIds([]) }}
                            className={`w-full text-left p-4 ${isSelected ? 'bg-blue-50' : 'bg-white'} hover:bg-slate-50`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <div className="font-semibold text-slate-900">{group.group_label}</div>
                                {group.group_hint && <div className="text-xs text-slate-600 mt-1">{group.group_hint}</div>}
                              </div>
                              <div className={`text-xs font-semibold px-2 py-1 rounded-lg ${isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}>
                                {group.kind === 'goods' ? '상품' : '서비스'}
                              </div>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-1">
                              {(group.classes || []).map(cls => (
                                <span key={cls.no} className="text-xs px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-700">
                                  {classLabel(cls.no, cls.name)}
                                </span>
                              ))}
                            </div>
                          </button>
                        )
                      })
                    )}
                  </div>
                )}
                <div className="flex items-center justify-between pt-2">
                  <button onClick={back} className="px-4 py-2 rounded-lg text-sm font-semibold bg-slate-100 text-slate-700">
                    이전
                  </button>
                  <button
                    onClick={next}
                    disabled={!canGoNext()}
                    className={`px-4 py-2 rounded-lg text-sm font-semibold ${canGoNext() ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-400'}`}
                  >
                    다음
                  </button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <div className="text-lg font-semibold text-slate-900">3단계: 상품군(세부)을 선택해 주세요</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-slate-700">검색</label>
                    <input
                      value={subgroupQuery}
                      onChange={e => setSubgroupQuery(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                      placeholder="예: 예금, 대출, 부동산, 보험"
                    />
                  </div>
                  <div className="flex items-end text-sm text-slate-600">
                    선택됨: <span className="ml-1 font-semibold text-slate-900">{selectedSubgroupIds.length}</span>개
                  </div>
                </div>
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                    <div className="text-sm font-semibold text-slate-900">{selectedGroup?.group_label || '선택한 상품'}</div>
                    {!!selectedGroup?.classes?.length && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {selectedGroup.classes.map(cls => (
                          <span key={cls.no} className="text-xs px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-700">
                            {classLabel(cls.no, cls.name)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="max-h-[420px] overflow-auto divide-y">
                    {subgroupOptions.length === 0 ? (
                      <div className="p-4 text-sm text-slate-500">선택 가능한 상품군이 없습니다.</div>
                    ) : (
                      subgroupOptions.map(sg => (
                        <label key={sg.subgroup_id} className="flex items-start gap-3 p-4 hover:bg-slate-50">
                          <input
                            type="checkbox"
                            checked={selectedSubgroupIds.includes(sg.subgroup_id)}
                            onChange={() => toggleSubgroup(sg.subgroup_id)}
                            className="mt-1 h-4 w-4"
                          />
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-slate-900">{sg.subgroup_label}</div>
                            <div className="text-xs text-slate-600 mt-1">
                              {sg.nice_classes?.length
                                ? `상품류: ${sg.nice_classes.map(no => classLabel(no, classNameMap.get(no))).join(', ')}`
                                : ''}
                            </div>
                            {(sg.examples || []).length > 0 && (
                              <div className="text-xs text-slate-500 mt-1">
                                예시: {(sg.examples || []).join(', ')}
                              </div>
                            )}
                          </div>
                        </label>
                      ))
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between pt-2">
                  <button onClick={back} className="px-4 py-2 rounded-lg text-sm font-semibold bg-slate-100 text-slate-700">
                    이전
                  </button>
                  <button
                    onClick={() => setStep(4)}
                    disabled={!canGoNext()}
                    className={`px-4 py-2 rounded-lg text-sm font-semibold ${canGoNext() ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-400'}`}
                  >
                    결과 보기
                  </button>
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-lg font-semibold text-slate-900">결과</div>
                    <div className="text-sm text-slate-600 mt-1">
                      {trademarkName} · {selectedGroup?.group_label || ''}
                    </div>
                  </div>
                  <button onClick={reset} className="px-4 py-2 rounded-lg text-sm font-semibold bg-slate-100 text-slate-700">
                    다시 하기
                  </button>
                </div>

                {isAnalyzing && (
                  <div className="p-4 border border-slate-200 rounded-xl bg-slate-50 text-sm text-slate-700">
                    분석 중입니다. 잠시만 기다려주세요…
                  </div>
                )}

                {analysisError && (
                  <div className="p-4 border border-rose-200 rounded-xl bg-rose-50 text-sm text-rose-900">
                    {analysisError}
                  </div>
                )}

                {analysis?.result && (
                  <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="p-4 border border-slate-200 rounded-xl">
                        <div className="text-xs font-semibold text-slate-500">등록 가능성(%)</div>
                        <div className="text-3xl font-extrabold text-slate-900 mt-2">
                          {formatPercent(analysis.result.final_registration_probability)}
                        </div>
                        <div className="text-xs text-slate-500 mt-2">
                          Stage 1 상한 {analysis.result.stage1.probability_cap}% 적용
                        </div>
                      </div>
                      <div className="p-4 border border-slate-200 rounded-xl">
                        <div className="text-xs font-semibold text-slate-500">선행상표(실질 장애물)</div>
                        <div className="text-3xl font-extrabold text-slate-900 mt-2">
                          {analysis.result.stage2.live_blockers.length}건
                        </div>
                        {analysis.result.stage2.search_failed && (
                          <div className="text-xs text-amber-700 mt-2">
                            검색 오류: {analysis.result.stage2.search_error_msg || '확인 필요'}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="p-5 border border-slate-200 rounded-xl">
                      <div className="text-sm font-bold text-slate-900">Stage 1: 식별력(절대적 거절 사유) 점검</div>
                      <div className="mt-2 text-sm text-slate-800">{analysis.result.stage1.summary}</div>
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                        <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
                          <div className="text-slate-500">리스크</div>
                          <div className="font-semibold text-slate-900">{analysis.result.stage1.risk_level}</div>
                        </div>
                        <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
                          <div className="text-slate-500">상한</div>
                          <div className="font-semibold text-slate-900">{analysis.result.stage1.probability_cap}%</div>
                        </div>
                        <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
                          <div className="text-slate-500">입증 필요</div>
                          <div className="font-semibold text-slate-900">
                            {analysis.result.stage1.acquired_distinctiveness_needed ? '예' : '아니오'}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="p-5 border border-slate-200 rounded-xl">
                      <div className="text-sm font-bold text-slate-900">Stage 2: 선행상표 유사군코드(SC) 정밀 충돌</div>
                      <div className="mt-2 text-xs text-slate-600">
                        동일코드 {analysis.result.stage2.scope_counts.exact_scope_candidates}건 · 동일류 보조검토 {analysis.result.stage2.scope_counts.same_class_candidates}건 · 상품-서비스 예외 {analysis.result.stage2.scope_counts.related_market_candidates}건
                      </div>
                      <div className="mt-4">
                        {analysis.result.stage2.live_blockers.length === 0 ? (
                          <div className="text-sm text-slate-600">실질 장애물로 분류된 선행상표가 없습니다.</div>
                        ) : (
                          <div className="space-y-3">
                            {analysis.result.stage2.live_blockers.slice(0, 6).map((p, idx) => (
                              <div key={`${p.applicationNumber}-${idx}`} className="border border-slate-200 rounded-xl p-4">
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <div className="font-semibold text-slate-900">{p.trademarkName || '-'}</div>
                                    <div className="text-xs text-slate-500 mt-0.5">
                                      상태: {p.registerStatus || '-'} · 출원번호: {p.applicationNumber || '-'}
                                    </div>
                                  </div>
                                  <div className="text-right">
                                    <div className="text-xs text-slate-500">혼동 위험</div>
                                    <div className="text-lg font-bold text-slate-900">{formatPercent(p.confusion_score || 0)}</div>
                                  </div>
                                </div>
                                <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                                  <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
                                    <div className="text-slate-500">표장 유사</div>
                                    <div className="font-semibold text-slate-900">{formatPercent(p.mark_similarity || 0)}</div>
                                  </div>
                                  <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
                                    <div className="text-slate-500">상품 유사</div>
                                    <div className="font-semibold text-slate-900">{formatPercent(p.product_similarity_score || 0)}</div>
                                  </div>
                                  <div className="px-3 py-2 rounded-lg bg-slate-50 border border-slate-200">
                                    <div className="text-slate-500">충돌 유형</div>
                                    <div className="font-semibold text-slate-900">{p.overlap_type || p.product_bucket || '-'}</div>
                                  </div>
                                </div>
                                {Array.isArray(p.strongest_matching_prior_codes) && p.strongest_matching_prior_codes.length > 0 && (
                                  <div className="mt-3 text-xs text-slate-700">
                                    <span className="text-slate-500">핵심 충돌 코드:</span>{' '}
                                    <span className="font-semibold">{p.strongest_matching_prior_codes.join(', ')}</span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}

                <div className="flex items-center justify-between">
                  <button onClick={back} className="px-4 py-2 rounded-lg text-sm font-semibold bg-slate-100 text-slate-700">
                    이전
                  </button>
                  <button onClick={runAnalyze} className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white">
                    다시 분석
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
