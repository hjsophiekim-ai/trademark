import { useState } from 'react'
import { Plus, Search, FileText, AlertTriangle, CheckCircle, X, Copy, ExternalLink } from 'lucide-react'
import type { SimilarityCheckReport, TrademarkFiling, Client } from '../types'
import { generateSearchFormula } from '../utils/searchFormula'
import { SIMILAR_GROUP_CODES } from '../data/similarGroupCodes'
import { getMockKiprisResults } from '../data/mockData'

interface Props {
  reports: SimilarityCheckReport[]
  filings: TrademarkFiling[]
  clients: Client[]
  onUpdate: (reports: SimilarityCheckReport[]) => void
}

export default function SimilarityCheck({ reports, filings, clients, onUpdate }: Props) {
  const [showNew, setShowNew] = useState(false)
  const [selected, setSelected] = useState<SimilarityCheckReport | null>(null)

  return (
    <div className="flex h-full">
      {/* 목록 */}
      <div className="flex-1 flex flex-col border-r border-gray-200">
        <div className="px-6 py-4 border-b bg-white flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">유사성 검토</h1>
          <button onClick={() => setShowNew(true)} className="btn-primary flex items-center gap-1.5">
            <Plus size={15} /> 새 검토
          </button>
        </div>

        <div className="flex-1 overflow-auto divide-y divide-gray-100">
          {reports.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-sm text-gray-400">
              작성된 검토 보고서가 없습니다
            </div>
          ) : (
            reports.map(report => {
              const client = clients.find(c => c.id === report.clientId)
              return (
                <div
                  key={report.id}
                  className={`px-6 py-4 cursor-pointer hover:bg-gray-50 transition-colors ${selected?.id === report.id ? 'bg-blue-50' : ''}`}
                  onClick={() => setSelected(report)}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-gray-900">{report.targetTrademark}</div>
                      <div className="text-xs text-gray-400 mt-0.5">{client?.name} · {report.targetClasses.map(c => `${c}류`).join(', ')}</div>
                      <div className="text-xs text-gray-500 mt-1">검색식: <code className="bg-gray-100 px-1 rounded">{report.searchFormula.slice(0, 40)}...</code></div>
                    </div>
                    <div className="flex items-center gap-2">
                      <RiskBadge level={report.riskLevel} />
                      <span className="text-xs text-gray-400">{report.createdAt.slice(0, 10)}</span>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* 상세 */}
      {selected ? (
        <ReportDetail report={selected} onClose={() => setSelected(null)} />
      ) : (
        <div className="w-96 bg-white border-l border-gray-200 flex items-center justify-center">
          <div className="text-center text-sm text-gray-400">
            <FileText size={32} className="mx-auto mb-2 text-gray-200" />
            보고서를 선택해주세요
          </div>
        </div>
      )}

      {/* 새 검토 폼 */}
      {showNew && (
        <NewReportForm
          filings={filings}
          clients={clients}
          onSave={report => { onUpdate([...reports, report]); setShowNew(false) }}
          onClose={() => setShowNew(false)}
        />
      )}
    </div>
  )
}

function RiskBadge({ level }: { level: 'LOW' | 'MEDIUM' | 'HIGH' }) {
  const styles = {
    LOW: 'bg-green-100 text-green-700',
    MEDIUM: 'bg-yellow-100 text-yellow-700',
    HIGH: 'bg-red-100 text-red-700',
  }
  const labels = { LOW: '저위험', MEDIUM: '중위험', HIGH: '고위험' }
  return <span className={`status-badge ${styles[level]}`}>{labels[level]}</span>
}

function ReportDetail({ report, onClose }: { report: SimilarityCheckReport; onClose: () => void }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(report.searchFormula)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
      <div className="px-5 py-4 border-b flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">검토 보고서</h3>
        <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-700 rounded">
          <X size={15} />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-5 space-y-5">
        <div>
          <div className="text-lg font-bold text-gray-900">{report.targetTrademark}</div>
          <div className="text-sm text-gray-500 mt-0.5">
            {report.targetClasses.map(c => `${c}류`).join(', ')} · {report.targetGoods}
          </div>
          <div className="mt-2"><RiskBadge level={report.riskLevel} /></div>
        </div>

        <div className="bg-slate-50 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-semibold text-slate-600">키프리스 검색식</div>
            <div className="flex gap-1">
              <button onClick={handleCopy} className="p-1 text-slate-400 hover:text-blue-600 rounded">
                <Copy size={13} />
              </button>
              <a
                href={`https://www.kipris.or.kr/khome/main.do`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-slate-400 hover:text-blue-600 rounded"
                title="키프리스 열기"
              >
                <ExternalLink size={13} />
              </a>
            </div>
          </div>
          <code className="text-xs text-slate-800 break-all">{report.searchFormula}</code>
          {copied && <div className="text-xs text-green-600 mt-1">클립보드에 복사됨</div>}
        </div>

        <div>
          <div className="text-xs font-semibold text-gray-500 mb-2">
            선행 유사상표 ({report.results.length}건)
          </div>
          <div className="space-y-3">
            {report.results.length === 0 ? (
              <div className="text-sm text-gray-400 flex items-center gap-2">
                <CheckCircle size={16} className="text-green-500" />
                유사 상표 없음
              </div>
            ) : (
              report.results.map((r, i) => (
                <div key={i} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-start justify-between mb-1">
                    <div className="font-medium text-sm text-gray-900">{r.trademarkName}</div>
                    <div className={`text-xs font-semibold px-2 py-0.5 rounded ${
                      r.similarityScore >= 70 ? 'bg-red-100 text-red-700' :
                      r.similarityScore >= 50 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>
                      유사도 {r.similarityScore}%
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    출원인: {r.applicant} · {r.status} · {r.applicationDate}
                  </div>
                  <div className="text-xs text-gray-600 mt-1 italic">{r.similarityReason}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 mb-2">
            {report.riskLevel === 'HIGH'
              ? <AlertTriangle size={13} />
              : <CheckCircle size={13} />
            }
            검토 의견
          </div>
          <p className="text-sm text-blue-900">{report.opinion}</p>
        </div>

        <div className="text-xs text-gray-400">
          작성일: {report.createdAt.slice(0, 10)}
        </div>
      </div>
    </div>
  )
}

function NewReportForm({ filings, clients, onSave, onClose }: {
  filings: TrademarkFiling[]
  clients: Client[]
  onSave: (r: SimilarityCheckReport) => void
  onClose: () => void
}) {
  const [targetTrademark, setTargetTrademark] = useState('')
  const [targetClasses, setTargetClasses] = useState('')
  const [targetGoods, setTargetGoods] = useState('')
  const [selectedCodes, setSelectedCodes] = useState<string[]>([])
  const [linkedFilingId, setLinkedFilingId] = useState('')
  const [opinion, setOpinion] = useState('')
  const [riskLevel, setRiskLevel] = useState<'LOW' | 'MEDIUM' | 'HIGH'>('LOW')
  const [searchFormula, setSearchFormula] = useState('')
  const [results, setResults] = useState<SimilarityCheckReport['results']>([])
  const [isSearching, setIsSearching] = useState(false)

  const handleGenerateFormula = () => {
    if (!targetTrademark) return
    const formula = generateSearchFormula(targetTrademark, selectedCodes)
    setSearchFormula(formula)
  }

  const handleMockSearch = async () => {
    if (!targetTrademark) return
    setIsSearching(true)
    await new Promise(r => setTimeout(r, 800))
    const mockResults = getMockKiprisResults(targetTrademark)
    setResults(mockResults)
    const maxScore = Math.max(...mockResults.map(r => r.similarityScore))
    setRiskLevel(maxScore >= 70 ? 'HIGH' : maxScore >= 50 ? 'MEDIUM' : 'LOW')
    setIsSearching(false)
  }

  const handleSave = () => {
    if (!targetTrademark) return
    const linkedFiling = filings.find(f => f.id === linkedFilingId)
    const now = new Date().toISOString()
    onSave({
      id: `r${Date.now()}`,
      filingId: linkedFilingId || undefined,
      clientId: linkedFiling?.clientId,
      targetTrademark,
      targetClasses: targetClasses.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n)),
      targetGoods,
      searchFormula,
      results,
      riskLevel,
      opinion,
      createdAt: now,
    })
  }

  const toggleCode = (code: string) => {
    setSelectedCodes(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    )
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-xl">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold">새 유사성 검토</h2>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-700 rounded">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">검토 상표명 *</label>
              <input
                className="input-field"
                value={targetTrademark}
                onChange={e => setTargetTrademark(e.target.value)}
                placeholder="예: MIRAE FASHION"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">지정 류 (쉼표 구분)</label>
              <input
                className="input-field"
                value={targetClasses}
                onChange={e => setTargetClasses(e.target.value)}
                placeholder="예: 25, 35"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">지정상품/서비스</label>
            <input
              className="input-field"
              value={targetGoods}
              onChange={e => setTargetGoods(e.target.value)}
              placeholder="예: 티셔츠, 청바지, 운동화"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-2">유사군 코드 선택</label>
            <div className="flex flex-wrap gap-1.5 max-h-28 overflow-auto border border-gray-200 rounded-lg p-3">
              {SIMILAR_GROUP_CODES.slice(0, 20).map(code => (
                <button
                  key={code.code}
                  type="button"
                  onClick={() => toggleCode(code.code)}
                  className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                    selectedCodes.includes(code.code)
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                  }`}
                >
                  {code.code} {code.name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-1">
              <label className="text-xs font-medium text-gray-600">키프리스 검색식</label>
              <button onClick={handleGenerateFormula} className="text-xs text-blue-600 hover:underline">자동 생성</button>
            </div>
            <div className="flex gap-2">
              <input
                className="input-field flex-1 font-mono text-xs"
                value={searchFormula}
                onChange={e => setSearchFormula(e.target.value)}
                placeholder="TN=[상표명+변형1+...] SC=코드1+코드2"
              />
              <button
                onClick={handleMockSearch}
                disabled={isSearching}
                className="btn-secondary flex items-center gap-1.5 whitespace-nowrap"
              >
                <Search size={13} />
                {isSearching ? '검색 중...' : 'Mock 검색'}
              </button>
            </div>
          </div>

          {results.length > 0 && (
            <div className="border border-gray-200 rounded-lg p-3">
              <div className="text-xs font-semibold text-gray-500 mb-2">검색 결과 ({results.length}건)</div>
              <div className="space-y-2">
                {results.map((r, i) => (
                  <div key={i} className="text-xs flex items-center gap-2">
                    <span className="font-mono text-gray-400">{r.applicationNumber}</span>
                    <span className="font-medium">{r.trademarkName}</span>
                    <span className="text-gray-400">{r.applicant}</span>
                    <span className={`ml-auto px-1.5 py-0.5 rounded font-semibold ${
                      r.similarityScore >= 70 ? 'bg-red-100 text-red-700' :
                      r.similarityScore >= 50 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-green-100 text-green-700'
                    }`}>{r.similarityScore}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">위험도</label>
              <select className="input-field" value={riskLevel} onChange={e => setRiskLevel(e.target.value as 'LOW' | 'MEDIUM' | 'HIGH')}>
                <option value="LOW">저위험</option>
                <option value="MEDIUM">중위험</option>
                <option value="HIGH">고위험</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">연계 출원 건</label>
              <select className="input-field" value={linkedFilingId} onChange={e => setLinkedFilingId(e.target.value)}>
                <option value="">없음</option>
                {filings.map(f => {
                  const client = clients.find(c => c.id === f.clientId)
                  return <option key={f.id} value={f.id}>{f.trademarkName} ({client?.name})</option>
                })}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">검토 의견</label>
            <textarea
              className="input-field"
              rows={3}
              value={opinion}
              onChange={e => setOpinion(e.target.value)}
              placeholder="선행 상표와의 유사도 분석 및 등록 가능성 의견..."
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">취소</button>
          <button onClick={handleSave} className="btn-primary">보고서 저장</button>
        </div>
      </div>
    </div>
  )
}
