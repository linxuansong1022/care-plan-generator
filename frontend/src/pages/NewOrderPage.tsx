import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

import { orderFormSchema, type OrderFormData, isValidNPI } from '@/lib/validators'
import { useCreateOrder } from '@/hooks/useOrders'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { FormField } from '@/components/forms/FormField'
import { DuplicateWarningModal } from '@/components/modals/DuplicateWarningModal'

export function NewOrderPage() {
  const navigate = useNavigate()
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false)
  const [duplicateWarnings, setDuplicateWarnings] = useState<string[]>([])
  const [pendingData, setPendingData] = useState<OrderFormData | null>(null)

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
    },
    mode: 'onBlur',
  })

  const createOrder = useCreateOrder()

  const providerNpi = watch('providerNpi')
  const npiValid = providerNpi?.length === 10 ? isValidNPI(providerNpi) : null

  const onSubmit = async (data: OrderFormData, confirmNotDuplicate = false) => {
    try {
      const result = await createOrder.mutateAsync({
        ...data,
        confirmNotDuplicate,
      })

      if (result.requiresConfirmation && !confirmNotDuplicate) {
        setDuplicateWarnings([
          ...result.providerWarnings,
          ...result.patientWarnings,
          ...result.warnings,
        ])
        setPendingData(data)
        setShowDuplicateWarning(true)
        return
      }

      // Success
      navigate(`/orders/${result.order?.id}`, {
        state: { message: 'Order created successfully' },
      })
    } catch (error) {
      console.error('Failed to create order:', error)
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
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Create New Order</h1>

      {createOrder.isError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <p className="text-red-700">
            {(createOrder.error as Error)?.message || 'Failed to create order'}
          </p>
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
                  placeholder="1234567893"
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
                10 digits with valid checksum
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
        onConfirm={handleConfirmNotDuplicate}
        onCancel={handleCancelDuplicate}
        isLoading={createOrder.isPending}
      />
    </div>
  )
}
