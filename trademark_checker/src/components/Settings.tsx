import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, ReactNode } from 'react'
import {
  Cloud,
  DownloadCloud,
  Download,
  FolderSync,
  HardDrive,
  RefreshCw,
  Save,
  Settings2,
  Upload,
  UploadCloud,
} from 'lucide-react'
import type { AppData, AppSettings, Client, GoogleDriveFile, SimilarityCheckReport, TrademarkFiling } from '../types'
import {
  buildAppData,
  downloadAsJson,
  googleSignIn,
  isGoogleSignedIn,
  listDriveFiles,
  loadFromDrive,
  saveLocalData,
} from '../utils/storage'

interface SettingsProps {
  settings: AppSettings
  onUpdate: (settings: AppSettings) => void
  driveFileId?: string
  lastSavedAt?: string
  clients: Client[]
  filings: TrademarkFiling[]
  reports: SimilarityCheckReport[]
}

const AUTO_SAVE_OPTIONS = [
  { value: 0, label: '수동 저장만' },
  { value: 5, label: '5분' },
  { value: 15, label: '15분' },
  { value: 30, label: '30분' },
  { value: 60, label: '60분' },
] as const

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

export default function Settings({
  settings,
  onUpdate,
  driveFileId,
  lastSavedAt,
  clients,
  filings,
  reports,
}: SettingsProps) {
  const [draft, setDraft] = useState<AppSettings>(settings)
  const [notice, setNotice] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [isConnectingDrive, setIsConnectingDrive] = useState(false)
  const [isRefreshingFiles, setIsRefreshingFiles] = useState(false)
  const [isRestoringFileId, setIsRestoringFileId] = useState<string>()
  const [driveFiles, setDriveFiles] = useState<GoogleDriveFile[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setDraft(settings)
  }, [settings])

  const appData = buildAppData(clients, filings, reports)
  const googleReady = Boolean(GOOGLE_CLIENT_ID)
  const googleConnected = isGoogleSignedIn()

  const updateDraft = (next: AppSettings) => {
    setDraft(next)
    setNotice('')
    setError('')
  }

  const handleSaveSettings = () => {
    onUpdate(draft)
    setNotice('설정을 저장했습니다.')
    setError('')
  }

  const handleExport = () => {
    downloadAsJson(appData)
    setNotice('현재 데이터를 JSON으로 내보냈습니다.')
    setError('')
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const isValidAppData = (value: unknown): value is AppData => {
    if (!value || typeof value !== 'object') return false
    const data = value as Partial<AppData>
    return Array.isArray(data.clients) && Array.isArray(data.filings) && Array.isArray(data.reports)
  }

  const handleImportFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const parsed: unknown = JSON.parse(text)
      if (!isValidAppData(parsed)) {
        throw new Error('지원하지 않는 데이터 형식입니다.')
      }

      saveLocalData(parsed)
      setNotice('데이터를 가져왔습니다. 화면을 새로고침합니다.')
      setError('')
      window.location.reload()
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : '데이터 가져오기에 실패했습니다.')
      setNotice('')
    } finally {
      event.target.value = ''
    }
  }

  const handleGoogleConnect = async () => {
    if (!googleReady) {
      setError('VITE_GOOGLE_CLIENT_ID가 설정되지 않아 Google Drive를 연결할 수 없습니다.')
      setNotice('')
      return
    }

    try {
      setIsConnectingDrive(true)
      await googleSignIn()
      setNotice('Google Drive 연결이 완료되었습니다.')
      setError('')
    } catch (connectError) {
      setError(connectError instanceof Error ? connectError.message : 'Google Drive 연결에 실패했습니다.')
      setNotice('')
    } finally {
      setIsConnectingDrive(false)
    }
  }

  const handleRefreshDriveFiles = async () => {
    try {
      setIsRefreshingFiles(true)
      const files = await listDriveFiles(draft.storage.googleDriveFolderId)
      setDriveFiles(files)
      setNotice(files.length > 0 ? 'Drive 백업 목록을 불러왔습니다.' : '불러올 Drive 백업이 없습니다.')
      setError('')
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : 'Drive 백업 목록 조회에 실패했습니다.')
      setNotice('')
    } finally {
      setIsRefreshingFiles(false)
    }
  }

  const handleRestoreFromDrive = async (fileId: string) => {
    const shouldRestore = window.confirm('선택한 Drive 백업으로 로컬 데이터를 덮어쓸까요?')
    if (!shouldRestore) return

    try {
      setIsRestoringFileId(fileId)
      const data = await loadFromDrive(fileId)
      saveLocalData(data)
      setNotice('Drive 백업을 복원했습니다. 화면을 새로고침합니다.')
      setError('')
      window.location.reload()
    } catch (restoreError) {
      setError(restoreError instanceof Error ? restoreError.message : 'Drive 백업 복원에 실패했습니다.')
      setNotice('')
    } finally {
      setIsRestoringFileId(undefined)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Settings2 size={24} className="text-blue-600" />
            설정
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            저장 방식, 기본 계산값, 데이터 백업을 한 곳에서 관리합니다.
          </p>
        </div>
        <button onClick={handleSaveSettings} className="btn-primary flex items-center gap-1.5">
          <Save size={14} />
          설정 저장
        </button>
      </div>

      {notice && (
        <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {notice}
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <section className="card p-5 space-y-5">
            <div>
              <h2 className="font-semibold text-gray-900">앱 동작</h2>
              <p className="text-xs text-gray-500 mt-1">현재 UI와 자동 저장 동작에 바로 반영됩니다.</p>
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={draft.useMock}
                onChange={event => updateDraft({ ...draft, useMock: event.target.checked })}
                className="w-4 h-4 mt-0.5 accent-blue-600"
              />
              <div>
                <div className="text-sm font-medium text-gray-800">Mock 데이터 모드 사용</div>
                <div className="text-xs text-gray-500 mt-1">
                  켜면 예시 고객/출원/리포트 데이터로 앱을 시작합니다.
                </div>
              </div>
            </label>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">자동 저장 간격</label>
                <select
                  className="input-field"
                  value={draft.storage.autoSaveInterval}
                  onChange={event =>
                    updateDraft({
                      ...draft,
                      storage: {
                        ...draft.storage,
                        autoSaveInterval: Number(event.target.value),
                      },
                    })
                  }
                >
                  {AUTO_SAVE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">기본 변리사 수수료</label>
                <input
                  type="number"
                  min={0}
                  step={10000}
                  value={draft.defaultAttorneyFeePerClass}
                  onChange={event =>
                    updateDraft({
                      ...draft,
                      defaultAttorneyFeePerClass: Number(event.target.value),
                    })
                  }
                  className="input-field"
                />
                <p className="text-xs text-gray-400 mt-1">비용 계산기의 클래스당 기본 입력값으로 사용됩니다.</p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">KIPRIS API Key</label>
              <input
                type="password"
                value={draft.kiprisApiKey ?? ''}
                onChange={event =>
                  updateDraft({
                    ...draft,
                    kiprisApiKey: event.target.value.trim() || undefined,
                  })
                }
                className="input-field"
                placeholder="프런트엔드 로컬 설정용"
              />
              <p className="text-xs text-gray-400 mt-1">
                현재 프런트엔드 내부에만 저장됩니다. 서버 `.env` 파일은 건드리지 않습니다.
              </p>
            </div>
          </section>

          <section className="card p-5 space-y-5">
            <div>
              <h2 className="font-semibold text-gray-900">Google Drive 백업</h2>
              <p className="text-xs text-gray-500 mt-1">기존 저장 기능과 연동되는 옵션만 노출합니다.</p>
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={draft.storage.useGoogleDrive}
                onChange={event =>
                  updateDraft({
                    ...draft,
                    storage: {
                      ...draft.storage,
                      useGoogleDrive: event.target.checked,
                    },
                  })
                }
                className="w-4 h-4 mt-0.5 accent-blue-600"
              />
              <div>
                <div className="text-sm font-medium text-gray-800">저장 시 Google Drive 동기화 사용</div>
                <div className="text-xs text-gray-500 mt-1">
                  수동 저장 또는 자동 저장 시 Drive 연결이 되어 있으면 함께 업로드합니다.
                </div>
              </div>
            </label>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Drive 폴더 ID</label>
              <input
                type="text"
                value={draft.storage.googleDriveFolderId ?? ''}
                onChange={event =>
                  updateDraft({
                    ...draft,
                    storage: {
                      ...draft.storage,
                      googleDriveFolderId: event.target.value.trim() || undefined,
                    },
                  })
                }
                className="input-field"
                placeholder="선택 입력"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleGoogleConnect}
                disabled={isConnectingDrive}
                className="btn-secondary flex items-center gap-1.5"
              >
                <Cloud size={14} />
                {isConnectingDrive ? '연결 중...' : googleConnected ? 'Drive 재연결' : 'Drive 연결'}
              </button>
              <button
                onClick={handleRefreshDriveFiles}
                disabled={!googleConnected || isRefreshingFiles}
                className="btn-secondary flex items-center gap-1.5"
              >
                <RefreshCw size={14} className={isRefreshingFiles ? 'animate-spin' : ''} />
                백업 목록 새로고침
              </button>
            </div>

            <div className="rounded-xl bg-gray-50 border border-gray-200 p-4 text-sm text-gray-600 space-y-1">
              <div>Google Client ID: {googleReady ? '설정됨' : '없음'}</div>
              <div>연결 상태: {googleConnected ? '연결됨' : '미연결'}</div>
              <div>현재 Drive 파일 ID: {driveFileId ?? '-'}</div>
            </div>

            {driveFiles.length > 0 && (
              <div className="space-y-3">
                {driveFiles.map(file => (
                  <div
                    key={file.id}
                    className="rounded-xl border border-gray-200 px-4 py-3 flex items-center justify-between gap-4"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">{file.name}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        수정: {new Date(file.modifiedTime).toLocaleString('ko-KR')}
                        {' · '}
                        크기: {file.size ? `${Number(file.size).toLocaleString('ko-KR')} bytes` : '-'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleRestoreFromDrive(file.id)}
                      disabled={isRestoringFileId === file.id}
                      className="btn-secondary whitespace-nowrap flex items-center gap-1.5"
                    >
                      <DownloadCloud size={14} />
                      {isRestoringFileId === file.id ? '복원 중...' : '이 백업 복원'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card p-5 space-y-4">
            <div>
              <h2 className="font-semibold text-gray-900">데이터 관리</h2>
              <p className="text-xs text-gray-500 mt-1">현재 로컬 데이터 백업과 복원을 수행합니다.</p>
            </div>

            <div className="flex flex-wrap gap-2">
              <button onClick={handleExport} className="btn-secondary flex items-center gap-1.5">
                <Download size={14} />
                JSON 내보내기
              </button>
              <button onClick={handleImportClick} className="btn-secondary flex items-center gap-1.5">
                <Upload size={14} />
                JSON 가져오기
              </button>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={handleImportFile}
            />

            <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-800">
              가져오기는 현재 로컬 저장 데이터를 덮어씁니다. 서버 파일이나 배포 설정은 변경하지 않습니다.
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="card p-5 space-y-4">
            <h2 className="font-semibold text-gray-900">현재 상태</h2>
            <StatusRow
              icon={<HardDrive size={14} className="text-slate-500" />}
              label="로컬 고객 수"
              value={`${clients.length}건`}
            />
            <StatusRow
              icon={<FolderSync size={14} className="text-blue-500" />}
              label="출원 수"
              value={`${filings.length}건`}
            />
            <StatusRow
              icon={<UploadCloud size={14} className="text-emerald-500" />}
              label="리포트 수"
              value={`${reports.length}건`}
            />
            <StatusRow
              icon={<Save size={14} className="text-amber-500" />}
              label="마지막 저장"
              value={lastSavedAt ?? '-'}
            />
          </section>

          <section className="card p-5 space-y-4">
            <h2 className="font-semibold text-gray-900">내보내기 미리보기</h2>
            <div className="rounded-xl bg-gray-50 border border-gray-200 p-4 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-gray-500">버전</span>
                <span className="font-medium text-gray-900">{appData.version}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-gray-500">생성 시각</span>
                <span className="font-medium text-gray-900">
                  {new Date(appData.exportedAt).toLocaleString('ko-KR')}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-gray-500">총 레코드</span>
                <span className="font-medium text-gray-900">
                  {(clients.length + filings.length + reports.length).toLocaleString('ko-KR')}건
                </span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function StatusRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl bg-gray-50 border border-gray-200 px-4 py-3">
      <div className="flex items-center gap-2 text-sm text-gray-600">
        {icon}
        <span>{label}</span>
      </div>
      <span className="text-sm font-semibold text-gray-900">{value}</span>
    </div>
  )
}
