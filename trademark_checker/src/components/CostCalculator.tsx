import { useState, useMemo } from 'react'
import { Calculator, Info, ChevronDown, ChevronUp, FileDown } from 'lucide-react'
import type { TrademarkFiling, FilingCostInput, ApplicantType } from '../types'
import { calculateFilingCost, formatKRW } from '../utils/costCalculator'
import { CLASS_NAMES } from '../data/similarGroupCodes'
import { loadSettings } from '../utils/storage'

interface Props {
  filings: TrademarkFiling[]
  onUpdateFiling: (filing: TrademarkFiling) => void
}

function getDefaultInput(): FilingCostInput {
  const settings = loadSettings()

  return {
  applicantType: '개인',
  classes: 1,
  goodsPerClass: [3],
  registrationTerm: 10,
  isOnline: true,
  includeAttorneyFee: true,
  customAttorneyFeePerClass:
    settings.defaultAttorneyFeePerClass === 330_000 ? 0 : settings.defaultAttorneyFeePerClass,
  }
}

export default function CostCalculator({ filings, onUpdateFiling }: Props) {
  const [input, setInput] = useState<FilingCostInput>(() => getDefaultInput())
  const [showBreakdown, setShowBreakdown] = useState(false)
  const [selectedFilingId, setSelectedFilingId] = useState<string>('')

  const result = useMemo(() => calculateFilingCost(input), [input])

  const handleClassChange = (n: number) => {
    const newGoods = Array(n).fill(0).map((_, i) => input.goodsPerClass[i] ?? 3)
    setInput(prev => ({ ...prev, classes: n, goodsPerClass: newGoods }))
  }

  const handleGoodsChange = (index: number, value: number) => {
    const newGoods = [...input.goodsPerClass]
    newGoods[index] = value
    setInput(prev => ({ ...prev, goodsPerClass: newGoods }))
  }

  const handleSaveToFiling = () => {
    if (!selectedFilingId) return
    const filing = filings.find(f => f.id === selectedFilingId)
    if (!filing) return
    onUpdateFiling({ ...filing, costInfo: result })
    alert(`"${filing.trademarkName}" 출원 건에 비용 정보가 저장되었습니다.`)
  }

  const handleExport = () => {
    const lines = [
      '=== 상표 출원 비용 계산서 ===',
      `계산일: ${new Date().toLocaleDateString('ko-KR')}`,
      '',
      `[입력 조건]`,
      `출원인 유형: ${input.applicantType}`,
      `출원 류 수: ${input.classes}류`,
      `등록료 납부: ${input.registrationTerm}년`,
      `전자출원: ${input.isOnline ? '예' : '아니오'}`,
      `변리사 수임료 포함: ${input.includeAttorneyFee ? '예' : '아니오'}`,
      '',
      '[비용 내역]',
      ...result.breakdown.map(b => `${b.label}: ${formatKRW(b.amount)}`),
      '',
      `[합계] ${formatKRW(result.totalFee)}`,
      '',
      '[주의사항]',
      ...result.notes,
    ]
    const content = lines.join('\n')
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `비용계산서_${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Calculator size={22} className="text-blue-600" />
            출원 비용 자동 계산
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            KIPO 공식 수수료 기준 (2024년) · 전자출원 기준
          </p>
        </div>
        <button onClick={handleExport} className="btn-secondary flex items-center gap-1.5">
          <FileDown size={14} /> 내보내기
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 입력 패널 */}
        <div className="card p-5 space-y-5">
          <h2 className="font-semibold text-gray-900">출원 조건 입력</h2>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">출원인 유형</label>
            <div className="grid grid-cols-3 gap-2">
              {(['개인', '소상공인', '중소기업', '법인', '대기업'] as ApplicantType[]).map(type => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setInput(prev => ({ ...prev, applicantType: type }))}
                  className={`py-2 rounded-lg text-xs font-medium border transition-colors ${
                    input.applicantType === type
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
            {(input.applicantType === '소상공인' || input.applicantType === '중소기업') && (
              <div className="mt-2 text-xs text-green-700 bg-green-50 rounded px-2 py-1 flex items-center gap-1">
                <Info size={11} />
                {input.applicantType === '소상공인' ? '출원료 50% 감면 적용' : '출원료 30% 감면 적용'}
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              출원 류 수: <span className="text-blue-600 font-semibold">{input.classes}류</span>
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={input.classes}
              onChange={e => handleClassChange(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>1류</span><span>10류</span>
            </div>
          </div>

          {/* 류별 지정상품 수 */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-2">
              류별 지정상품 수
              <span className="text-gray-400 ml-1">(6개 초과 시 1개당 2,000원 추가)</span>
            </label>
            <div className="space-y-2">
              {Array.from({ length: input.classes }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-16 shrink-0">
                    제{i + 1}번째 류{input.classes <= 3 ? ` (${CLASS_NAMES[25] ?? ''})` : ''}
                  </span>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={input.goodsPerClass[i] ?? 3}
                    onChange={e => handleGoodsChange(i, Number(e.target.value))}
                    className="input-field w-24 text-center"
                  />
                  <span className="text-xs text-gray-400">개</span>
                  {(input.goodsPerClass[i] ?? 3) > 6 && (
                    <span className="text-xs text-amber-600">
                      +{((input.goodsPerClass[i] ?? 3) - 6) * 2000}원
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-2">등록료 납부 방식</label>
            <div className="grid grid-cols-2 gap-2">
              {([10, 5] as const).map(term => (
                <button
                  key={term}
                  type="button"
                  onClick={() => setInput(prev => ({ ...prev, registrationTerm: term }))}
                  className={`py-2 rounded-lg text-xs font-medium border transition-colors ${
                    input.registrationTerm === term
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                  }`}
                >
                  {term}년 {term === 10 ? '일시납' : '분납'}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={input.isOnline}
                onChange={e => setInput(prev => ({ ...prev, isOnline: e.target.checked }))}
                className="w-4 h-4 accent-blue-600"
              />
              <span className="text-sm text-gray-700">전자출원 (권장)</span>
              {!input.isOnline && <span className="text-xs text-amber-600">종이출원 20% 가산</span>}
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={input.includeAttorneyFee}
                onChange={e => setInput(prev => ({ ...prev, includeAttorneyFee: e.target.checked }))}
                className="w-4 h-4 accent-blue-600"
              />
              <span className="text-sm text-gray-700">변리사 수임료 포함</span>
            </label>
            {input.includeAttorneyFee && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  瑜섎떦 蹂由ъ궗 ?섏엫猷?
                </label>
                <input
                  type="number"
                  min={0}
                  step={10000}
                  value={input.customAttorneyFeePerClass ?? 0}
                  onChange={e =>
                    setInput(prev => ({
                      ...prev,
                      customAttorneyFeePerClass: Number(e.target.value),
                    }))
                  }
                  className="input-field"
                />
                <div className="text-xs text-gray-400 mt-1">
                  0??湲곕낯 怨꾩궛 ?쒖떇?쓣 ?ъ슜?⑸땲?? ?ㅼ젙?먯꽌 湲곕낯媛믪쓣 諛붽꿀 ???덉뒿?덈떎.
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 결과 패널 */}
        <div className="space-y-4">
          {/* 요약 */}
          <div className="card p-5">
            <h2 className="font-semibold text-gray-900 mb-4">비용 요약</h2>
            <div className="space-y-3">
              <CostRow label="출원료" amount={result.applicationFee} highlight={false} />
              <CostRow label={`등록료 (${input.registrationTerm}년)`} amount={result.registrationFee} highlight={false} />
              {result.attorneyFee > 0 && (
                <CostRow label="변리사 수임료" amount={result.attorneyFee} highlight={false} />
              )}
              {result.discountInfo && (
                <div className="text-xs text-green-700 bg-green-50 rounded px-3 py-1.5 flex items-center gap-1">
                  <Info size={11} />
                  {result.discountInfo}
                </div>
              )}
              <div className="border-t border-gray-200 pt-3">
                <CostRow label="합계 (VAT 별도)" amount={result.totalFee} highlight={true} />
              </div>
            </div>
          </div>

          {/* 상세 내역 토글 */}
          <div className="card overflow-hidden">
            <button
              onClick={() => setShowBreakdown(!showBreakdown)}
              className="w-full px-5 py-3 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <span>상세 내역</span>
              {showBreakdown ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
            {showBreakdown && (
              <div className="px-5 pb-4 space-y-2">
                {result.breakdown.map((item, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <div>
                      <span className={item.amount < 0 ? 'text-green-700' : 'text-gray-700'}>
                        {item.label}
                      </span>
                      {item.detail && (
                        <div className="text-xs text-gray-400">{item.detail}</div>
                      )}
                    </div>
                    <span className={`font-medium ${item.amount < 0 ? 'text-green-700' : 'text-gray-900'}`}>
                      {item.amount < 0 ? '- ' : ''}{formatKRW(Math.abs(item.amount))}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 주의사항 */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="text-xs font-semibold text-amber-700 mb-2 flex items-center gap-1">
              <Info size={12} /> 주의사항
            </div>
            <ul className="space-y-1">
              {result.notes.map((note, i) => (
                <li key={i} className="text-xs text-amber-800">· {note}</li>
              ))}
            </ul>
          </div>

          {/* 출원 건에 저장 */}
          {filings.length > 0 && (
            <div className="card p-4 space-y-2">
              <div className="text-xs font-medium text-gray-600">출원 건에 비용 저장</div>
              <div className="flex gap-2">
                <select
                  className="input-field flex-1"
                  value={selectedFilingId}
                  onChange={e => setSelectedFilingId(e.target.value)}
                >
                  <option value="">출원 건 선택...</option>
                  {filings.map(f => (
                    <option key={f.id} value={f.id}>{f.trademarkName}</option>
                  ))}
                </select>
                <button
                  onClick={handleSaveToFiling}
                  disabled={!selectedFilingId}
                  className="btn-primary whitespace-nowrap"
                >
                  저장
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 비교표 */}
      <div className="card p-5">
        <h2 className="font-semibold text-gray-900 mb-4">류수별 비용 비교표</h2>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="table-header">출원인</th>
                {[1, 2, 3, 5].map(n => (
                  <th key={n} className="table-header">{n}류</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(['개인', '소상공인', '법인'] as ApplicantType[]).map(type => (
                <tr key={type} className={input.applicantType === type ? 'bg-blue-50' : ''}>
                  <td className="table-cell font-medium">{type}</td>
                  {[1, 2, 3, 5].map(n => {
                    const cost = calculateFilingCost({
                      ...input,
                      applicantType: type,
                      classes: n,
                      goodsPerClass: Array(n).fill(3),
                    })
                    return (
                      <td key={n} className="table-cell">
                        {formatKRW(cost.totalFee)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="text-xs text-gray-400 mt-2">
          * 전자출원, 지정상품 3개/류, {input.registrationTerm}년 일시납, 변리사 수임료 {input.includeAttorneyFee ? '포함' : '미포함'}
        </div>
      </div>
    </div>
  )
}

function CostRow({ label, amount, highlight }: { label: string; amount: number; highlight: boolean }) {
  return (
    <div className={`flex justify-between ${highlight ? 'text-base' : 'text-sm'}`}>
      <span className={highlight ? 'font-bold text-gray-900' : 'text-gray-600'}>{label}</span>
      <span className={highlight ? 'font-bold text-blue-700 text-lg' : 'font-medium text-gray-900'}>
        {formatKRW(amount)}
      </span>
    </div>
  )
}
