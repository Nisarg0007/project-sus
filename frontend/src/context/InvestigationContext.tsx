/**
 * Investigation Context
 *
 * Application-level state for the SUS investigation workflow.
 * Manages:
 * - Selected entity IDs (merchant, incident, event)
 * - Investigation navigation path
 * - Investigation execution state (loading, error, result)
 *
 * This context represents APPLICATION STATE, not data fetching.
 * Data fetching is delegated to the service layer.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import type { InvestigationRunResult } from '../types';
import type { TransactionValidationResponse } from '../api/transactions';
import {
  runInvestigation,
  type ServiceResult,
} from '../services/investigationService';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DataSourceMode = 'default' | 'upload';

interface InvestigationState {
  selectedMerchantId: string | null;
  selectedIncidentId: string | null;
  selectedActivityEventId: string | null;
  investigationPath: string[];
}

interface InvestigationExecutionState {
  isLoading: boolean;
  error: string | null;
  result: InvestigationRunResult | null;
  hasRun: boolean;
}

interface DataSourceState {
  mode: DataSourceMode;
  datasetId: string | null;
  uploadedFile: File | null;
  validation: TransactionValidationResponse | null;
  isUploading: boolean;
  isValidating: boolean;
  uploadError: string | null;
}

interface InvestigationContextValue extends InvestigationState, InvestigationExecutionState, DataSourceState {
  // Entity selection
  setMerchant: (id: string | null) => void;
  setIncident: (id: string | null) => void;
  setActivityEvent: (id: string | null) => void;

  // Navigation path
  pushPath: (label: string) => void;
  clearPath: () => void;

  // Data source
  setDataSourceMode: (mode: DataSourceMode) => void;
  setUploadedFile: (file: File | null) => void;
  setDatasetId: (id: string | null) => void;
  setValidation: (v: TransactionValidationResponse | null) => void;
  setUploading: (v: boolean) => void;
  setValidating: (v: boolean) => void;
  setUploadError: (e: string | null) => void;

  // Investigation execution
  executeInvestigation: (merchantFilter?: string) => Promise<void>;
  clearInvestigationResult: () => void;

  // Reset
  clearAll: () => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const InvestigationContext = createContext<InvestigationContextValue | null>(null);

export function InvestigationProvider({ children }: { children: ReactNode }) {
  // Entity selection state
  const [state, setState] = useState<InvestigationState>({
    selectedMerchantId: null,
    selectedIncidentId: null,
    selectedActivityEventId: null,
    investigationPath: [],
  });

  // Investigation execution state
  const [execState, setExecState] = useState<InvestigationExecutionState>({
    isLoading: false,
    error: null,
    result: null,
    hasRun: false,
  });

  // Data source state
  const [dsState, setDsState] = useState<DataSourceState>({
    mode: 'default',
    datasetId: null,
    uploadedFile: null,
    validation: null,
    isUploading: false,
    isValidating: false,
    uploadError: null,
  });

  // --- Entity selection ---

  const setMerchant = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, selectedMerchantId: id }));
  }, []);

  const setIncident = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, selectedIncidentId: id }));
  }, []);

  const setActivityEvent = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, selectedActivityEventId: id }));
  }, []);

  // --- Navigation path ---

  const pushPath = useCallback((label: string) => {
    setState((prev) => ({
      ...prev,
      investigationPath: [...prev.investigationPath, label],
    }));
  }, []);

  const clearPath = useCallback(() => {
    setState((prev) => ({ ...prev, investigationPath: [] }));
  }, []);

  // --- Investigation execution ---

  const executeInvestigation = useCallback(async (merchantFilter?: string) => {
    setExecState({ isLoading: true, error: null, result: null, hasRun: false });

    const request: Record<string, unknown> = merchantFilter ? { merchant_filter: merchantFilter } : {};

    // Attach dataset_id if in upload mode
    if (dsState.mode === 'upload' && dsState.datasetId) {
      request.dataset_id = dsState.datasetId;
    }

    const serviceResult: ServiceResult<InvestigationRunResult> = await runInvestigation(request);

    if (serviceResult.error) {
      setExecState({
        isLoading: false,
        error: serviceResult.error.message,
        result: null,
        hasRun: false,
      });
    } else {
      setExecState({
        isLoading: false,
        error: null,
        result: serviceResult.data,
        hasRun: true,
      });
    }
  }, [dsState.mode, dsState.datasetId]);

  const clearInvestigationResult = useCallback(() => {
    setExecState({ isLoading: false, error: null, result: null, hasRun: false });
  }, []);

  // --- Data source setters ---

  const setDataSourceMode = useCallback((mode: DataSourceMode) => {
    setDsState(prev => ({ ...prev, mode }));
  }, []);
  const setUploadedFile = useCallback((file: File | null) => {
    setDsState(prev => ({ ...prev, uploadedFile: file }));
  }, []);
  const setDatasetId = useCallback((id: string | null) => {
    setDsState(prev => ({ ...prev, datasetId: id }));
  }, []);
  const setValidation = useCallback((v: TransactionValidationResponse | null) => {
    setDsState(prev => ({ ...prev, validation: v }));
  }, []);
  const setUploading = useCallback((v: boolean) => {
    setDsState(prev => ({ ...prev, isUploading: v }));
  }, []);
  const setValidating = useCallback((v: boolean) => {
    setDsState(prev => ({ ...prev, isValidating: v }));
  }, []);
  const setUploadError = useCallback((e: string | null) => {
    setDsState(prev => ({ ...prev, uploadError: e }));
  }, []);

  // --- Full reset ---

  const clearAll = useCallback(() => {
    setState({
      selectedMerchantId: null,
      selectedIncidentId: null,
      selectedActivityEventId: null,
      investigationPath: [],
    });
    setExecState({ isLoading: false, error: null, result: null, hasRun: false });
    setDsState({
      mode: 'default', datasetId: null, uploadedFile: null, validation: null,
      isUploading: false, isValidating: false, uploadError: null,
    });
  }, []);

  return (
    <InvestigationContext.Provider
      value={{
        ...state,
        ...execState,
        ...dsState,
        setMerchant,
        setIncident,
        setActivityEvent,
        pushPath,
        clearPath,
        setDataSourceMode,
        setUploadedFile,
        setDatasetId,
        setValidation,
        setUploading,
        setValidating,
        setUploadError,
        executeInvestigation,
        clearInvestigationResult,
        clearAll,
      }}
    >
      {children}
    </InvestigationContext.Provider>
  );
}

export function useInvestigation(): InvestigationContextValue {
  const ctx = useContext(InvestigationContext);
  if (!ctx) {
    throw new Error('useInvestigation must be used within InvestigationProvider');
  }
  return ctx;
}
