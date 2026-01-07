import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  Loader2,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react'

import { useOrder, useCarePlanStatus, useCarePlan, useRegenerateCarePlan } from '@/hooks/useOrders'
import { carePlanService } from '@/services/orderService'
import { formatDateTime, getStatusColor, cn } from '@/lib/utils'
import { Button } from '@/components/ui/Button'

export function OrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: order, isLoading: orderLoading } = useOrder(id!)
  const { data: status } = useCarePlanStatus(id!)
  const { data: carePlan, isLoading: carePlanLoading } = useCarePlan(id!)
  const regenerate = useRegenerateCarePlan()

  if (orderLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!order) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">Order not found</p>
      </div>
    )
  }

  const handleDownload = () => {
    window.open(carePlanService.getDownloadUrl(id!), '_blank')
  }

  const handleRegenerate = () => {
    regenerate.mutate(id!)
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          to="/orders"
          className="text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h1 className="text-2xl font-bold">Order Details</h1>
        <span
          className={cn(
            'px-3 py-1 rounded-full text-sm font-medium',
            getStatusColor(order.status)
          )}
        >
          {order.status}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Patient Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Patient Information
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-gray-500">Name</dt>
              <dd className="font-medium">
                {order.patient.firstName} {order.patient.lastName}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">MRN</dt>
              <dd className="font-mono">{order.patient.mrn}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Primary Diagnosis</dt>
              <dd className="font-mono">{order.patient.primaryDiagnosisCode}</dd>
            </div>
          </dl>
        </div>

        {/* Provider Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Referring Provider
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-gray-500">Name</dt>
              <dd className="font-medium">{order.provider.name}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">NPI</dt>
              <dd className="font-mono">{order.provider.npi}</dd>
            </div>
          </dl>
        </div>

        {/* Order Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Order Information
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-gray-500">Medication</dt>
              <dd className="font-medium">{order.medicationName}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Created</dt>
              <dd>{formatDateTime(order.createdAt)}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Last Updated</dt>
              <dd>{formatDateTime(order.updatedAt)}</dd>
            </div>
          </dl>
        </div>

        {/* Care Plan Status */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Care Plan
          </h2>

          {status?.status === 'pending' && (
            <div className="flex items-center gap-3 text-yellow-600">
              <Clock className="h-5 w-5" />
              <span>Waiting in queue...</span>
            </div>
          )}

          {status?.status === 'processing' && (
            <div className="flex items-center gap-3 text-blue-600">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Generating care plan...</span>
            </div>
          )}

          {status?.status === 'completed' && status?.carePlanAvailable && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 text-green-600">
                <CheckCircle className="h-5 w-5" />
                <span>Care plan ready</span>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleDownload}>
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
                <Button
                  variant="outline"
                  onClick={handleRegenerate}
                  disabled={regenerate.isPending}
                >
                  <RefreshCw
                    className={cn(
                      'mr-2 h-4 w-4',
                      regenerate.isPending && 'animate-spin'
                    )}
                  />
                  Regenerate
                </Button>
              </div>
            </div>
          )}

          {status?.status === 'failed' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 text-red-600">
                <AlertCircle className="h-5 w-5" />
                <span>Generation failed</span>
              </div>
              {status.errorMessage && (
                <p className="text-sm text-gray-500">{status.errorMessage}</p>
              )}
              <Button
                onClick={handleRegenerate}
                disabled={regenerate.isPending}
              >
                <RefreshCw
                  className={cn(
                    'mr-2 h-4 w-4',
                    regenerate.isPending && 'animate-spin'
                  )}
                />
                Retry
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Care Plan Content */}
      {carePlan && !carePlanLoading && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Care Plan Content
          </h2>
          <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-[600px]">
            <pre className="text-sm whitespace-pre-wrap font-mono">
              {carePlan.content}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
