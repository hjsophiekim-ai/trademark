import { useState, useMemo } from 'react'
import { Search, Tag, Info } from 'lucide-react'
import { SIMILAR_GROUP_CODES, CLASS_NAMES, RETAIL_SERVICE_MAP } from '../data/similarGroupCodes'

export default function SimilarGroupCodeSearch() {
  const [search, setSearch] = useState('')
  const [classFilter, setClassFilter] = useState<number | 'all'>('all')
  const [selected, setSelected] = useState<typeof SIMILAR_GROUP_CODES[0] | null>(null)

  const classes = useMemo(() =>
    Array.from(new Set(SIMILAR_GROUP_CODES.map(c => c.class))).sort((a, b) => a - b),
    []
  )

  const filtered = useMemo(() =>
    SIMILAR_GROUP_CODES.filter(c => {
      const matchClass = classFilter === 'all' || c.class === classFilter
      const matchSearch = !search ||
        c.code.toLowerCase().includes(search.toLowerCase()) ||
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.description.toLowerCase().includes(search.toLowerCase()) ||
        c.examples.some(e => e.includes(search))
      return matchClass && matchSearch
    }),
    [search, classFilter]
  )

  return (
    <div className="flex h-full">
      {/* 검색 패널 */}
      <div className="flex-1 flex flex-col border-r border-gray-200">
        <div className="px-6 py-4 border-b bg-white space-y-3">
          <h1 className="text-xl font-bold text-gray-900">유사군 코드 조회</h1>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="input-field pl-8"
                placeholder="코드, 상품명, 설명 검색..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <select
              className="input-field w-auto"
              value={classFilter}
              onChange={e => setClassFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
            >
              <option value="all">전체 류</option>
              {classes.map(c => (
                <option key={c} value={c}>제{c}류 - {CLASS_NAMES[c]}</option>
              ))}
            </select>
          </div>
          <div className="text-xs text-gray-400">{filtered.length}개 코드</div>
        </div>

        <div className="flex-1 overflow-auto">
          <table className="w-full">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="table-header">코드</th>
                <th className="table-header">류</th>
                <th className="table-header">명칭</th>
                <th className="table-header">설명</th>
                <th className="table-header">판매업 연계</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(code => {
                const retailCodes = RETAIL_SERVICE_MAP[code.code] ?? []
                return (
                  <tr
                    key={code.code}
                    className={`hover:bg-blue-50 cursor-pointer transition-colors ${selected?.code === code.code ? 'bg-blue-50' : ''}`}
                    onClick={() => setSelected(code)}
                  >
                    <td className="table-cell">
                      <span className="font-mono text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                        {code.code}
                      </span>
                    </td>
                    <td className="table-cell text-gray-500 text-xs">
                      제{code.class}류
                    </td>
                    <td className="table-cell font-medium text-gray-900">{code.name}</td>
                    <td className="table-cell text-gray-500 text-xs">{code.description}</td>
                    <td className="table-cell">
                      {retailCodes.length > 0 ? (
                        <div className="flex gap-1 flex-wrap">
                          {retailCodes.map(rc => (
                            <span key={rc} className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-mono">
                              {rc}
                            </span>
                          ))}
                        </div>
                      ) : '-'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 상세 패널 */}
      {selected ? (
        <div className="w-72 bg-white border-l border-gray-200 p-5 space-y-5">
          <div>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-mono font-semibold">
              {selected.code}
            </span>
            <h3 className="text-lg font-bold text-gray-900 mt-2">{selected.name}</h3>
            <div className="text-sm text-gray-500 mt-1">
              제{selected.class}류 ({CLASS_NAMES[selected.class]})
            </div>
          </div>

          <div>
            <div className="text-xs font-semibold text-gray-500 mb-1">설명</div>
            <p className="text-sm text-gray-700">{selected.description}</p>
          </div>

          <div>
            <div className="text-xs font-semibold text-gray-500 mb-2">지정상품 예시</div>
            <div className="flex flex-wrap gap-1.5">
              {selected.examples.map(e => (
                <span key={e} className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">{e}</span>
              ))}
            </div>
          </div>

          {RETAIL_SERVICE_MAP[selected.code] && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 mb-2">
                <Tag size={12} />
                판매업 연계 유사군
              </div>
              <div className="space-y-1">
                {RETAIL_SERVICE_MAP[selected.code].map(rc => {
                  const retailCode = SIMILAR_GROUP_CODES.find(c => c.code === rc)
                  return (
                    <div key={rc} className="text-xs text-amber-800">
                      <span className="font-mono font-semibold">{rc}</span>
                      {retailCode && <span className="ml-1 text-amber-600">- {retailCode.name}</span>}
                    </div>
                  )
                })}
              </div>
              <div className="mt-2 text-xs text-amber-600 flex items-start gap-1">
                <Info size={10} className="mt-0.5 shrink-0" />
                <span>해당 상품의 판매업(소매업) 출원 시 함께 검토 필요</span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="w-72 bg-white border-l border-gray-200 flex items-center justify-center">
          <div className="text-center text-sm text-gray-400">
            <Tag size={32} className="mx-auto mb-2 text-gray-200" />
            코드를 선택하면<br />상세 정보가 표시됩니다
          </div>
        </div>
      )}
    </div>
  )
}
