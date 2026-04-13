import { useMemo } from 'react'
import {
  FileText, Users, CheckCircle2, AlertTriangle, Clock,
  TrendingUp, ArrowRight, Activity,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import type { Client, TrademarkFiling, SimilarityCheckReport, FilingStatus } from '../types'
import type { Page } from '../App'
import { formatKRW } from '../utils/costCalculator'

interface DashboardProps {
  clients: Client[]
  filings: TrademarkFiling[]
  reports: SimilarityCheckReport[]
  isMockMode: boolean
  onNavigate: (page: Page) => void
}

const STATUS_COLORS: Record<FilingStatus, string> = {
  '검토중': '#f59e0b',
  '출원준비': '#3b82f6',
  '출원완료': '#6366f1',
  '심사중': '#8b5cf6',
  '등록결정': '#10b981',
  '등록완료': '#059669',
  '거절결정': '#ef4444',
  '이의신청중': '#f97316',
  '포기': '#9ca3af',
}

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6366f1', '#f97316', '#9ca3af']

export default function Dashboard({ clients, filings, reports, isMockMode, onNavigate }: DashboardProps) {
  const stats = useMemo(() => {
    const statusDist: Record<string, number> = {}
    filings.forEach(f => {
      statusDist[f.status] = (statusDist[f.status] || 0) + 1
    })

    const totalRevenue = filings.reduce((sum, f) => sum + (f.costInfo?.totalFee ?? 0), 0)

    const activeStatuses: FilingStatus[] = ['출원준비', '출원완료', '심사중', '등록결정', '이의신청중']
    const activeFilings = filings.filter(f => activeStatuses.includes(f.status)).length

    return {
      totalFilings: filings.length,
      activeFilings,
      registeredCount: statusDist['등록완료'] ?? 0,
      rejectedCount: statusDist['거절결정'] ?? 0,
      totalClients: clients.length,
      totalRevenue,
      statusDist,
    }
  }, [clients, filings])

  const pieData = Object.entries(stats.statusDist).map(([status, count]) => ({
    name: status,
    value: count,
  }))

  // 월별 출원 건수 (최근 6개월)
  const monthlyData = useMemo(() => {
    const counts: Record<string, number> = {}
    filings.forEach(f => {
      if (f.applicationDate) {
        const month = f.applicationDate.slice(0, 7)
        counts[month] = (counts[month] || 0) + 1
      } else if (f.createdAt) {
        const month = f.createdAt.slice(0, 7)
        counts[month] = (counts[month] || 0) + 1
      }
    })
    const months = Object.keys(counts).sort().slice(-6)
    return months.map(m => ({
      month: m.slice(5) + '월',
      건수: counts[m],
    }))
  }, [filings])

  const recentFilings = [...filings]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 5)

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>
          <p className="text-sm text-gray-500 mt-1">
            {new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}
          </p>
        </div>
        {isMockMode && (
          <div className="px-3 py-1.5 bg-amber-100 border border-amber-300 rounded-lg text-xs text-amber-700 font-medium">
            Mock 데이터 모드 - 설정에서 실데이터로 전환 가능
          </div>
        )}
      </div>

      {/* 주요 통계 카드 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="전체 출원"
          value={stats.totalFilings}
          sub={`진행중 ${stats.activeFilings}건`}
          icon={<FileText size={20} className="text-blue-500" />}
          color="blue"
          onClick={() => onNavigate('filings')}
        />
        <StatCard
          label="등록 완료"
          value={stats.registeredCount}
          sub={`총 ${stats.totalFilings}건 중`}
          icon={<CheckCircle2 size={20} className="text-green-500" />}
          color="green"
        />
        <StatCard
          label="의뢰인"
          value={stats.totalClients}
          sub="전체"
          icon={<Users size={20} className="text-purple-500" />}
          color="purple"
          onClick={() => onNavigate('clients')}
        />
        <StatCard
          label="거절 결정"
          value={stats.rejectedCount}
          sub="이의신청 검토 필요"
          icon={<AlertTriangle size={20} className="text-red-500" />}
          color="red"
        />
      </div>

      {/* 수임료 총계 */}
      {stats.totalRevenue > 0 && (
        <div className="card p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
              <TrendingUp size={20} className="text-blue-600" />
            </div>
            <div>
              <div className="text-sm text-gray-500">총 출원 비용 (예상)</div>
              <div className="text-2xl font-bold text-gray-900">{formatKRW(stats.totalRevenue)}</div>
            </div>
          </div>
          <button
            onClick={() => onNavigate('cost-calculator')}
            className="btn-secondary flex items-center gap-1 text-xs"
          >
            비용 계산기 <ArrowRight size={12} />
          </button>
        </div>
      )}

      {/* 차트 영역 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 상태 분포 파이 차트 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">출원 현황</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry, i) => (
                    <Cell
                      key={entry.name}
                      fill={STATUS_COLORS[entry.name as FilingStatus] ?? PIE_COLORS[i % PIE_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [`${v}건`, '']} />
                <Legend iconType="circle" iconSize={8} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart />
          )}
        </div>

        {/* 월별 출원 바 차트 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">월별 출원 건수</h3>
          {monthlyData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={monthlyData} barSize={28}>
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="건수" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart />
          )}
        </div>
      </div>

      {/* 최근 출원 목록 */}
      <div className="card">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Activity size={16} className="text-gray-400" />
            최근 출원
          </h3>
          <button
            onClick={() => onNavigate('filings')}
            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
          >
            전체 보기 <ArrowRight size={12} />
          </button>
        </div>
        <div className="divide-y divide-gray-50">
          {recentFilings.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-gray-400">출원 데이터가 없습니다</div>
          ) : (
            recentFilings.map(filing => {
              const client = clients.find(c => c.id === filing.clientId)
              return (
                <div key={filing.id} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50 cursor-pointer" onClick={() => onNavigate('filings')}>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center text-xs font-bold text-blue-600">
                      {filing.classes[0] ?? '?'}류
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900">{filing.trademarkName}</div>
                      <div className="text-xs text-gray-400">{client?.name}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={filing.status} />
                    <Clock size={12} className="text-gray-300" />
                    <span className="text-xs text-gray-400">
                      {filing.updatedAt.slice(0, 10)}
                    </span>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({
  label, value, sub, icon, color, onClick,
}: {
  label: string
  value: number
  sub: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'purple' | 'red'
  onClick?: () => void
}) {
  const bg = { blue: 'bg-blue-50', green: 'bg-green-50', purple: 'bg-purple-50', red: 'bg-red-50' }[color]
  return (
    <div
      className={`card p-4 ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-gray-500 font-medium">{label}</div>
          <div className="text-3xl font-bold text-gray-900 mt-1">{value}</div>
          <div className="text-xs text-gray-400 mt-1">{sub}</div>
        </div>
        <div className={`w-10 h-10 ${bg} rounded-xl flex items-center justify-center`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

export function StatusBadge({ status }: { status: FilingStatus }) {
  const colorMap: Record<FilingStatus, string> = {
    '검토중': 'bg-amber-100 text-amber-700',
    '출원준비': 'bg-blue-100 text-blue-700',
    '출원완료': 'bg-indigo-100 text-indigo-700',
    '심사중': 'bg-violet-100 text-violet-700',
    '등록결정': 'bg-emerald-100 text-emerald-700',
    '등록완료': 'bg-green-100 text-green-700',
    '거절결정': 'bg-red-100 text-red-700',
    '이의신청중': 'bg-orange-100 text-orange-700',
    '포기': 'bg-gray-100 text-gray-500',
  }
  return (
    <span className={`status-badge ${colorMap[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

function EmptyChart() {
  return (
    <div className="h-[220px] flex items-center justify-center text-sm text-gray-400">
      데이터 없음
    </div>
  )
}
