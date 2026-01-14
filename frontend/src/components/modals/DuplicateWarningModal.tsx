import { AlertTriangle, Loader2, X, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { Warning } from '@/types'

interface DuplicateWarningModalProps {
  open: boolean
  warnings: Warning[]
  blockingError?: string
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

export function DuplicateWarningModal({
  open,
  warnings,
  blockingError,
  onConfirm,
  onCancel,
  isLoading = false,
}: DuplicateWarningModalProps) {
  if (!open) return null

  const isBlocked = !!blockingError

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6">
        {/* Close button */}
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className={`p-2 rounded-full ${isBlocked ? 'bg-red-100' : 'bg-amber-100'}`}>
            {isBlocked ? (
              <XCircle className="h-6 w-6 text-red-600" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-amber-600" />
            )}
          </div>
          <h2 className="text-lg font-semibold text-gray-900">
            {isBlocked ? 'Cannot Create Order' : 'Potential Duplicate Detected'}
          </h2>
        </div>

        {/* Blocking Error */}
        {isBlocked && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm mb-4">
            {blockingError}
          </div>
        )}

        {/* Warnings */}
        <div className="space-y-3 mb-6">
          {warnings.map((warning, index) => (
            <div
              key={index}
              className={`p-3 rounded-lg text-sm ${
                warning.action_required
                  ? 'bg-amber-50 border border-amber-200 text-amber-800'
                  : 'bg-blue-50 border border-blue-200 text-blue-800'
              }`}
            >
              <div className="font-medium">{warning.code}</div>
              <div>{warning.message}</div>
            </div>
          ))}
        </div>

        {/* Instructions */}
        {!isBlocked && (
          <div className="bg-gray-50 p-4 rounded-lg text-sm text-gray-600 mb-6">
            <p className="font-medium mb-2">What would you like to do?</p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <strong>Cancel</strong> - Go back and review/correct the information
              </li>
              <li>
                <strong>Continue Anyway</strong> - Confirm this is not a duplicate and proceed
              </li>
            </ul>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            {isBlocked ? 'Close' : 'Cancel'}
          </Button>
          {!isBlocked && (
            <Button
              onClick={onConfirm}
              disabled={isLoading}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                'Continue Anyway'
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
