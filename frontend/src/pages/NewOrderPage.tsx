import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle, Loader2, Info } from 'lucide-react'

import { orderFormSchema, type OrderFormData, isValidNPI } from '@/lib/validators'
import { useCreateOrder } from '@/hooks/useOrders'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { FormField } from '@/components/forms/FormField'
import { DuplicateWarningModal } from '@/components/modals/DuplicateWarningModal'
import type { Warning } from '@/types'

export function NewOrderPage() {
  const navigate = useNavigate()
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false)
  const [duplicateWarnings, setDuplicateWarnings] = useState<Warning[]>([])
  const [blockingError, setBlockingError] = useState<string | undefined>()
  const [pendingData, setPendingData] = useState<OrderFormData | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<OrderFormData>({
    resolver: zodResolver(orderFormSchema),
    defaultValues: {
      patientMrn: '',
      patientFirstName: '',
      patientLastName: '',
      primaryDiagnosisCode: '',
      additionalDiagnoses: [],
      medicationHistory: [],
      providerNpi: '',
      providerName: '',
      medicationName: '',
      patientRecords: '',
      // Note: medicationHistory is stored as array but displayed as string in textarea
    },
    mode: 'onBlur',
  })

  const createOrder = useCreateOrder()

  const providerNpi = watch('providerNpi')
  const npiValid = providerNpi?.length === 10 ? isValidNPI(providerNpi) : null

  const onSubmit = async (data: OrderFormData, confirmNotDuplicate = false) => {
    setSuccessMessage(null)
    setBlockingError(undefined)
    
    try {
      const result = await createOrder.mutateAsync({
        ...data,
        confirmNotDuplicate,
      })

      // Check for blocking issues
      if (result.isBlocked) {
        setBlockingError(result.blockingReason)
        setDuplicateWarnings(result.allWarnings || [])
        setShowDuplicateWarning(true)
        return
      }

      // Check for warnings requiring confirmation
      if (result.requiresConfirmation && !confirmNotDuplicate) {
        setDuplicateWarnings(result.allWarnings || [])
        setPendingData(data)
        setShowDuplicateWarning(true)
        return
      }

      // Success - show info messages if any
      const infoMessages = result.allWarnings?.filter((w: Warning) => !w.action_required) || []
      if (infoMessages.length > 0) {
        setSuccessMessage(infoMessages.map((w: Warning) => w.message).join(' '))
      }

      // Navigate to order detail
      navigate(`/orders/${result.order?.id}`, {
        state: { 
          message: 'Order created successfully',
          warnings: infoMessages,
        },
      })
    } catch (error: any) {
      console.error('Failed to create order:', error)
      
      // Parse error response for warnings
      if (error.response?.data) {
        const data = error.response.data
        if (data.all_warnings || data.warnings) {
          setDuplicateWarnings(data.all_warnings || data.warnings || [])
          setBlockingError(data.blocking_reason || data.detail)
          setShowDuplicateWarning(true)
        }
      }
    }
  }

  const handleConfirmNotDuplicate = async () => {
    if (!pendingData) return
    setShowDuplicateWarning(false)
    await onSubmit(pendingData, true)
  }

  const handleCancelDuplicate = () => {
    setShowDuplicateWarning(false)
    setPendingData(null)
    setBlockingError(undefined)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Create New Order</h1>

      {/* Success Message */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start gap-3">
          <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
          <div>
            <p className="text-green-700 font-medium">Order created!</p>
            <p className="text-green-600 text-sm">{successMessage}</p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {createOrder.isError && !showDuplicateWarning && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
          <div>
            <p className="text-red-700 font-medium">Failed to create order</p>
            <p className="text-red-600 text-sm">
              {(createOrder.error as any)?.response?.data?.detail || 
               (createOrder.error as Error)?.message || 
               'An unexpected error occurred'}
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit((data) => onSubmit(data))} className="space-y-8">
        {/* Patient Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Patient Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="MRN" error={errors.patientMrn?.message} required>
              <Input
                {...register('patientMrn')}
                placeholder="123456"
                maxLength={6}
                className="font-mono"
                error={!!errors.patientMrn}
              />
              <p className="text-xs text-gray-500 mt-1">Exactly 6 digits</p>
            </FormField>

            <FormField label="First Name" error={errors.patientFirstName?.message} required>
              <Input
                {...register('patientFirstName')}
                placeholder="John"
                error={!!errors.patientFirstName}
              />
            </FormField>

            <FormField label="Last Name" error={errors.patientLastName?.message} required>
              <Input
                {...register('patientLastName')}
                placeholder="Doe"
                error={!!errors.patientLastName}
              />
            </FormField>

            <FormField label="Date of Birth" error={errors.patientDateOfBirth?.message}>
              <Input
                type="date"
                {...register('patientDateOfBirth')}
                max={new Date().toISOString().split('T')[0]}
              />
            </FormField>

            <FormField label="Sex" error={errors.patientSex?.message}>
              <Select {...register('patientSex')}>
                <option value="">Select sex</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </Select>
            </FormField>

            <FormField label="Weight (kg)" error={errors.patientWeightKg?.message}>
              <Input
                type="number"
                step="0.1"
                {...register('patientWeightKg', { valueAsNumber: true })}
                placeholder="72.5"
              />
            </FormField>

            <FormField
              label="Allergies"
              error={errors.patientAllergies?.message}
              className="md:col-span-2"
            >
              <Textarea
                {...register('patientAllergies')}
                placeholder="None known to medications"
                rows={2}
              />
            </FormField>

            <FormField
              label="Primary Diagnosis (ICD-10)"
              error={errors.primaryDiagnosisCode?.message}
              required
              className="md:col-span-2"
            >
              <div className="flex gap-2">
                <Input
                  {...register('primaryDiagnosisCode')}
                  placeholder="G70.00"
                  className="w-32 font-mono uppercase"
                  error={!!errors.primaryDiagnosisCode}
                />
                <Input
                  {...register('primaryDiagnosisDescription')}
                  placeholder="Myasthenia gravis"
                  className="flex-1"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Format: Letter + 2 digits + optional decimal (e.g., G70.00, I10)
              </p>
            </FormField>

            <FormField
              label="Medication History"
              error={errors.medicationHistory?.message}
              className="md:col-span-2"
            >
              <Textarea
                {...register('medicationHistory', {
                  setValueAs: (v: string | string[]) => {
                    if (Array.isArray(v)) return v
                    return v ? v.split('\n').map(s => s.trim()).filter(Boolean) : []
                  }
                })}
                placeholder="Enter one medication per line, e.g.:
Prednisone 10mg daily
Methotrexate 15mg weekly
IVIG 30g monthly"
                rows={4}
              />
              <p className="text-xs text-gray-500 mt-1">
                One medication per line (include dosage and frequency if known)
              </p>
            </FormField>
          </div>
        </div>

        {/* Provider Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Referring Provider
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="NPI" error={errors.providerNpi?.message} required>
              <div className="relative">
                <Input
                  {...register('providerNpi')}
                  placeholder="1234567890"
                  maxLength={10}
                  className="font-mono pr-10"
                  error={!!errors.providerNpi}
                />
                {npiValid !== null && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {npiValid ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                10 digits
              </p>
            </FormField>

            <FormField label="Provider Name" error={errors.providerName?.message} required>
              <Input
                {...register('providerName')}
                placeholder="Dr. Jane Smith"
                error={!!errors.providerName}
              />
            </FormField>
          </div>
          
          {/* Info about NPI */}
          <div className="mt-4 p-3 bg-blue-50 rounded-lg flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-500 mt-0.5" />
            <p className="text-sm text-blue-700">
              If this NPI already exists with a different name, you will be notified. 
              If the NPI is new, a new provider record will be created.
            </p>
          </div>
        </div>

        {/* Order Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-blue-700">
            Order Details
          </h2>
          <div className="space-y-4">
            <FormField
              label="Medication Name"
              error={errors.medicationName?.message}
              required
            >
              <Input
                {...register('medicationName')}
                placeholder="IVIG (Privigen)"
                error={!!errors.medicationName}
              />
            </FormField>

            <FormField
              label="Patient Records / Clinical Notes"
              error={errors.patientRecords?.message}
              required
            >
              <Textarea
                {...register('patientRecords')}
                placeholder="Paste patient clinical records here..."
                rows={15}
                className="font-mono text-sm"
                error={!!errors.patientRecords}
              />
              <p className="text-xs text-gray-500 mt-1">
                Include all relevant clinical information for care plan generation
              </p>
            </FormField>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => navigate('/orders')}>
            Cancel
          </Button>
          <Button type="submit" disabled={createOrder.isPending}>
            {createOrder.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Order'
            )}
          </Button>
        </div>
      </form>

      {/* Duplicate Warning Modal */}
      <DuplicateWarningModal
        open={showDuplicateWarning}
        warnings={duplicateWarnings}
        blockingError={blockingError}
        onConfirm={handleConfirmNotDuplicate}
        onCancel={handleCancelDuplicate}
        isLoading={createOrder.isPending}
      />
    </div>
  )
}