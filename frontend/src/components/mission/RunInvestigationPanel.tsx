/**
 * RunInvestigationPanel
 *
 * Enhanced investigation run UI that supports:
 * - Default dataset mode (existing behavior)
 * - CSV upload mode with drag/drop
 * - Pre-run validation results
 * - Parameter configuration (z_threshold, merchant_filter)
 */

import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useInvestigation } from '../../context/InvestigationContext';
import { uploadTransactionCSV, validateTransactionCSV } from '../../api/transactions';

export function RunInvestigationPanel() {
  const {
    mode,
    datasetId,
    uploadedFile,
    validation,
    isUploading,
    isValidating,
    uploadError,
    isLoading,
    error,
    result,
    setDataSourceMode,
    setUploadedFile,
    setDatasetId,
    setValidation,
    setUploading,
    setValidating,
    setUploadError,
    executeInvestigation,
  } = useInvestigation();

  const [zThreshold, setZThreshold] = useState<string>('0.5');
  const [merchantFilter, setMerchantFilter] = useState<string>('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setUploadError('Please select a CSV file');
      return;
    }
    setUploadedFile(file);
    setUploadError(null);
    setValidation(null);
    setDatasetId(null);

    // Validate first
    setValidating(true);
    try {
      const response = await validateTransactionCSV(file);
      if (response.ok && response.data) {
        setValidation(response.data);
      } else {
        setUploadError(response.error?.message || 'Validation failed');
      }
    } catch {
      setUploadError('Failed to validate file');
    } finally {
      setValidating(false);
    }
  }, [setUploadedFile, setUploadError, setValidation, setDatasetId, setValidating]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleUploadAndRun = useCallback(async () => {
    if (!uploadedFile) return;

    setUploading(true);
    setUploadError(null);
    try {
      const response = await uploadTransactionCSV(uploadedFile);
      if (response.ok && response.data) {
        setDatasetId(response.data.dataset_id);
        // Now run the investigation
        await executeInvestigation(merchantFilter || undefined);
      } else {
        setUploadError(response.error?.message || 'Upload failed');
      }
    } catch {
      setUploadError('Upload failed');
    } finally {
      setUploading(false);
    }
  }, [uploadedFile, merchantFilter, setUploading, setUploadError, setDatasetId, executeInvestigation]);

  const handleRunDefault = useCallback(() => {
    executeInvestigation(merchantFilter || undefined);
  }, [merchantFilter, executeInvestigation]);

  const isRunning = isLoading || isUploading;

  return (
    <div className="border border-[#1E293B]/60 bg-[#0B0F18]/80 p-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <h3 className="text-[11px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
          Run Investigation
        </h3>
      </div>

      {/* Data Source Toggle */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setDataSourceMode('default')}
          className={`px-3 py-1.5 text-[10px] font-mono tracking-wider uppercase transition-all duration-200 ${
            mode === 'default'
              ? 'bg-[#1E293B] text-[#38BDF8] border border-[#38BDF8]/30'
              : 'bg-transparent text-[#8A94A6] border border-[#1E293B] hover:border-[#38BDF8]/20'
          }`}
        >
          Default Dataset
        </button>
        <button
          onClick={() => setDataSourceMode('upload')}
          className={`px-3 py-1.5 text-[10px] font-mono tracking-wider uppercase transition-all duration-200 ${
            mode === 'upload'
              ? 'bg-[#1E293B] text-[#38BDF8] border border-[#38BDF8]/30'
              : 'bg-transparent text-[#8A94A6] border border-[#1E293B] hover:border-[#38BDF8]/20'
          }`}
        >
          Upload CSV
        </button>
      </div>

      {/* Upload Area */}
      <AnimatePresence>
        {mode === 'upload' && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden mb-4"
          >
            {/* Drag/Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed p-6 text-center cursor-pointer transition-all duration-200 ${
                isDragOver
                  ? 'border-[#38BDF8]/50 bg-[#38BDF8]/5'
                  : 'border-[#1E293B] hover:border-[#38BDF8]/30'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
              {uploadedFile ? (
                <div>
                  <p className="text-[11px] font-mono text-[#34D399]">
                    ✓ {uploadedFile.name}
                  </p>
                  <p className="text-[10px] font-mono text-[#8A94A6] mt-1">
                    {(uploadedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-[11px] font-mono text-[#8A94A6]">
                    Drag & drop a transaction CSV here
                  </p>
                  <p className="text-[10px] font-mono text-[#8A94A6]/60 mt-1">
                    or click to browse
                  </p>
                </div>
              )}
            </div>

            {/* Validation Results */}
            {(isValidating || validation || uploadError) && (
              <div className="mt-3 space-y-2">
                {isValidating && (
                  <p className="text-[10px] font-mono text-[#38BDF8]/70">
                    Validating...
                  </p>
                )}

                {validation && (
                  <div className={`p-3 border text-[10px] font-mono ${
                    validation.is_valid
                      ? 'border-[#34D399]/30 bg-[#34D399]/5'
                      : 'border-[#FF5C5C]/30 bg-[#FF5C5C]/5'
                  }`}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={validation.is_valid ? 'text-[#34D399]' : 'text-[#FF5C5C]'}>
                        {validation.is_valid ? '✓ Valid' : '✗ Invalid'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[#8A94A6]">
                      <span>Rows: {validation.total_rows.toLocaleString()}</span>
                      {validation.unique_merchants != null && (
                        <span>Merchants: {validation.unique_merchants}</span>
                      )}
                      {validation.date_range_start && (
                        <span>From: {validation.date_range_start.slice(0, 10)}</span>
                      )}
                      {validation.date_range_end && (
                        <span>To: {validation.date_range_end.slice(0, 10)}</span>
                      )}
                      {validation.amount_min != null && (
                        <span>Min amt: ₹{validation.amount_min.toFixed(2)}</span>
                      )}
                      {validation.amount_max != null && (
                        <span>Max amt: ₹{validation.amount_max.toFixed(2)}</span>
                      )}
                    </div>
                    {validation.errors.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {validation.errors.map((err, i) => (
                          <p key={i} className="text-[#FF5C5C]">• {err}</p>
                        ))}
                      </div>
                    )}
                    {validation.warnings.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {validation.warnings.map((warn, i) => (
                          <p key={i} className="text-[#FBBF24]">• {warn}</p>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {uploadError && (
                  <p className="text-[10px] font-mono text-[#FF5C5C]">
                    {uploadError}
                  </p>
                )}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Parameters */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div>
          <label className="block text-[10px] font-mono text-[#8A94A6] mb-1">
            Z-Score Threshold
          </label>
          <input
            type="number"
            step="0.1"
            min="0.01"
            value={zThreshold}
            onChange={(e) => setZThreshold(e.target.value)}
            className="w-full px-2 py-1.5 text-[11px] font-mono bg-[#0F1623] border border-[#1E293B] text-[#8A94A6] focus:border-[#38BDF8]/30 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-[10px] font-mono text-[#8A94A6] mb-1">
            Merchant Filter
          </label>
          <input
            type="text"
            placeholder="All merchants"
            value={merchantFilter}
            onChange={(e) => setMerchantFilter(e.target.value)}
            className="w-full px-2 py-1.5 text-[11px] font-mono bg-[#0F1623] border border-[#1E293B] text-[#8A94A6] placeholder-[#8A94A6]/40 focus:border-[#38BDF8]/30 focus:outline-none"
          />
        </div>
      </div>

      {/* Run Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={mode === 'upload' ? handleUploadAndRun : handleRunDefault}
          disabled={isRunning || (mode === 'upload' && (!uploadedFile || !validation?.is_valid))}
          className="px-4 py-2 text-xs font-mono tracking-wider uppercase bg-[#0F1623] border border-[#1E293B] text-[#8A94A6] hover:text-[#38BDF8] hover:border-[#38BDF8]/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning
            ? isUploading ? 'Uploading...' : 'Running Investigation...'
            : mode === 'upload' ? 'Upload & Run' : 'Run Investigation'}
        </button>

        {result && (
          <span className="text-xs font-mono text-[#34D399]">
            {result.totalResults} windows analyzed — {result.fullIncidents.length} incidents found
          </span>
        )}

        {error && (
          <span className="text-xs font-mono text-[#FF5C5C]">
            {error}
          </span>
        )}
      </div>

      {/* Source label */}
      {result && (
        <p className="mt-2 text-[10px] font-mono text-[#8A94A6]/60">
          Source: {mode === 'upload' && datasetId ? `Uploaded dataset ${datasetId}` : 'Default demo dataset'}
        </p>
      )}
    </div>
  );
}
