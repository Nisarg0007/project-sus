import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface InvestigationState {
  selectedMerchantId: string | null;
  selectedIncidentId: string | null;
  selectedActivityEventId: string | null;
  investigationPath: string[];
}

interface InvestigationContextValue extends InvestigationState {
  setMerchant: (id: string | null) => void;
  setIncident: (id: string | null) => void;
  setActivityEvent: (id: string | null) => void;
  pushPath: (label: string) => void;
  clearPath: () => void;
  clearAll: () => void;
}

const InvestigationContext = createContext<InvestigationContextValue | null>(null);

export function InvestigationProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<InvestigationState>({
    selectedMerchantId: null,
    selectedIncidentId: null,
    selectedActivityEventId: null,
    investigationPath: [],
  });

  const setMerchant = useCallback((id: string | null) => {
    setState(prev => ({ ...prev, selectedMerchantId: id }));
  }, []);

  const setIncident = useCallback((id: string | null) => {
    setState(prev => ({ ...prev, selectedIncidentId: id }));
  }, []);

  const setActivityEvent = useCallback((id: string | null) => {
    setState(prev => ({ ...prev, selectedActivityEventId: id }));
  }, []);

  const pushPath = useCallback((label: string) => {
    setState(prev => ({
      ...prev,
      investigationPath: [...prev.investigationPath, label],
    }));
  }, []);

  const clearPath = useCallback(() => {
    setState(prev => ({ ...prev, investigationPath: [] }));
  }, []);

  const clearAll = useCallback(() => {
    setState({
      selectedMerchantId: null,
      selectedIncidentId: null,
      selectedActivityEventId: null,
      investigationPath: [],
    });
  }, []);

  return (
    <InvestigationContext.Provider
      value={{
        ...state,
        setMerchant,
        setIncident,
        setActivityEvent,
        pushPath,
        clearPath,
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
