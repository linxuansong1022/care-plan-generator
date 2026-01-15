import { useState, useRef } from 'react'
import { X, Upload, FileText, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useUploadCarePlan, useUploadCarePlanFile } from '@/hooks/useOrders'

interface UploadCarePlanModalProps {
  orderId: string
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function UploadCarePlanModal({
  orderId,
  isOpen,
  onClose,
  onSuccess,
}: UploadCarePlanModalProps) {
  const [content, setContent] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadMode, setUploadMode] = useState<'text' | 'file'>('text')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const uploadText = useUploadCarePlan()
  const uploadFile = useUploadCarePlanFile()

  const isUploading = uploadText.isPending || uploadFile.isPending

  if (!isOpen) return null

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      // Also read file content to preview
      const reader = new FileReader()
      reader.onload = (event) => {
        setContent(event.target?.result as string)
      }
      reader.readAsText(file)
    }
  }

  const handleSubmit = async () => {
    try {
      if (uploadMode === 'file' && selectedFile) {
        await uploadFile.mutateAsync({ orderId, file: selectedFile })
      } else if (content.trim()) {
        await uploadText.mutateAsync({ orderId, content })
      }
      onSuccess()
      handleClose()
    } catch (error) {
      console.error('Upload failed:', error)
    }
  }

  const handleClose = () => {
    setContent('')
    setSelectedFile(null)
    setUploadMode('text')
    onClose()
  }

  const canSubmit =
    (uploadMode === 'text' && content.trim().length > 0) ||
    (uploadMode === 'file' && selectedFile !== null)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Upload Care Plan</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 flex-1 overflow-auto">
          {/* Upload Mode Toggle */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setUploadMode('text')}
              className={`flex-1 py-2 px-4 rounded-lg border transition-colors ${
                uploadMode === 'text'
                  ? 'bg-blue-50 border-blue-500 text-blue-700'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <FileText className="h-4 w-4 inline mr-2" />
              Paste Text
            </button>
            <button
              onClick={() => setUploadMode('file')}
              className={`flex-1 py-2 px-4 rounded-lg border transition-colors ${
                uploadMode === 'file'
                  ? 'bg-blue-50 border-blue-500 text-blue-700'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Upload className="h-4 w-4 inline mr-2" />
              Upload File
            </button>
          </div>

          {uploadMode === 'text' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Care Plan Content
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste your care plan content here..."
                className="w-full h-64 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm resize-none"
              />
              <p className="mt-1 text-sm text-gray-500">
                {content.length} characters
              </p>
            </div>
          ) : (
            <div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept=".txt,.text"
                className="hidden"
              />
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
              >
                {selectedFile ? (
                  <div>
                    <FileText className="h-12 w-12 mx-auto text-blue-500 mb-2" />
                    <p className="font-medium text-gray-900">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                    <p className="text-sm text-blue-600 mt-2">Click to change file</p>
                  </div>
                ) : (
                  <div>
                    <Upload className="h-12 w-12 mx-auto text-gray-400 mb-2" />
                    <p className="font-medium text-gray-600">
                      Click to select a file
                    </p>
                    <p className="text-sm text-gray-500">
                      Supports .txt files
                    </p>
                  </div>
                )}
              </div>

              {/* Preview */}
              {content && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Preview
                  </label>
                  <div className="bg-gray-50 rounded-lg p-3 max-h-40 overflow-auto">
                    <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
                      {content.substring(0, 500)}
                      {content.length > 500 && '...'}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Warning */}
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              <strong>Note:</strong> Uploading a new care plan will replace any
              existing care plan for this order.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t bg-gray-50">
          <Button variant="outline" onClick={handleClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || isUploading}>
            {isUploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Upload Care Plan
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
