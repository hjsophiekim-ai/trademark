import type { AppData, AppSettings, StorageSettings } from '../types'
import type { Client, TrademarkFiling, SimilarityCheckReport } from '../types'

const STORAGE_KEY = 'trademark_checker_data'
const SETTINGS_KEY = 'trademark_checker_settings'

// ===== 로컬 스토리지 (브라우저 LocalStorage) =====

export function loadLocalData(): AppData | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as AppData
  } catch {
    return null
  }
}

export function saveLocalData(data: AppData): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return getDefaultSettings()
    return JSON.parse(raw) as AppSettings
  } catch {
    return getDefaultSettings()
  }
}

export function saveSettings(settings: AppSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
}

function getDefaultSettings(): AppSettings {
  return {
    useMock: import.meta.env.VITE_USE_MOCK === 'true',
    storage: {
      useGoogleDrive: false,
      autoSaveInterval: 30,
    },
    defaultAttorneyFeePerClass: 330_000,
    kiprisApiKey: undefined,
  }
}

// ===== JSON 파일 다운로드 (로컬 폴더 저장) =====

export function downloadAsJson(data: AppData, filename?: string): void {
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const now = new Date()
  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '')
  a.href = url
  a.download = filename ?? `trademark_data_${dateStr}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ===== 구글 드라이브 API =====

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string
const SCOPES = 'https://www.googleapis.com/auth/drive.file'
const DRIVE_API = 'https://www.googleapis.com/drive/v3'
const UPLOAD_API = 'https://www.googleapis.com/upload/drive/v3'

let googleAccessToken: string | null = null

// Google OAuth2 로그인
export async function googleSignIn(): Promise<string> {
  return new Promise((resolve, reject) => {
    const params = new URLSearchParams({
      client_id: GOOGLE_CLIENT_ID,
      redirect_uri: window.location.origin + '/oauth-callback',
      response_type: 'token',
      scope: SCOPES,
    })
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params}`

    // 팝업으로 OAuth 진행
    const popup = window.open(authUrl, 'google_auth', 'width=500,height=600')
    if (!popup) {
      reject(new Error('팝업이 차단되었습니다. 브라우저 팝업을 허용해주세요.'))
      return
    }

    const checkClosed = setInterval(() => {
      try {
        if (popup.closed) {
          clearInterval(checkClosed)
          // 팝업 닫힘 - 토큰을 sessionStorage에서 확인
          const token = sessionStorage.getItem('google_access_token')
          if (token) {
            googleAccessToken = token
            sessionStorage.removeItem('google_access_token')
            resolve(token)
          } else {
            reject(new Error('구글 로그인이 취소되었습니다.'))
          }
        }
        // 팝업 URL 체크 (같은 오리진일 때)
        const hash = popup.location.hash
        if (hash) {
          const params = new URLSearchParams(hash.substring(1))
          const token = params.get('access_token')
          if (token) {
            googleAccessToken = token
            popup.close()
            clearInterval(checkClosed)
            resolve(token)
          }
        }
      } catch {
        // 크로스 오리진 에러 무시 (정상)
      }
    }, 500)
  })
}

export function setGoogleAccessToken(token: string) {
  googleAccessToken = token
}

export function getGoogleAccessToken(): string | null {
  return googleAccessToken
}

export function isGoogleSignedIn(): boolean {
  return !!googleAccessToken
}

// 구글 드라이브에 파일 저장/업데이트
export async function saveToDrive(
  data: AppData,
  folderId?: string,
  existingFileId?: string,
): Promise<{ fileId: string; webViewLink: string }> {
  if (!googleAccessToken) throw new Error('구글 로그인이 필요합니다')

  const filename = 'trademark_data.json'
  const content = JSON.stringify(data, null, 2)
  const blob = new Blob([content], { type: 'application/json' })

  const metadata: Record<string, unknown> = {
    name: filename,
    mimeType: 'application/json',
  }
  if (folderId) metadata.parents = [folderId]

  const form = new FormData()
  form.append('metadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }))
  form.append('file', blob)

  let url: string
  let method: string

  if (existingFileId) {
    // 업데이트
    url = `${UPLOAD_API}/files/${existingFileId}?uploadType=multipart`
    method = 'PATCH'
    // 업데이트 시 parents 불필요
    delete metadata.parents
  } else {
    // 신규 생성
    url = `${UPLOAD_API}/files?uploadType=multipart`
    method = 'POST'
  }

  const res = await fetch(url, {
    method,
    headers: { Authorization: `Bearer ${googleAccessToken}` },
    body: form,
  })

  if (!res.ok) {
    const err = await res.json()
    throw new Error(`구글 드라이브 저장 실패: ${err.error?.message ?? res.statusText}`)
  }

  const file = await res.json()

  // webViewLink 조회
  const metaRes = await fetch(
    `${DRIVE_API}/files/${file.id}?fields=id,name,webViewLink,modifiedTime`,
    { headers: { Authorization: `Bearer ${googleAccessToken}` } },
  )
  const meta = await metaRes.json()

  return { fileId: file.id, webViewLink: meta.webViewLink ?? '' }
}

// 구글 드라이브에서 파일 목록 조회
export async function listDriveFiles(folderId?: string): Promise<{
  id: string; name: string; modifiedTime: string; size: string
}[]> {
  if (!googleAccessToken) throw new Error('구글 로그인이 필요합니다')

  let q = "name contains 'trademark' and mimeType='application/json' and trashed=false"
  if (folderId) q += ` and '${folderId}' in parents`

  const params = new URLSearchParams({
    q,
    fields: 'files(id,name,modifiedTime,size)',
    orderBy: 'modifiedTime desc',
  })

  const res = await fetch(`${DRIVE_API}/files?${params}`, {
    headers: { Authorization: `Bearer ${googleAccessToken}` },
  })

  if (!res.ok) throw new Error('파일 목록 조회 실패')
  const data = await res.json()
  return data.files ?? []
}

// 구글 드라이브에서 파일 읽기
export async function loadFromDrive(fileId: string): Promise<AppData> {
  if (!googleAccessToken) throw new Error('구글 로그인이 필요합니다')

  const res = await fetch(`${DRIVE_API}/files/${fileId}?alt=media`, {
    headers: { Authorization: `Bearer ${googleAccessToken}` },
  })

  if (!res.ok) throw new Error('파일 읽기 실패')
  return res.json()
}

// ===== 통합 저장 (로컬 + 드라이브 동시) =====

export async function saveDataEverywhere(
  data: AppData,
  settings: StorageSettings,
  driveFileId?: string,
): Promise<{
  localSaved: boolean
  driveSaved: boolean
  driveFileId?: string
  driveLink?: string
  error?: string
}> {
  const result = {
    localSaved: false,
    driveSaved: false,
    driveFileId: undefined as string | undefined,
    driveLink: undefined as string | undefined,
    error: undefined as string | undefined,
  }

  // 1. 로컬 저장 (항상)
  try {
    saveLocalData(data)
    result.localSaved = true
  } catch (e) {
    result.error = `로컬 저장 실패: ${e}`
  }

  // 2. 구글 드라이브 저장 (설정 시)
  if (settings.useGoogleDrive && isGoogleSignedIn()) {
    try {
      const driveResult = await saveToDrive(
        data,
        settings.googleDriveFolderId,
        driveFileId,
      )
      result.driveSaved = true
      result.driveFileId = driveResult.fileId
      result.driveLink = driveResult.webViewLink
    } catch (e) {
      result.error = (result.error ? result.error + ' / ' : '') + `드라이브 저장 실패: ${e}`
    }
  }

  return result
}

// ===== AppData 빌더 =====
export function buildAppData(
  clients: Client[],
  filings: TrademarkFiling[],
  reports: SimilarityCheckReport[],
): AppData {
  return {
    version: '1.0.0',
    exportedAt: new Date().toISOString(),
    clients,
    filings,
    reports,
  }
}
