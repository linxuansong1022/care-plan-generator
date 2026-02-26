import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { orderService, carePlanService } from '@/services/orderService'
import type { OrderCreateData, OrderResponse } from '@/types'

/**
 * Hook for creating orders
 */
export function useCreateOrder() {
  const queryClient = useQueryClient()

  return useMutation<
    OrderResponse,
    Error,
    OrderCreateData & { confirmNotDuplicate?: boolean }
  >({
    mutationFn: (data) => orderService.createOrder(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

/**
 * Hook for fetching orders list
 */
export function useOrders(params?: {
  page?: number
  status?: string
  providerNpi?: string
  patientMrn?: string
}) {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => orderService.getOrders(params),
  })
}

/**
 * Hook for fetching single order
 */
export function useOrder(orderId: string) {
  return useQuery({
    queryKey: ['orders', orderId],
    queryFn: () => orderService.getOrder(orderId),
    enabled: !!orderId,
  })
}

/**
 * Hook for regenerating care plan
 */
export function useRegenerateCarePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (orderId: string) => orderService.regenerateCarePlan(orderId),
    onSuccess: (_, orderId) => {
      queryClient.invalidateQueries({ queryKey: ['orders', orderId] })
      queryClient.invalidateQueries({ queryKey: ['carePlanStatus', orderId] })
    },
  })
}

/**
 * Hook for fetching care plan status with polling
 */
export function useCarePlanStatus(orderId: string) {
  return useQuery({
    queryKey: ['carePlanStatus', orderId],
    queryFn: () => carePlanService.getStatus(orderId),
    enabled: !!orderId,
    refetchInterval: (query) => {
      const data = query.state.data
      // Poll while pending or processing
      if (data?.status === 'pending' || data?.status === 'processing') {
        return 3000 // Poll every 3 seconds
      }
      return false // Stop polling
    },
  })
}

/**
 * Hook for fetching care plan content
 */
export function useCarePlan(orderId: string) {
  return useQuery({
    queryKey: ['carePlan', orderId],
    queryFn: () => carePlanService.getCarePlan(orderId),
    enabled: !!orderId,
  })
}

/**
 * Hook for uploading a custom care plan
 */
export function useUploadCarePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ orderId, content }: { orderId: string; content: string }) =>
      carePlanService.uploadCarePlan(orderId, content),
    onSuccess: (_, { orderId }) => {
      queryClient.invalidateQueries({ queryKey: ['orders', orderId] })
      queryClient.invalidateQueries({ queryKey: ['carePlanStatus', orderId] })
      queryClient.invalidateQueries({ queryKey: ['carePlan', orderId] })
    },
  })
}

/**
 * Hook for uploading a care plan file
 */
export function useUploadCarePlanFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ orderId, file }: { orderId: string; file: File }) =>
      carePlanService.uploadCarePlanFile(orderId, file),
    onSuccess: (_, { orderId }) => {
      queryClient.invalidateQueries({ queryKey: ['orders', orderId] })
      queryClient.invalidateQueries({ queryKey: ['carePlanStatus', orderId] })
      queryClient.invalidateQueries({ queryKey: ['carePlan', orderId] })
    },
  })
}
