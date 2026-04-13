import { useState } from 'react'
import { Plus, Search, Filter, Edit2, Trash2, ChevronRight, X } from 'lucide-react'
import type { TrademarkFiling, Client, FilingStatus, TrademarkType } from '../types'
import { StatusBadge } from './Dashboard'
import { CLASS_NAMES } from '../data/similarGroupCodes'
import { formatKRW } from '../utils/costCalculator'

interface FilingManagerProps {
  filings: TrademarkFiling[]
  clients: Client[]
  onUpdate: (filings: TrademarkFiling[]) => void
}

const STATUS_OPTIONS: FilingStatus[] = [
  '검토중', '출원준비', '출원완료', '심사중', '등록결정', '등록완료', '거절결정', '이의신청중', '포기',
]

const TYPE_OPTIONS: TrademarkType[] = ['문자', '도형', '결합', '입체', '색채', '소리', '냄새']

export default function FilingManager({ filings, clients, onUpdate }: FilingManagerProps) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('전체')
  const [selected, setSelected] = useState<TrademarkFiling | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<TrademarkFiling | null>(null)

  const filtered = filings.filter(f => {
    const client = clients.find(c => c.id === f.clientId)
    const matchSearch = !search ||
      f.trademarkName.toLowerCase().includes(search.toLowerCase()) ||
      client?.name.toLowerCase().includes(search.toLowerCase()) ||
      f.applicationNumber?.includes(search) ||
      f.goods.some(g => g.includes(search))
    const matchStatus = statusFilter === '전체' || f.status === statusFilter
    return matchSearch && matchStatus
  })

  const handleDelete = (id: string) => {
    if (!confirm('이 출원 건을 삭제하시겠습니까?')) return
    onUpdate(filings.filter(f => f.id !== id))
    if (selected?.id === id) setSelected(null)
  }

  const handleSave = (filing: TrademarkFiling) => {
    if (editTarget) {
      onUpdate(filings.map(f => f.id === filing.id ? filing : f))
    } else {
      onUpdate([...filings, filing])
    }
    setShowForm(false)
    setEditTarget(null)
  }

  return (
    <div className="flex h-full">
      {/* 목록 패널 */}
      <div className="flex-1 flex flex-col border-r border-gray-200">
        {/* 헤더 */}
        <div className="px-6 py-4 border-b border-gray-200 bg-white space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900">출원 관리</h1>
            <button
              onClick={() => { setEditTarget(null); setShowForm(true) }}
              className="btn-primary flex items-center gap-1.5"
            >
              <Plus size={15} /> 새 출원
            </button>
          </div>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="input-field pl-8"
                placeholder="상표명, 의뢰인, 출원번호 검색..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-1">
              <Filter size={14} className="text-gray-400" />
              <select
                className="input-field w-auto"
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                <option value="전체">전체</option>
                {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* 테이블 */}
        <div className="flex-1 overflow-auto">
          <table className="w-full">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="table-header">상표명</th>
                <th className="table-header">의뢰인</th>
                <th className="table-header">류</th>
                <th className="table-header">출원번호</th>
                <th className="table-header">상태</th>
                <th className="table-header">비용</th>
                <th className="table-header"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="table-cell text-center text-gray-400 py-12">
                    검색 결과가 없습니다
                  </td>
                </tr>
              ) : (
                filtered.map(filing => {
                  const client = clients.find(c => c.id === filing.clientId)
                  const isSelected = selected?.id === filing.id
                  return (
                    <tr
                      key={filing.id}
                      className={`hover:bg-blue-50 cursor-pointer transition-colors ${isSelected ? 'bg-blue-50' : ''}`}
                      onClick={() => setSelected(filing)}
                    >
                      <td className="table-cell font-medium text-gray-900">{filing.trademarkName}</td>
                      <td className="table-cell text-gray-500">{client?.name ?? '-'}</td>
                      <td className="table-cell">
                        <div className="flex flex-wrap gap-1">
                          {filing.classes.map(c => (
                            <span key={c} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                              {c}류
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="table-cell text-gray-400 text-xs font-mono">
                        {filing.applicationNumber ?? '미부여'}
                      </td>
                      <td className="table-cell">
                        <StatusBadge status={filing.status} />
                      </td>
                      <td className="table-cell text-xs text-gray-500">
                        {filing.costInfo ? formatKRW(filing.costInfo.totalFee) : '-'}
                      </td>
                      <td className="table-cell">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={e => { e.stopPropagation(); setEditTarget(filing); setShowForm(true) }}
                            className="p-1 text-gray-400 hover:text-blue-600 rounded"
                          >
                            <Edit2 size={14} />
                          </button>
                          <button
                            onClick={e => { e.stopPropagation(); handleDelete(filing.id) }}
                            className="p-1 text-gray-400 hover:text-red-600 rounded"
                          >
                            <Trash2 size={14} />
                          </button>
                          <ChevronRight size={14} className="text-gray-300" />
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 상세 패널 */}
      {selected && (
        <FilingDetail
          filing={selected}
          client={clients.find(c => c.id === selected.clientId)}
          onClose={() => setSelected(null)}
          onEdit={() => { setEditTarget(selected); setShowForm(true) }}
        />
      )}

      {/* 출원 폼 모달 */}
      {showForm && (
        <FilingForm
          filing={editTarget}
          clients={clients}
          onSave={handleSave}
          onClose={() => { setShowForm(false); setEditTarget(null) }}
        />
      )}
    </div>
  )
}

// 상세 패널
function FilingDetail({ filing, client, onClose, onEdit }: {
  filing: TrademarkFiling
  client?: Client
  onClose: () => void
  onEdit: () => void
}) {
  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
      <div className="px-5 py-4 border-b flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">출원 상세</h3>
        <div className="flex gap-1">
          <button onClick={onEdit} className="p-1.5 text-gray-400 hover:text-blue-600 rounded">
            <Edit2 size={15} />
          </button>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-700 rounded">
            <X size={15} />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-5 space-y-4">
        <div>
          <div className="text-lg font-bold text-gray-900">{filing.trademarkName}</div>
          <div className="mt-1"><StatusBadge status={filing.status} /></div>
        </div>

        <InfoRow label="유형" value={filing.trademarkType} />
        <InfoRow label="의뢰인" value={client?.name ?? '-'} />
        <InfoRow label="지정 류" value={filing.classes.map(c => `${c}류 (${CLASS_NAMES[c] ?? ''})`).join(', ')} />
        <InfoRow label="지정상품" value={filing.goods.join(', ')} />
        <InfoRow label="출원번호" value={filing.applicationNumber ?? '미부여'} />
        <InfoRow label="등록번호" value={filing.registrationNumber ?? '-'} />
        <InfoRow label="출원일" value={filing.applicationDate ?? '-'} />
        <InfoRow label="등록일" value={filing.registrationDate ?? '-'} />
        <InfoRow label="만료일" value={filing.expiryDate ?? '-'} />

        {filing.costInfo && (
          <div className="bg-blue-50 rounded-lg p-3">
            <div className="text-xs font-semibold text-blue-700 mb-2">비용 정보</div>
            <div className="space-y-1 text-xs text-blue-800">
              <div className="flex justify-between">
                <span>출원료</span><span>{formatKRW(filing.costInfo.applicationFee)}</span>
              </div>
              <div className="flex justify-between">
                <span>등록료</span><span>{formatKRW(filing.costInfo.registrationFee)}</span>
              </div>
              {filing.costInfo.attorneyFee > 0 && (
                <div className="flex justify-between">
                  <span>수임료</span><span>{formatKRW(filing.costInfo.attorneyFee)}</span>
                </div>
              )}
              <div className="flex justify-between font-semibold border-t border-blue-200 pt-1 mt-1">
                <span>합계</span><span>{formatKRW(filing.costInfo.totalFee)}</span>
              </div>
            </div>
          </div>
        )}

        {filing.notes && (
          <div>
            <div className="text-xs font-semibold text-gray-500 mb-1">메모</div>
            <div className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{filing.notes}</div>
          </div>
        )}
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="w-20 text-gray-400 shrink-0">{label}</span>
      <span className="text-gray-800 flex-1 break-all">{value}</span>
    </div>
  )
}

// 출원 등록/수정 폼
function FilingForm({ filing, clients, onSave, onClose }: {
  filing: TrademarkFiling | null
  clients: Client[]
  onSave: (f: TrademarkFiling) => void
  onClose: () => void
}) {
  const [form, setForm] = useState<Partial<TrademarkFiling>>(
    filing ?? {
      trademarkType: '문자',
      classes: [],
      similarGroupCodes: [],
      goods: [],
      status: '검토중',
      notes: '',
    }
  )
  const [goodsInput, setGoodsInput] = useState(filing?.goods.join(', ') ?? '')
  const [classInput, setClassInput] = useState(filing?.classes.join(', ') ?? '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.trademarkName || !form.clientId) return
    const now = new Date().toISOString()
    onSave({
      id: filing?.id ?? `f${Date.now()}`,
      clientId: form.clientId!,
      trademarkName: form.trademarkName!,
      trademarkType: form.trademarkType ?? '문자',
      classes: classInput.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n)),
      similarGroupCodes: form.similarGroupCodes ?? [],
      goods: goodsInput.split(',').map(s => s.trim()).filter(Boolean),
      status: form.status ?? '검토중',
      applicationNumber: form.applicationNumber,
      registrationNumber: form.registrationNumber,
      applicationDate: form.applicationDate,
      registrationDate: form.registrationDate,
      expiryDate: form.expiryDate,
      notes: form.notes ?? '',
      createdAt: filing?.createdAt ?? now,
      updatedAt: now,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] flex flex-col shadow-xl">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">{filing ? '출원 수정' : '새 출원 등록'}</h2>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-700 rounded">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex-1 overflow-auto p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">상표명 *</label>
            <input
              className="input-field"
              value={form.trademarkName ?? ''}
              onChange={e => setForm(f => ({ ...f, trademarkName: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">의뢰인 *</label>
            <select
              className="input-field"
              value={form.clientId ?? ''}
              onChange={e => setForm(f => ({ ...f, clientId: e.target.value }))}
              required
            >
              <option value="">선택</option>
              {clients.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">상표 유형</label>
              <select
                className="input-field"
                value={form.trademarkType ?? '문자'}
                onChange={e => setForm(f => ({ ...f, trademarkType: e.target.value as TrademarkType }))}
              >
                {TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">진행 상태</label>
              <select
                className="input-field"
                value={form.status ?? '검토중'}
                onChange={e => setForm(f => ({ ...f, status: e.target.value as FilingStatus }))}
              >
                {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">지정 류 (쉼표 구분)</label>
            <input
              className="input-field"
              placeholder="예: 25, 35"
              value={classInput}
              onChange={e => setClassInput(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">지정상품 (쉼표 구분)</label>
            <input
              className="input-field"
              placeholder="예: 티셔츠, 바지, 재킷"
              value={goodsInput}
              onChange={e => setGoodsInput(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">출원번호</label>
              <input
                className="input-field"
                placeholder="4020260012345"
                value={form.applicationNumber ?? ''}
                onChange={e => setForm(f => ({ ...f, applicationNumber: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">출원일</label>
              <input
                type="date"
                className="input-field"
                value={form.applicationDate ?? ''}
                onChange={e => setForm(f => ({ ...f, applicationDate: e.target.value }))}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">메모</label>
            <textarea
              className="input-field"
              rows={3}
              value={form.notes ?? ''}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
            />
          </div>
        </form>
        <div className="px-6 py-4 border-t flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">취소</button>
          <button onClick={handleSubmit as never} className="btn-primary">
            {filing ? '수정 저장' : '등록'}
          </button>
        </div>
      </div>
    </div>
  )
}
