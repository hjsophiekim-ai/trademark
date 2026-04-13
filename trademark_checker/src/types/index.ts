// ===== 상표 출원 관련 타입 =====

export type FilingStatus =
  | '검토중'
  | '출원준비'
  | '출원완료'
  | '심사중'
  | '등록결정'
  | '등록완료'
  | '거절결정'
  | '이의신청중'
  | '포기';

export type TrademarkType = '문자' | '도형' | '결합' | '입체' | '색채' | '소리' | '냄새';

export type ApplicantType = '개인' | '법인' | '소상공인' | '중소기업' | '대기업' | '국가/공공기관';

// 유사군 코드
export interface SimilarGroupCode {
  code: string;         // e.g. "G0101"
  class: number;        // 상품류 e.g. 25
  name: string;         // e.g. "의류"
  description: string;
  examples: string[];
}

// 상표 출원 건
export interface TrademarkFiling {
  id: string;
  clientId: string;
  trademarkName: string;       // 상표명
  trademarkType: TrademarkType;
  classes: number[];            // 지정 류 번호들
  similarGroupCodes: string[];  // 유사군 코드들
  goods: string[];              // 지정상품/서비스
  status: FilingStatus;
  applicationNumber?: string;   // 출원번호 e.g. "4020240012345"
  registrationNumber?: string;  // 등록번호
  applicationDate?: string;     // 출원일 (ISO 8601)
  registrationDate?: string;    // 등록일
  expiryDate?: string;          // 만료일
  notes: string;
  priority?: string;            // 우선권 주장
  createdAt: string;
  updatedAt: string;

  // 비용 정보
  costInfo?: FilingCostResult;
}

// 의뢰인
export interface Client {
  id: string;
  name: string;
  type: ApplicantType;
  businessNumber?: string;      // 사업자등록번호
  contact: string;
  email: string;
  phone: string;
  address?: string;
  filingIds: string[];
  createdAt: string;
  updatedAt: string;
}

// 유사 상표 검색 결과
export interface SimilarTrademarkResult {
  applicationNumber: string;
  trademarkName: string;
  applicant: string;
  classes: number[];
  status: string;
  applicationDate: string;
  similarityScore: number;    // 0~100
  similarityReason: string;
}

// 유사성 검토 보고서
export interface SimilarityCheckReport {
  id: string;
  filingId?: string;
  clientId?: string;
  targetTrademark: string;
  targetClasses: number[];
  targetGoods: string;
  searchFormula: string;       // 키프리스 검색식
  results: SimilarTrademarkResult[];
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  opinion: string;             // 검토 의견
  createdAt: string;
}

// ===== 비용 계산 관련 타입 =====

export interface FilingCostInput {
  applicantType: ApplicantType;
  classes: number;              // 출원 류 수
  goodsPerClass: number[];      // 각 류별 지정상품 수
  registrationTerm: 10 | 5;    // 등록료 납부 기간
  isOnline: boolean;            // 전자출원 여부
  includeAttorneyFee: boolean;  // 변리사 수임료 포함 여부
  customAttorneyFeePerClass?: number;
}

export interface FilingCostBreakdown {
  label: string;
  amount: number;
  unit: string;
  detail?: string;
}

export interface FilingCostResult {
  applicationFee: number;       // 출원료
  registrationFee: number;      // 등록료
  attorneyFee: number;          // 변리사 수임료
  totalFee: number;             // 합계
  breakdown: FilingCostBreakdown[];
  discountInfo?: string;
  notes: string[];
}

// ===== 저장 관련 타입 =====

export interface AppData {
  version: string;
  exportedAt: string;
  clients: Client[];
  filings: TrademarkFiling[];
  reports: SimilarityCheckReport[];
}

export interface GoogleDriveFile {
  id: string;
  name: string;
  modifiedTime: string;
  size: string;
}

export interface StorageSettings {
  useGoogleDrive: boolean;
  googleDriveFolderId?: string;
  autoSaveInterval: number;     // minutes, 0 = manual
  lastSyncedAt?: string;
}

// ===== 앱 설정 =====
export interface AppSettings {
  useMock: boolean;
  storage: StorageSettings;
  defaultAttorneyFeePerClass: number;
  kiprisApiKey?: string;
}

// ===== 대시보드 통계 =====
export interface DashboardStats {
  totalFilings: number;
  activeFilings: number;
  registeredCount: number;
  rejectedCount: number;
  pendingCount: number;
  totalClients: number;
  totalRevenue: number;
  recentActivity: ActivityItem[];
  statusDistribution: { status: FilingStatus; count: number }[];
  monthlyFilings: { month: string; count: number }[];
}

export interface ActivityItem {
  id: string;
  type: 'filing_created' | 'status_changed' | 'client_added' | 'report_created';
  description: string;
  timestamp: string;
}
