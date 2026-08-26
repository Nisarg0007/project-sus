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
import {
  runInvestigation,
  type ServiceResult,
} from '../services/investigationService';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

interface InvestigationContextValue extends InvestigationState, InvestigationExecutionState {
  // Entity selection
  setMerchant: (id: string | null) => void;
  setIncident: (id: string | null) => void;
  setActivityEvent: (id: string | null) => void;

  // Navigation path
  pushPath: (label: string) => void;
  clearPath: () => void;

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

    const request = merchantFilter ? { merchant_filter: merchantFilter } : {};

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
  }, []);

  const clearInvestigationResult = useCallback(() => {
    setExecState({ isLoading: false, error: null, result: null, hasRun: false });
  }, []);

  // --- Full reset ---

  const clearAll = useCallback(() => {
    setState({
      selectedMerchantId: null,
      selectedIncidentId: null,
      selectedActivityEventId: null,
      investigationPath: [],
    });
    setExecState({
      isLoading: false,
      error: null,
      result: null,
      hasRun: false,
    });
  }, []);

  return (
    <InvestigationContext.Provider
      value={{
        ...state,
        ...execState,
        setMerchant,
        setIncident,
        setActivityEvent,
        pushPath,
        clearPath,
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
