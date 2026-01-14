import { z } from 'zod'

/**
 * Validate NPI - must be exactly 10 digits
 */
function isValidNPI(npi: string): boolean {
  return /^\d{10}$/.test(npi)
}

/**
 * Validate ICD-10 code format
 */
function isValidICD10(code: string): boolean {
  return /^[A-TV-Z]\d{2}(\.\w{1,4})?$/i.test(code)
}

// Patient section schema
export const patientSchema = z.object({
  patientMrn: z
    .string()
    .length(6, 'MRN must be exactly 6 digits')
    .regex(/^\d{6}$/, 'MRN must contain only digits'),

  patientFirstName: z
    .string()
    .min(1, 'First name is required')
    .max(100, 'First name too long'),

  patientLastName: z
    .string()
    .min(1, 'Last name is required')
    .max(100, 'Last name too long'),

  patientDateOfBirth: z
    .string()
    .optional()
    .refine(
      (val) => !val || !isNaN(Date.parse(val)),
      'Invalid date format'
    )
    .refine(
      (val) => !val || new Date(val) <= new Date(),
      'Date of birth cannot be in the future'
    ),

  patientSex: z
    .enum(['Male', 'Female', 'Other'])
    .optional(),

  patientWeightKg: z
    .number()
    .positive('Weight must be positive')
    .max(500, 'Weight seems too high')
    .optional(),

  patientAllergies: z
    .string()
    .max(1000, 'Allergies text too long')
    .optional(),

  primaryDiagnosisCode: z
    .string()
    .min(1, 'Primary diagnosis is required')
    .refine(isValidICD10, 'Invalid ICD-10 code format (e.g., G70.00, I10)'),

  primaryDiagnosisDescription: z
    .string()
    .max(500)
    .optional(),

  additionalDiagnoses: z
    .array(z.string())
    .default([]),

  medicationHistory: z
    .array(z.string())
    .default([]),
})

// Provider section schema
export const providerSchema = z.object({
  providerNpi: z
    .string()
    .length(10, 'NPI must be exactly 10 digits')
    .regex(/^\d{10}$/, 'NPI must contain only digits'),

  providerName: z
    .string()
    .min(1, 'Provider name is required')
    .max(200, 'Provider name too long'),
})

// Order section schema
export const orderSchema = z.object({
  medicationName: z
    .string()
    .min(1, 'Medication name is required')
    .max(200, 'Medication name too long'),

  patientRecords: z
    .string()
    .min(1, 'Patient records are required')
    .max(50000, 'Patient records too long'),
})

// Complete form schema
export const orderFormSchema = patientSchema
  .merge(providerSchema)
  .merge(orderSchema)

export type OrderFormData = z.infer<typeof orderFormSchema>

// Export NPI validator for real-time validation
export { isValidNPI, isValidICD10 }
