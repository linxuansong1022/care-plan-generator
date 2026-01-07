import { Link } from 'react-router-dom'
import { FileText, Loader2 } from 'lucide-react'

import { useOrders } from '@/hooks/useOrders'
import { formatDateTime, getStatusColor } from '@/lib/utils'
import { cn } from '@/lib/utils'

export function OrdersPage() {
  const { data, isLoading, isError, error } = useOrders()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">
          Error loading orders: {(error as Error)?.message}
        </p>
      </div>
    )
  }

  const orders = data?.results || []

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Orders</h1>
        <Link
          to="/"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          New Order
        </Link>
      </div>

      {orders.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500 mb-4">No orders yet</p>
          <Link
            to="/"
            className="text-blue-600 hover:underline"
          >
            Create your first order
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Patient
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Provider
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Medication
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Care Plan
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {orders.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link
                      to={`/orders/${order.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {order.patientName}
                    </Link>
                    <p className="text-sm text-gray-500">MRN: {order.patientMrn}</p>
                  </td>
                  <td className="px-6 py-4">
                    <p>{order.providerName}</p>
                    <p className="text-sm text-gray-500">NPI: {order.providerNpi}</p>
                  </td>
                  <td className="px-6 py-4">{order.medicationName}</td>
                  <td className="px-6 py-4">
                    <span
                      className={cn(
                        'px-2 py-1 rounded-full text-xs font-medium',
                        getStatusColor(order.status)
                      )}
                    >
                      {order.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDateTime(order.createdAt)}
                  </td>
                  <td className="px-6 py-4">
                    {order.hasCarePlan ? (
                      <span className="text-green-600">✓ Ready</span>
                    ) : order.status === 'processing' ? (
                      <span className="text-blue-600">Generating...</span>
                    ) : order.status === 'failed' ? (
                      <span className="text-red-600">Failed</span>
                    ) : (
                      <span className="text-gray-400">Pending</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
