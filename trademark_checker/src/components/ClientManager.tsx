import { useState } from 'react'
import { Plus, Search, Edit2, Trash2, X, User, Building2 } from 'lucide-react'
import type { Client, TrademarkFiling, ApplicantType } from '../types'
import { StatusBadge } from './Dashboard'

interface Props {
  clients: Client[]
  filings: TrademarkFiling[]
  onUpdate: (clients: Client[]) => void
}

const APPLICANT_TYPES: ApplicantType[] = ['개인', '법인', '소상공인', '중소기업', '대기업', '국가/공공기관']

export default function ClientManager({ clients, filings, onUpdate }: Props) {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Client | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<Client | null>(null)

  const filtered = clients.filter(c =>
    !search ||
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.email.toLowerCase().includes(search.toLowerCase()) ||
    c.phone.includes(search) ||
    c.businessNumber?.includes(search)
  )

  const handleDelete = (id: string) => {
    if (!confirm('이 의뢰인을 삭제하시겠습니까? 관련 출원 데이터는 유지됩니다.')) return
    onUpdate(clients.filter(c => c.id !== id))
    if (selected?.id === id) setSelected(null)
  }

  const handleSave = (client: Client) => {
    if (editTarget) {
      onUpdate(clients.map(c => c.id === client.id ? client : c))
    } else {
      onUpdate([...clients, client])
    }
    setShowForm(false)
    setEditTarget(null)
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col border-r border-gray-200">
        <div className="px-6 py-4 border-b bg-white space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900">의뢰인 관리</h1>
            <button onClick={() => { setEditTarget(null); setShowForm(true) }} className="btn-primary flex items-center gap-1.5">
              <Plus size={15} /> 새 의뢰인
            </button>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="input-field pl-8"
              placeholder="이름, 이메일, 연락처 검색..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-sm text-gray-400">의뢰인 없음</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filtered.map(client => {
                const clientFilings = filings.filter(f => f.clientId === client.id)
                const isSelected = selected?.id === client.id
                return (
                  <div
                    key={client.id}
                    className={`px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors ${isSelected ? 'bg-blue-50' : ''}`}
                    onClick={() => setSelected(client)}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${client.type === '개인' || client.type === '소상공인' ? 'bg-blue-100' : 'bg-purple-100'}`}>
                        {client.type === '개인' || client.type === '소상공인'
                          ? <User size={18} className="text-blue-600" />
                          : <Building2 size={18} className="text-purple-600" />
                        }
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">{client.name}</div>
                        <div className="text-xs text-gray-400">{client.type} · {client.email}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-xs text-gray-400">
                        출원 {clientFilings.length}건
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={e => { e.stopPropagation(); setEditTarget(client); setShowForm(true) }}
                          className="p-1 text-gray-400 hover:text-blue-600 rounded"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); handleDelete(client.id) }}
                          className="p-1 text-gray-400 hover:text-red-600 rounded"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* 상세 */}
      {selected && (
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
          <div className="px-5 py-4 border-b flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">의뢰인 상세</h3>
            <button onClick={() => setSelected(null)} className="p-1.5 text-gray-400 hover:text-gray-700 rounded">
              <X size={15} />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                {selected.type === '개인' || selected.type === '소상공인'
                  ? <User size={22} className="text-blue-600" />
                  : <Building2 size={22} className="text-purple-600" />
                }
              </div>
              <div>
                <div className="font-bold text-gray-900">{selected.name}</div>
                <div className="text-sm text-gray-400">{selected.type}</div>
              </div>
            </div>

            {[
              { label: '이메일', value: selected.email },
              { label: '연락처', value: selected.phone },
              { label: '사업자번호', value: selected.businessNumber ?? '-' },
              { label: '담당자', value: selected.contact },
              { label: '주소', value: selected.address ?? '-' },
              { label: '등록일', value: selected.createdAt.slice(0, 10) },
            ].map(({ label, value }) => (
              <div key={label} className="flex gap-2 text-sm">
                <span className="w-20 text-gray-400 shrink-0">{label}</span>
                <span className="text-gray-800">{value}</span>
              </div>
            ))}

            <div>
              <div className="text-xs font-semibold text-gray-500 mb-2">출원 목록</div>
              <div className="space-y-2">
                {filings
                  .filter(f => f.clientId === selected.id)
                  .map(f => (
                    <div key={f.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                      <span className="text-sm font-medium text-gray-700">{f.trademarkName}</span>
                      <StatusBadge status={f.status} />
                    </div>
                  ))
                }
                {filings.filter(f => f.clientId === selected.id).length === 0 && (
                  <div className="text-sm text-gray-400">출원 없음</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {showForm && (
        <ClientForm
          client={editTarget}
          onSave={handleSave}
          onClose={() => { setShowForm(false); setEditTarget(null) }}
        />
      )}
    </div>
  )
}

function ClientForm({ client, onSave, onClose }: {
  client: Client | null
  onSave: (c: Client) => void
  onClose: () => void
}) {
  const [form, setForm] = useState<Partial<Client>>(
    client ?? { type: '개인' }
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name || !form.email) return
    const now = new Date().toISOString()
    onSave({
      id: client?.id ?? `c${Date.now()}`,
      name: form.name!,
      type: form.type ?? '개인',
      businessNumber: form.businessNumber,
      contact: form.contact ?? '',
      email: form.email!,
      phone: form.phone ?? '',
      address: form.address,
      filingIds: client?.filingIds ?? [],
      createdAt: client?.createdAt ?? now,
      updatedAt: now,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold">{client ? '의뢰인 수정' : '새 의뢰인 등록'}</h2>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-700 rounded">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">이름 *</label>
              <input className="input-field" value={form.name ?? ''} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">유형</label>
              <select className="input-field" value={form.type ?? '개인'} onChange={e => setForm(f => ({ ...f, type: e.target.value as ApplicantType }))}>
                {APPLICANT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">이메일 *</label>
            <input type="email" className="input-field" value={form.email ?? ''} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">연락처</label>
              <input className="input-field" placeholder="010-0000-0000" value={form.phone ?? ''} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">담당자</label>
              <input className="input-field" value={form.contact ?? ''} onChange={e => setForm(f => ({ ...f, contact: e.target.value }))} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">사업자등록번호</label>
            <input className="input-field" placeholder="000-00-00000" value={form.businessNumber ?? ''} onChange={e => setForm(f => ({ ...f, businessNumber: e.target.value }))} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">주소</label>
            <input className="input-field" value={form.address ?? ''} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} />
          </div>
        </form>
        <div className="px-6 py-4 border-t flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">취소</button>
          <button onClick={handleSubmit as never} className="btn-primary">{client ? '수정 저장' : '등록'}</button>
        </div>
      </div>
    </div>
  )
}
