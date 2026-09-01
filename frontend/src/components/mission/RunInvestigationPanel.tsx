/**
 * RunInvestigationPanel
 *
 * Step-based investigation workflow:
 * DATA → CONFIGURE → RUN
 *
 * Clean, focused, analyst-oriented.
 */

import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useInvestigation } from '../../context/InvestigationContext';
import { uploadTransactionCSV, validateTransactionCSV } from '../../api/transactions';
import { Upload, FileText, Settings, Play, CheckCircle, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';

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
    setValidating,
    setUploadError,
    executeInvestigation,
  } = useInvestigation();

  const [zThreshold, setZThreshold] = useState<string>('0.5');
  const [merchantFilter, setMerchantFilter] = useState<string>('');
  const [configExpanded, setConfigExpanded] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Determine current step
  const dataReady = mode === 'default' || (mode === 'upload' && validation?.is_valid && !!datasetId);
  const isRunning = isLoading || isUploading;

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setUploadError('Please select a CSV file');
      return;
    }
    setUploadedFile(file);
    setUploadError(null);
    setValidation(null);
    setDatasetId(null);

    setValidating(true);
    try {
      const response = await validateTransactionCSV(file);
      if (response.ok && response.data) {
        setValidation(response.data);
        // Auto-upload after validation
        const uploadResponse = await uploadTransactionCSV(file);
        if (uploadResponse.ok && uploadResponse.data) {
          setDatasetId(uploadResponse.data.dataset_id);
        } else {
          setUploadError(uploadResponse.error?.message || 'Upload failed');
        }
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

  const handleRun = useCallback(() => {
    executeInvestigation(merchantFilter || undefined);
  }, [merchantFilter, executeInvestigation]);

  return (
    <div className="space-y-0">
      {/* Step 1: DATA */}
      <Step
        number={1}
        label="DATA"
        status={dataReady ? 'complete' : 'current'}
      >
        {/* Mode toggle */}
        <div className="flex gap-2 mb-3">
          <ModeButton
            active={mode === 'default'}
            onClick={() => { setDataSourceMode('default'); setUploadedFile(null); setValidation(null); setDatasetId(null); setUploadError(null); }}
            icon={<FileText className="w-3.5 h-3.5" />}
            label="Default Dataset"
            sublabel="Built-in demo data"
          />
          <ModeButton
            active={mode === 'upload'}
            onClick={() => setDataSourceMode('upload')}
            icon={<Upload className="w-3.5 h-3.5" />}
            label="Upload CSV"
            sublabel="Your transaction data"
          />
        </div>

        {/* Default mode info */}
        {mode === 'default' && (
          <p className="text-[10px] font-mono text-[#8A94A6]/60">
            Uses the configured pipeline dataset for demonstration.
          </p>
        )}

        {/* Upload mode */}
        <AnimatePresence>
          {mode === 'upload' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {!uploadedFile ? (
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                  onDragLeave={() => setIsDragOver(false)}
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
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                  />
                  <Upload className="w-6 h-6 text-[#8A94A6]/40 mx-auto mb-2" />
                  <p className="text-[11px] font-mono text-[#8A94A6]">
                    Drop a transaction CSV here
                  </p>
                  <p className="text-[10px] font-mono text-[#8A94A6]/40 mt-1">
                    or click to browse
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-3 p-3 border border-[#34D399]/30 bg-[#34D399]/5">
                    <CheckCircle className="w-4 h-4 text-[#34D399] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-mono text-[#F3F4F6] truncate">{uploadedFile.name}</p>
                      <p className="text-[10px] font-mono text-[#8A94A6]">
                        {(uploadedFile.size / 1024).toFixed(1)} KB
                        {datasetId && ` · ${datasetId}`}
                      </p>
                    </div>
                    <button
                      onClick={() => { setUploadedFile(null); setValidation(null); setDatasetId(null); setUploadError(null); }}
                      className="text-[10px] font-mono text-[#8A94A6] hover:text-[#FF5C5C] transition-colors"
                    >
                      Change
                    </button>
                  </div>

                  {/* Validation summary */}
                  {isValidating && (
                    <p className="text-[10px] font-mono text-[#38BDF8]/70">Validating...</p>
                  )}
                  {validation && (
                    <div className={`p-3 border text-[10px] font-mono ${
                      validation.is_valid
                        ? 'border-[#34D399]/20 bg-[#34D399]/3'
                        : 'border-[#FF5C5C]/30 bg-[#FF5C5C]/5'
                    }`}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={validation.is_valid ? 'text-[#34D399]' : 'text-[#FF5C5C]'}>
                          {validation.is_valid ? '✓ Validated' : '✗ Validation failed'}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[#8A94A6]">
                        <span>Rows: {validation.total_rows.toLocaleString()}</span>
                        {validation.unique_merchants != null && <span>Merchants: {validation.unique_merchants}</span>}
                        {validation.date_range_start && <span>From: {validation.date_range_start.slice(0, 10)}</span>}
                        {validation.date_range_end && <span>To: {validation.date_range_end.slice(0, 10)}</span>}
                      </div>
                      {validation.errors.length > 0 && (
                        <div className="mt-2 space-y-0.5">
                          {validation.errors.map((err, i) => (
                            <p key={i} className="text-[#FF5C5C]">• {err}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {uploadError && (
                    <div className="flex items-center gap-2 p-2 border border-[#FF5C5C]/30 bg-[#FF5C5C]/5">
                      <AlertTriangle className="w-3.5 h-3.5 text-[#FF5C5C] shrink-0" />
                      <p className="text-[10px] font-mono text-[#FF5C5C]">{uploadError}</p>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </Step>

      {/* Step 2: CONFIGURE */}
      <Step
        number={2}
        label="CONFIGURE"
        status={isRunning ? 'disabled' : 'available'}
      >
        <button
          onClick={() => setConfigExpanded(!configExpanded)}
          className="flex items-center gap-2 text-[10px] font-mono text-[#8A94A6] hover:text-[#F3F4F6] transition-colors"
        >
          <Settings className="w-3 h-3" />
          <span>{configExpanded ? 'Hide' : 'Show'} parameters</span>
          {configExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>

        <AnimatePresence>
          {configExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div>
                  <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">
                    Z-SCORE THRESHOLD
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.01"
                    value={zThreshold}
                    onChange={(e) => setZThreshold(e.target.value)}
                    className="w-full px-2 py-1.5 text-[11px] font-mono bg-[#0F1623] border border-[#1E293B] text-[#8A94A6] focus:border-[#38BDF8]/30 focus:outline-none"
                  />
                  <p className="text-[9px] font-mono text-[#8A94A6]/40 mt-0.5">
                    Sensitivity for spike detection (default: 0.5)
                  </p>
                </div>
                <div>
                  <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">
                    MERCHANT FILTER
                  </label>
                  <input
                    type="text"
                    placeholder="All merchants"
                    value={merchantFilter}
                    onChange={(e) => setMerchantFilter(e.target.value)}
                    className="w-full px-2 py-1.5 text-[11px] font-mono bg-[#0F1623] border border-[#1E293B] text-[#8A94A6] placeholder-[#8A94A6]/40 focus:border-[#38BDF8]/30 focus:outline-none"
                  />
                  <p className="text-[9px] font-mono text-[#8A94A6]/40 mt-0.5">
                    Analyze a single merchant (optional)
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Step>

      {/* Step 3: RUN */}
      <Step
        number={3}
        label="RUN"
        status={isRunning ? 'running' : 'available'}
      >
        <div className="flex items-center gap-4">
          <button
            onClick={handleRun}
            disabled={isRunning || (mode === 'upload' && !dataReady)}
            className="flex items-center gap-2 px-5 py-2.5 text-[11px] font-mono tracking-wider uppercase bg-[#38BDF8] text-[#0B0F18] hover:bg-[#60CCFA] disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
          >
            {isRunning ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-[#0B0F18]/30 border-t-[#0B0F18] rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                Run Investigation
              </>
            )}
          </button>

          {result && (
            <span className="text-[10px] font-mono text-[#34D399]">
              {result.totalResults} windows · {result.fullIncidents.length} incidents
            </span>
          )}
          {error && (
            <span className="text-[10px] font-mono text-[#FF5C5C]">
              {error}
            </span>
          )}
        </div>
      </Step>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Step({
  number,
  label,
  status,
  children,
}: {
  number: number;
  label: string;
  status: 'current' | 'complete' | 'available' | 'disabled' | 'running';
  children: React.ReactNode;
}) {
  const statusColors = {
    current: 'text-[#38BDF8] border-[#38BDF8] bg-[#38BDF8]/10',
    complete: 'text-[#34D399] border-[#34D399] bg-[#34D399]/10',
    available: 'text-[#8A94A6] border-[#1E293B] bg-transparent',
    disabled: 'text-[#8A94A6]/40 border-[#1E293B]/50 bg-transparent',
    running: 'text-[#38BDF8] border-[#38BDF8] bg-[#38BDF8]/10',
  };

  return (
    <div className="flex gap-4 py-4 border-b border-[#1a1f2e]/40 last:border-b-0">
      {/* Step indicator */}
      <div className="flex flex-col items-center shrink-0">
        <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center text-[10px] font-mono font-bold ${statusColors[status]}`}>
          {status === 'complete' ? '✓' : number}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-mono tracking-[0.15em] uppercase text-[#8A94A6] mb-2">
          {label}
        </div>
        {children}
      </div>
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  icon,
  label,
  sublabel,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  sublabel: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2.5 px-3 py-2 text-left border transition-all duration-200 ${
        active
          ? 'border-[#38BDF8]/40 bg-[#38BDF8]/5 text-[#F3F4F6]'
          : 'border-[#1E293B] bg-transparent text-[#8A94A6] hover:border-[#38BDF8]/20'
      }`}
    >
      <span className={active ? 'text-[#38BDF8]' : 'text-[#8A94A6]/60'}>{icon}</span>
      <div>
        <p className="text-[10px] font-mono tracking-wider">{label}</p>
        <p className="text-[9px] font-mono text-[#8A94A6]/50">{sublabel}</p>
      </div>
    </button>
  );
}
