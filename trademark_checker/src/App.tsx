import { useState, useEffect, useCallback } from 'react'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import FilingManager from './components/FilingManager'
import ClientManager from './components/ClientManager'
import SimilarityCheck from './components/SimilarityCheck'
import SimilarGroupCodeSearch from './components/SimilarGroupCodeSearch'
import CostCalculator from './components/CostCalculator'
import Settings from './components/Settings'
import type { Client, TrademarkFiling, SimilarityCheckReport, AppSettings } from './types'
import {
  MOCK_CLIENTS,
  MOCK_FILINGS,
  MOCK_REPORTS,
} from './data/mockData'
import {
  loadLocalData,
  saveLocalData,
  loadSettings,
  saveSettings,
  buildAppData,
  saveToDrive,
  isGoogleSignedIn,
} from './utils/storage'

export type Page =
  | 'dashboard'
  | 'filings'
  | 'clients'
  | 'similarity'
  | 'similar-codes'
  | 'cost-calculator'
  | 'settings'

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [settings, setSettings] = useState<AppSettings>(loadSettings)

  // 데이터 상태
  const [clients, setClients] = useState<Client[]>([])
  const [filings, setFilings] = useState<TrademarkFiling[]>([])
  const [reports, setReports] = useState<SimilarityCheckReport[]>([])

  // 저장 상태
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [driveFileId, setDriveFileId] = useState<string | undefined>()
  const [lastSavedAt, setLastSavedAt] = useState<string | undefined>()
  const [isMockMode, setIsMockMode] = useState(settings.useMock)

  // 초기 데이터 로드
  useEffect(() => {
    if (isMockMode) {
      setClients(MOCK_CLIENTS)
      setFilings(MOCK_FILINGS)
      setReports(MOCK_REPORTS)
    } else {
      const localData = loadLocalData()
      if (localData) {
        setClients(localData.clients)
        setFilings(localData.filings)
        setReports(localData.reports)
      } else {
        // 로컬에 데이터 없으면 Mock 데이터로 초기화
        setClients(MOCK_CLIENTS)
        setFilings(MOCK_FILINGS)
        setReports(MOCK_REPORTS)
        setIsMockMode(true)
      }
    }
  }, [isMockMode])

  // 저장 함수
  const handleSave = useCallback(async () => {
    setSaveStatus('saving')
    try {
      const appData = buildAppData(clients, filings, reports)

      // 로컬 저장 (항상)
      saveLocalData(appData)

      // 구글 드라이브 저장 (로그인된 경우)
      if (settings.storage.useGoogleDrive && isGoogleSignedIn()) {
        const result = await saveToDrive(
          appData,
          settings.storage.googleDriveFolderId,
          driveFileId,
        )
        setDriveFileId(result.fileId)
      }

      const now = new Date().toLocaleTimeString('ko-KR')
      setLastSavedAt(now)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 5000)
    }
  }, [clients, filings, reports, settings, driveFileId])

  // 자동 저장
  useEffect(() => {
    if (settings.storage.autoSaveInterval <= 0) return
    const interval = setInterval(handleSave, settings.storage.autoSaveInterval * 60 * 1000)
    return () => clearInterval(interval)
  }, [handleSave, settings.storage.autoSaveInterval])

  const handleSettingsChange = (newSettings: AppSettings) => {
    setSettings(newSettings)
    saveSettings(newSettings)
    setIsMockMode(newSettings.useMock)
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return (
          <Dashboard
            clients={clients}
            filings={filings}
            reports={reports}
            isMockMode={isMockMode}
            onNavigate={setCurrentPage}
          />
        )
      case 'filings':
        return (
          <FilingManager
            filings={filings}
            clients={clients}
            onUpdate={setFilings}
          />
        )
      case 'clients':
        return (
          <ClientManager
            clients={clients}
            filings={filings}
            onUpdate={setClients}
          />
        )
      case 'similarity':
        return (
          <SimilarityCheck
            reports={reports}
            filings={filings}
            clients={clients}
            onUpdate={setReports}
          />
        )
      case 'similar-codes':
        return <SimilarGroupCodeSearch />
      case 'cost-calculator':
        return (
          <CostCalculator
            filings={filings}
            onUpdateFiling={(updated) =>
              setFilings(prev => prev.map(f => f.id === updated.id ? updated : f))
            }
          />
        )
      case 'settings':
        return (
          <Settings
            settings={settings}
            onUpdate={handleSettingsChange}
            driveFileId={driveFileId}
            lastSavedAt={lastSavedAt}
            clients={clients}
            filings={filings}
            reports={reports}
          />
        )
      default:
        return null
    }
  }

  return (
    <Layout
      currentPage={currentPage}
      onNavigate={setCurrentPage}
      saveStatus={saveStatus}
      lastSavedAt={lastSavedAt}
      isMockMode={isMockMode}
      onSave={handleSave}
      isGoogleConnected={isGoogleSignedIn()}
      useGoogleDrive={settings.storage.useGoogleDrive}
    >
      {renderPage()}
    </Layout>
  )
}
