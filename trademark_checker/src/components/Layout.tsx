import type { ReactNode } from 'react'
import {
  LayoutDashboard, FileText, Users, Search, Tag, Calculator,
  Settings, Save, Cloud, CloudOff, Database, CheckCircle, AlertCircle, Loader2,
} from 'lucide-react'
import type { Page } from '../App'

interface LayoutProps {
  children: ReactNode
  currentPage: Page
  onNavigate: (page: Page) => void
  saveStatus: 'idle' | 'saving' | 'saved' | 'error'
  lastSavedAt?: string
  isMockMode: boolean
  onSave: () => void
  isGoogleConnected: boolean
  useGoogleDrive: boolean
}

const NAV_ITEMS: { id: Page; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: '대시보드', icon: LayoutDashboard },
  { id: 'filings', label: '출원 관리', icon: FileText },
  { id: 'clients', label: '의뢰인 관리', icon: Users },
  { id: 'similarity', label: '유사성 검토', icon: Search },
  { id: 'similar-codes', label: '유사군 코드', icon: Tag },
  { id: 'cost-calculator', label: '출원 비용 계산', icon: Calculator },
  { id: 'settings', label: '설정', icon: Settings },
]

export default function Layout({
  children,
  currentPage,
  onNavigate,
  saveStatus,
  lastSavedAt,
  isMockMode,
  onSave,
  isGoogleConnected,
  useGoogleDrive,
}: LayoutProps) {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* 사이드바 */}
      <aside className="w-60 bg-slate-900 text-white flex flex-col shrink-0">
        {/* 로고 */}
        <div className="px-5 py-5 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              TM
            </div>
            <div>
              <div className="font-semibold text-sm leading-tight">상표 관리</div>
              <div className="text-xs text-slate-400 leading-tight">대시보드</div>
            </div>
          </div>
        </div>

        {/* Mock 모드 배너 */}
        {isMockMode && (
          <div className="mx-3 mt-3 px-3 py-1.5 bg-amber-900/50 border border-amber-700 rounded-lg">
            <div className="flex items-center gap-1.5">
              <Database size={12} className="text-amber-400 shrink-0" />
              <span className="text-xs text-amber-300 font-medium">Mock 데이터 모드</span>
            </div>
          </div>
        )}

        {/* 네비게이션 */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon
            const isActive = currentPage === item.id
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon size={16} />
                {item.label}
              </button>
            )
          })}
        </nav>

        {/* 저장 상태 */}
        <div className="px-4 py-4 border-t border-slate-700">
          <button
            onClick={onSave}
            disabled={saveStatus === 'saving'}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-slate-200 transition-colors disabled:opacity-50"
          >
            {saveStatus === 'saving' ? (
              <Loader2 size={14} className="animate-spin" />
            ) : saveStatus === 'saved' ? (
              <CheckCircle size={14} className="text-green-400" />
            ) : saveStatus === 'error' ? (
              <AlertCircle size={14} className="text-red-400" />
            ) : (
              <Save size={14} />
            )}
            <span>
              {saveStatus === 'saving' ? '저장 중...' :
               saveStatus === 'saved' ? '저장 완료' :
               saveStatus === 'error' ? '저장 실패' : '저장하기'}
            </span>
          </button>

          {/* 저장 위치 표시 */}
          <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
            <div className="flex items-center gap-1">
              <CheckCircle size={10} className="text-green-500" />
              <span>로컬</span>
            </div>
            {useGoogleDrive && (
              <div className="flex items-center gap-1">
                {isGoogleConnected ? (
                  <>
                    <Cloud size={10} className="text-blue-400" />
                    <span className="text-blue-400">드라이브</span>
                  </>
                ) : (
                  <>
                    <CloudOff size={10} className="text-slate-500" />
                    <span>드라이브 미연결</span>
                  </>
                )}
              </div>
            )}
          </div>

          {lastSavedAt && (
            <div className="mt-1 text-xs text-slate-600">마지막 저장: {lastSavedAt}</div>
          )}
        </div>
      </aside>

      {/* 메인 콘텐츠 */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
