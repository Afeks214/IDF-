// Authentication types
export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  name: string;
  isActive: boolean;
  lastLogin?: string;
}

export type UserRole = 'admin' | 'manager' | 'tester' | 'viewer';

export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
  rememberMe?: boolean;
}

export interface AuthResponse {
  user: User;
  token: string;
  refreshToken: string;
}

// Building types
export interface Building {
  id: string;
  buildingCode: string;
  buildingName: string;
  managerName: string;
  redTeam: string;
  status: BuildingStatus;
  testsCount?: number;
  lastTestDate?: string;
  createdAt: string;
  updatedAt: string;
}

export type BuildingStatus = 'active' | 'inactive';

export interface CreateBuildingData {
  buildingCode: string;
  buildingName: string;
  managerName: string;
  redTeam: string;
  status?: BuildingStatus;
}

// Test types
export interface TestRecord {
  id: string;
  buildingId: string;
  building?: Building;
  testType: TestType;
  testLeader: string;
  testRound: number;
  testDate: string;
  status: TestStatus;
  results?: string;
  reportDistributed: boolean;
  retestRequired: boolean;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export type TestType = 'engineering' | 'security' | 'safety' | 'operational';
export type TestStatus = 'pending' | 'inProgress' | 'completed' | 'failed';

export interface CreateTestData {
  buildingId: string;
  testType: TestType;
  testLeader: string;
  testRound: number;
  testDate: string;
  notes?: string;
}

export interface UpdateTestData extends Partial<CreateTestData> {
  status?: TestStatus;
  results?: string;
  reportDistributed?: boolean;
  retestRequired?: boolean;
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  timestamp: string;
  pagination?: PaginationInfo;
}

export interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// Filter types
export interface BuildingFilters extends PaginationParams {
  search?: string;
  status?: BuildingStatus;
  managerName?: string;
}

export interface TestFilters extends PaginationParams {
  search?: string;
  buildingId?: string;
  testType?: TestType;
  status?: TestStatus;
  testLeader?: string;
  dateFrom?: string;
  dateTo?: string;
}

// Dashboard types
export interface DashboardStats {
  totalBuildings: number;
  totalTests: number;
  pendingTests: number;
  completedTests: number;
  failedTests: number;
  testsThisMonth: number;
  testsLastMonth: number;
}

export interface TestsByType {
  testType: TestType;
  count: number;
  percentage: number;
}

export interface TestsByStatus {
  status: TestStatus;
  count: number;
  percentage: number;
}

export interface MonthlyTestTrend {
  month: string;
  tests: number;
  completed: number;
  failed: number;
}

export interface DashboardData {
  stats: DashboardStats;
  testsByType: TestsByType[];
  testsByStatus: TestsByStatus[];
  monthlyTrend: MonthlyTestTrend[];
  recentTests: TestRecord[];
}

// Form types
export interface FormError {
  field: string;
  message: string;
}

export interface ApiError {
  message: string;
  errors?: FormError[];
  statusCode?: number;
}

// Theme types
export interface ThemeContextType {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  direction: 'rtl' | 'ltr';
  toggleDirection: () => void;
}

// Navigation types
export interface MenuItem {
  id: string;
  label: string;
  path: string;
  icon?: React.ComponentType;
  children?: MenuItem[];
  roles?: UserRole[];
}

// Report types
export interface ReportFilters {
  dateFrom: string;
  dateTo: string;
  buildingIds?: string[];
  testTypes?: TestType[];
  statuses?: TestStatus[];
}

export interface ReportData {
  filters: ReportFilters;
  buildings: Building[];
  tests: TestRecord[];
  summary: {
    totalTests: number;
    completedTests: number;
    failedTests: number;
    pendingTests: number;
  };
}

export type ExportFormat = 'pdf' | 'excel' | 'csv';

export interface ExportRequest {
  filters: ReportFilters;
  format: ExportFormat;
  filename?: string;
}

// Structure-Specific Competency Management Types

// Structure Types
export interface Structure {
  id: string;
  structureCode: string;
  structureName: string;
  structureType: StructureType;
  location: string;
  managerId: string;
  manager: {
    id: string;
    name: string;
    role: string;
    phone?: string;
    email?: string;
  };
  competencyStatus: CompetencyStatus;
  lastInspectionDate?: string;
  nextInspectionDate?: string;
  totalItems: number;
  completedItems: number;
  pendingVisits: number;
  verified: number;
  createdAt: string;
  updatedAt: string;
}

export type StructureType = 'building' | 'facility' | 'infrastructure' | 'system';
export type CompetencyStatus = 'compliant' | 'partial' | 'non-compliant' | 'pending';

// Inspection Types
export interface Inspection {
  id: string;
  structureId: string;
  structure?: Structure;
  inspectionType: InspectionType;
  status: InspectionStatus;
  responsiblePerson: string;
  responsiblePersonId?: string;
  scheduledDate: string;
  completedDate?: string;
  results?: string;
  notes?: string;
  followUpRequired: boolean;
  nextInspectionDate?: string;
  items: InspectionItem[];
  createdAt: string;
  updatedAt: string;
}

export type InspectionType = 'initial' | 'follow-up' | 'routine' | 'emergency';
export type InspectionStatus = 'scheduled' | 'in-progress' | 'completed' | 'cancelled' | 'requires-follow-up';

// Inspection Item Types
export interface InspectionItem {
  id: string;
  inspectionId: string;
  itemCode: string;
  itemName: string;
  category: ItemCategory;
  itemType: ItemType;
  priority: ItemPriority;
  status: ItemStatus;
  responsiblePerson?: string;
  checkDate?: string;
  verificationDate?: string;
  results?: string;
  notes?: string;
  followUpRequired: boolean;
  dueDate?: string;
  completionEvidence?: string[];
  createdAt: string;
  updatedAt: string;
}

export type ItemCategory = 'safety' | 'security' | 'maintenance' | 'operational' | 'regulatory';
export type ItemType = 'visit' | 'verification' | 'documentation' | 'measurement' | 'test';
export type ItemPriority = 'critical' | 'high' | 'medium' | 'low';
export type ItemStatus = 'pending' | 'in-progress' | 'completed' | 'verified' | 'failed' | 'not-applicable';

// Competency Summary Types
export interface CompetencySummary {
  structureId: string;
  totalRequirements: number;
  completedRequirements: number;
  verifiedRequirements: number;
  pendingVisits: number;
  failedRequirements: number;
  completionPercentage: number;
  verificationPercentage: number;
  overallStatus: CompetencyStatus;
  lastUpdated: string;
  categoryBreakdown: CategorySummary[];
  upcomingDeadlines: InspectionItem[];
  criticalIssues: InspectionItem[];
}

export interface CategorySummary {
  category: ItemCategory;
  total: number;
  completed: number;
  verified: number;
  pending: number;
  failed: number;
  percentage: number;
}

// Data Entry Form Types
export interface InspectionFormData {
  structureId: string;
  inspectionType: InspectionType;
  responsiblePerson: string;
  scheduledDate: string;
  notes?: string;
  items: InspectionItemFormData[];
}

export interface InspectionItemFormData {
  id?: string;
  itemCode: string;
  itemName: string;
  category: ItemCategory;
  itemType: ItemType;
  priority: ItemPriority;
  responsiblePerson?: string;
  results?: string;
  notes?: string;
  followUpRequired: boolean;
  dueDate?: string;
}

// Workflow State Types
export interface WorkflowState {
  inspectionId: string;
  currentStage: WorkflowStage;
  stages: WorkflowStageInfo[];
  canAdvance: boolean;
  canRevert: boolean;
  nextStage?: WorkflowStage;
  previousStage?: WorkflowStage;
  assignedTo?: string;
  dueDate?: string;
}

export type WorkflowStage = 'planning' | 'scheduled' | 'in-progress' | 'review' | 'approval' | 'completed' | 'archived';

export interface WorkflowStageInfo {
  stage: WorkflowStage;
  name: string;
  description: string;
  isCompleted: boolean;
  isActive: boolean;
  completedDate?: string;
  assignedTo?: string;
  requiredActions: string[];
}

// Filter Types for Structure Management
export interface StructureFilters extends PaginationParams {
  search?: string;
  structureType?: StructureType;
  competencyStatus?: CompetencyStatus;
  managerId?: string;
  location?: string;
  hasOverdueItems?: boolean;
}

export interface InspectionFilters extends PaginationParams {
  search?: string;
  structureId?: string;
  inspectionType?: InspectionType;
  status?: InspectionStatus;
  responsiblePerson?: string;
  dateFrom?: string;
  dateTo?: string;
  followUpRequired?: boolean;
}

export interface InspectionItemFilters extends PaginationParams {
  search?: string;
  inspectionId?: string;
  structureId?: string;
  category?: ItemCategory;
  itemType?: ItemType;
  priority?: ItemPriority;
  status?: ItemStatus;
  responsiblePerson?: string;
  overdueOnly?: boolean;
}

// Operations Inspection Module Types

export type OperationalCheckType = 
  | 'structural_inspection'  // בדיקה תפעולית למבנה
  | 'operational_run'        // הרצה תפעולית
  | 'tafam_continuity';      // הרצת תפ"מ ורציפות תפקוד

export type OperationalCheckStatus = 'pending' | 'in_progress' | 'passed' | 'failed' | 'not_applicable';

export interface OperationalCheckItem {
  id: string;
  checkCode: string;
  description: string;
  descriptionHebrew: string;
  checkType: OperationalCheckType;
  isRequired: boolean;
  status: OperationalCheckStatus;
  notes?: string;
  completedAt?: string;
  completedBy?: string;
  evidenceRequired: boolean;
  evidenceFiles?: string[];
}

export interface TafamCheck extends OperationalCheckItem {
  tafamComponent: string;
  continuityTest: boolean;
  functionalTest: boolean;
  performanceMetrics?: {
    responseTime?: number;
    throughput?: number;
    availability?: number;
  };
}

export interface OperationalInspection {
  id: string;
  buildingId: string;
  building?: Building;
  inspectionType: 'operations';
  inspectionSubtype: OperationalCheckType;
  inspectionLeader: string;
  inspectionRound: number;
  scheduledDate: string;
  startedAt?: string;
  completedAt?: string;
  status: TestStatus;
  
  // Checklist items
  structuralChecks: OperationalCheckItem[];
  operationalRunChecks: OperationalCheckItem[];
  tafamChecks: TafamCheck[];
  
  // Progress tracking
  totalChecks: number;
  completedChecks: number;
  passedChecks: number;
  failedChecks: number;
  progressPercentage: number;
  
  // Results and documentation
  overallResult: 'passed' | 'failed' | 'conditional';
  reportPath?: string;
  reportDistributed: boolean;
  followUpRequired: boolean;
  notes?: string;
  
  // Timestamps
  createdAt: string;
  updatedAt: string;
}

export interface CreateOperationalInspectionData {
  buildingId: string;
  inspectionSubtype: OperationalCheckType;
  inspectionLeader: string;
  inspectionRound: number;
  scheduledDate: string;
  notes?: string;
}

export interface UpdateOperationalInspectionData extends Partial<CreateOperationalInspectionData> {
  status?: TestStatus;
  structuralChecks?: OperationalCheckItem[];
  operationalRunChecks?: OperationalCheckItem[];
  tafamChecks?: TafamCheck[];
  overallResult?: 'passed' | 'failed' | 'conditional';
  reportDistributed?: boolean;
  followUpRequired?: boolean;
}

export interface OperationalInspectionFilters extends PaginationParams {
  search?: string;
  buildingId?: string;
  inspectionSubtype?: OperationalCheckType;
  status?: TestStatus;
  inspectionLeader?: string;
  dateFrom?: string;
  dateTo?: string;
  overallResult?: 'passed' | 'failed' | 'conditional';
}

// Operational Checklist Templates
export interface OperationalChecklistTemplate {
  id: string;
  templateName: string;
  templateNameHebrew: string;
  checkType: OperationalCheckType;
  version: string;
  isActive: boolean;
  checkItems: Omit<OperationalCheckItem, 'id' | 'status' | 'completedAt' | 'completedBy' | 'notes' | 'evidenceFiles'>[];
  createdAt: string;
  updatedAt: string;
}