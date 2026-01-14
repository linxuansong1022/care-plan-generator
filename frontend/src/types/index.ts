// Patient types
export interface Patient {
  id: string
  mrn: string
  firstName: string
  lastName: string
  dateOfBirth?: string
  sex?: 'Male' | 'Female' | 'Other'
  weightKg?: number
  allergies?: string
  primaryDiagnosisCode: string
  primaryDiagnosisDescription?: string
}

// Provider types
export interface Provider {
  id: string
  npi: string
  name: string
  phone?: string
  fax?: string
}

// Order types
export type OrderStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface Order {
  id: string
  patient: Patient
  provider: Provider
  medicationName: string
  status: OrderStatus
  hasCarePlan: boolean
  errorMessage?: string
  createdAt: string
  updatedAt: string
}

export interface OrderListItem {
  id: string
  patientMrn: string
  patientName: string
  providerNpi: string
  providerName: string
  medicationName: string
  status: OrderStatus
  hasCarePlan: boolean
  createdAt: string
}

// Form data for creating orders
export interface OrderCreateData {
  // Patient info
  patientMrn: string
  patientFirstName: string
  patientLastName: string
  patientDateOfBirth?: string
  patientSex?: string
  patientWeightKg?: number
  patientAllergies?: string
  
  // Diagnosis
  primaryDiagnosisCode: string
  primaryDiagnosisDescription?: string
  additionalDiagnoses: string[]
  medicationHistory: string[]
  
  // Provider
  providerNpi: string
  providerName: string
  
  // Order
  medicationName: string
  patientRecords: string
  
  // Confirmation
  confirmNotDuplicate?: boolean
}

// Warning type from API
export interface Warning {
  code: string
  message: string
  action_required: boolean
  data?: Record<string, unknown>
}

// API response types
export interface OrderResponse {
  order?: Order
  warnings: Warning[]
  patientWarnings: Warning[]
  providerWarnings: Warning[]
  allWarnings?: Warning[]
  isPotentialDuplicate: boolean
  requiresConfirmation: boolean
  isBlocked?: boolean
  blockingReason?: string
  duplicateOrderId?: string
}

export interface CarePlanStatus {
  orderId: string
  status: OrderStatus
  carePlanAvailable: boolean
  errorMessage?: string
}

export interface CarePlan {
  id: string
  orderId: string
  content: string
  filePath?: string
  llmModel?: string
  generatedAt?: string
}

// Paginated response
export interface PaginatedResponse<T> {
  count: number
  next?: string
  previous?: string
  results: T[]
}
