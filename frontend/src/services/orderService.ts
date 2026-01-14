import api from './api'
import type {
  Order,
  OrderListItem,
  OrderCreateData,
  OrderResponse,
  PaginatedResponse,
  CarePlanStatus,
  CarePlan,
} from '@/types'

/**
 * Transform snake_case to camelCase
 */
function transformOrder(data: Record<string, unknown>): Order {
  return {
    id: data.id as string,
    patient: {
      id: (data.patient as Record<string, unknown>)?.id as string,
      mrn: (data.patient as Record<string, unknown>)?.mrn as string,
      firstName: (data.patient as Record<string, unknown>)?.first_name as string,
      lastName: (data.patient as Record<string, unknown>)?.last_name as string,
      primaryDiagnosisCode: (data.patient as Record<string, unknown>)?.primary_diagnosis_code as string,
    },
    provider: {
      id: (data.provider as Record<string, unknown>)?.id as string,
      npi: (data.provider as Record<string, unknown>)?.npi as string,
      name: (data.provider as Record<string, unknown>)?.name as string,
    },
    medicationName: data.medication_name as string,
    status: data.status as Order['status'],
    hasCarePlan: data.has_care_plan as boolean,
    errorMessage: data.error_message as string | undefined,
    createdAt: data.created_at as string,
    updatedAt: data.updated_at as string,
  }
}

function transformOrderListItem(data: Record<string, unknown>): OrderListItem {
  return {
    id: data.id as string,
    patientMrn: data.patient_mrn as string,
    patientName: data.patient_name as string,
    providerNpi: data.provider_npi as string,
    providerName: data.provider_name as string,
    medicationName: data.medication_name as string,
    status: data.status as OrderListItem['status'],
    hasCarePlan: data.has_care_plan as boolean,
    createdAt: data.created_at as string,
  }
}

export const orderService = {
  /**
   * Create a new order
   */
  async createOrder(
    data: OrderCreateData & { confirmNotDuplicate?: boolean }
  ): Promise<OrderResponse> {
    // Transform camelCase to snake_case
    const payload = {
      patient_mrn: data.patientMrn,
      patient_first_name: data.patientFirstName,
      patient_last_name: data.patientLastName,
      patient_date_of_birth: data.patientDateOfBirth || null,
      patient_sex: data.patientSex || null,
      patient_weight_kg: data.patientWeightKg || null,
      patient_allergies: data.patientAllergies || null,
      primary_diagnosis_code: data.primaryDiagnosisCode,
      primary_diagnosis_description: data.primaryDiagnosisDescription || null,
      additional_diagnoses: data.additionalDiagnoses,
      medication_history: data.medicationHistory,
      provider_npi: data.providerNpi,
      provider_name: data.providerName,
      medication_name: data.medicationName,
      patient_records: data.patientRecords,
      confirm_not_duplicate: data.confirmNotDuplicate || false,
    }

    const response = await api.post('/orders/', payload)

    const warnings = response.data.warnings || []
    const patientWarnings = response.data.patient_warnings || []
    const providerWarnings = response.data.provider_warnings || []

    return {
      order: response.data.order ? transformOrder(response.data.order) : undefined,
      warnings,
      patientWarnings,
      providerWarnings,
      allWarnings: warnings,  // warnings already contains all warnings
      isPotentialDuplicate: response.data.is_potential_duplicate || false,
      requiresConfirmation: response.data.requires_confirmation || false,
      isBlocked: response.data.is_blocked || false,
      blockingReason: response.data.blocking_reason,
      duplicateOrderId: response.data.duplicate_order_id,
    }
  },

  /**
   * Get paginated list of orders
   */
  async getOrders(params?: {
    page?: number
    status?: string
    providerNpi?: string
    patientMrn?: string
  }): Promise<PaginatedResponse<OrderListItem>> {
    const response = await api.get('/orders/', {
      params: {
        page: params?.page,
        status: params?.status,
        provider_npi: params?.providerNpi,
        patient_mrn: params?.patientMrn,
      },
    })

    return {
      count: response.data.count,
      next: response.data.next,
      previous: response.data.previous,
      results: response.data.results.map(transformOrderListItem),
    }
  },

  /**
   * Get single order by ID
   */
  async getOrder(orderId: string): Promise<Order> {
    const response = await api.get(`/orders/${orderId}/`)
    return transformOrder(response.data)
  },

  /**
   * Regenerate care plan for an order
   */
  async regenerateCarePlan(orderId: string): Promise<void> {
    await api.post(`/orders/${orderId}/regenerate/`)
  },
}

export const carePlanService = {
  /**
   * Get care plan status
   */
  async getStatus(orderId: string): Promise<CarePlanStatus> {
    const response = await api.get(`/care-plans/status/${orderId}/`)
    return {
      orderId: response.data.order_id,
      status: response.data.status,
      carePlanAvailable: response.data.care_plan_available,
      errorMessage: response.data.error_message,
    }
  },

  /**
   * Get care plan content
   */
  async getCarePlan(orderId: string): Promise<CarePlan> {
    const response = await api.get(`/care-plans/by-order/${orderId}/`)
    return {
      id: response.data.id,
      orderId: response.data.order_id,
      content: response.data.content,
      filePath: response.data.file_path,
      llmModel: response.data.llm_model,
      generatedAt: response.data.generated_at,
    }
  },

  /**
   * Get download URL for care plan
   */
  getDownloadUrl(orderId: string): string {
    const baseUrl = import.meta.env.VITE_API_URL || '/api/v1'
    return `${baseUrl}/care-plans/download/${orderId}/`
  },
}

export const exportService = {
  /**
   * Get export URL for all orders with care plans
   */
  getExportUrl(): string {
    const baseUrl = import.meta.env.VITE_API_URL || '/api/v1'
    return `${baseUrl}/export/`
  },

  /**
   * Trigger CSV download
   */
  downloadExport(): void {
    const url = this.getExportUrl()
    window.open(url, '_blank')
  },
}
