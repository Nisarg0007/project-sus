/**
 * Data Source Abstraction
 *
 * Provides a unified interface for accessing data, supporting both:
 * - mock mode (default): uses hardcoded mock data
 * - api mode: calls the real backend
 *
 * The data source mode is controlled by VITE_DATA_SOURCE environment variable.
 * UI components never contain mode-switching logic — they call these
 * functions and get the right data.
 */

import type {
  DashboardMetrics,
  InvestigationAnomaly,
  ActivityEvent,
  FullIncident,
  Merchant,
  MerchantDirectoryItem,
  MerchantProfile,
  Incident,
  Anomaly,
} from '../types';
import {
  merchants,
  dashboardMetrics,
  investigationAnomalies,
  activityEvents,
  fullIncidents,
  merchantDirectory,
  merchantProfiles,
  incidents,
  anomalies,
} from './mockData';
import {
  runInvestigation as apiRunInvestigation,
  rerunInvestigation as apiRerunInvestigation,
  compareInvestigations as apiCompareInvestigations,
  getInvestigationHistory as apiGetInvestigationHistory,
  getInvestigationById as apiGetInvestigationById,
} from '../services/investigationService';
import type {
  InvestigationHistoryList,
  InvestigationHistoryDetail,
} from '../api/mappers/investigationHistoryMapper';
import type { BackendComparisonResponse } from '../api/investigations';
import type { InvestigationHistoryFilters } from '../api/investigations';
import { fetchMerchants, fetchMerchantDirectory, fetchMerchantProfile } from '../services/merchantService';
import { fetchActivityEvents } from '../services/activityService';
import { fetchFullIncidents } from '../services/incidentService';
import type { InvestigationRequest } from '../api/investigations';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

type DataSourceMode = 'mock' | 'api';

function getMode(): DataSourceMode {
  const env = import.meta.env.VITE_DATA_SOURCE;
  if (env === 'api') return 'api';
  return 'mock';
}

// ---------------------------------------------------------------------------
// Mock data functions (return existing mock data)
// ---------------------------------------------------------------------------

const mockData = {
  getDashboardMetrics: (): DashboardMetrics => dashboardMetrics,
  getMerchants: (): Merchant[] => merchants,
  getMerchantDirectory: (): MerchantDirectoryItem[] => merchantDirectory,
  getMerchantProfile: (id: string): MerchantProfile | null =>
    merchantProfiles[id] ?? null,
  getInvestigationAnomalies: (): InvestigationAnomaly[] => investigationAnomalies,
  getActivityEvents: (): ActivityEvent[] => activityEvents,
  getFullIncidents: (): FullIncident[] => fullIncidents,
  getIncidents: (): Incident[] => incidents,
  getAnomalies: (): Anomaly[] => anomalies,
  runInvestigation: async (request?: InvestigationRequest) => {
    // In mock mode, run the investigation against the real pipeline
    // but return the result in the same format as API mode
    return apiRunInvestigation(request ?? {});
  },

  // Investigation history — mock mode returns empty list
  getInvestigationHistory: async (
    _limit?: number,
    _offset?: number,
    _filters?: InvestigationHistoryFilters,
  ): Promise<InvestigationHistoryList> => {
    return { total: 0, limit: _limit ?? 20, offset: _offset ?? 0, items: [] };
  },

  getInvestigationById: async (
    _id: string,
  ): Promise<InvestigationHistoryDetail | null> => {
    return null;
  },

  compareInvestigations: async (
    _baseId: string,
    _compareId: string,
  ): Promise<BackendComparisonResponse | null> => {
    return null;
  },
};

// ---------------------------------------------------------------------------
// Public API — single entry point for all data access
// ---------------------------------------------------------------------------

export const dataSource = {
  /** Get the current data source mode. */
  getMode,

  /** Check if running in API mode. */
  isApiMode: (): boolean => getMode() === 'api',

  /** Dashboard metrics (overview numbers). */
  getDashboardMetrics: async (): Promise<DashboardMetrics> => {
    return mockData.getDashboardMetrics();
  },

  /** All merchants. */
  getMerchants: async (): Promise<Merchant[]> => {
    if (getMode() === 'api') {
      const result = await fetchMerchants();
      return result.data ?? mockData.getMerchants();
    }
    return mockData.getMerchants();
  },

  /** Merchant directory items for the sidebar. */
  getMerchantDirectory: async (): Promise<MerchantDirectoryItem[]> => {
    if (getMode() === 'api') {
      const result = await fetchMerchantDirectory();
      return result.data ?? mockData.getMerchantDirectory();
    }
    return mockData.getMerchantDirectory();
  },

  /** Full merchant profile with behavioral fingerprint. */
  getMerchantProfile: async (id: string): Promise<MerchantProfile | null> => {
    if (getMode() === 'api') {
      const result = await fetchMerchantProfile(id);
      return result.data ?? mockData.getMerchantProfile(id);
    }
    return mockData.getMerchantProfile(id);
  },

  /** Investigation anomalies for Mission Control. */
  getInvestigationAnomalies: async (): Promise<InvestigationAnomaly[]> => {
    return mockData.getInvestigationAnomalies();
  },

  /** Activity feed events. */
  getActivityEvents: async (): Promise<ActivityEvent[]> => {
    if (getMode() === 'api') {
      const result = await fetchActivityEvents();
      return result.data ?? mockData.getActivityEvents();
    }
    return mockData.getActivityEvents();
  },

  /** Full incidents with investigation details. */
  getFullIncidents: async (): Promise<FullIncident[]> => {
    if (getMode() === 'api') {
      const result = await fetchFullIncidents();
      return result.data ?? mockData.getFullIncidents();
    }
    return mockData.getFullIncidents();
  },

  /** Basic incident list. */
  getIncidents: async (): Promise<Incident[]> => {
    return mockData.getIncidents();
  },

  /** Anomaly list. */
  getAnomalies: async (): Promise<Anomaly[]> => {
    return mockData.getAnomalies();
  },

  /** Run a pipeline investigation (works in both modes). */
  runInvestigation: async (request?: InvestigationRequest) => {
    return mockData.runInvestigation(request);
  },

  /** Re-run a previous investigation using its stored configuration. */
  rerunInvestigation: async (investigationId: string) => {
    if (getMode() === 'api') {
      return apiRerunInvestigation(investigationId);
    }
    // Mock mode: run the pipeline with default params
    return apiRerunInvestigation(investigationId);
  },

  /** Investigation history list. */
  getInvestigationHistory: async (
    limit?: number,
    offset?: number,
    filters?: InvestigationHistoryFilters,
  ): Promise<InvestigationHistoryList> => {
    if (getMode() === 'api') {
      const result = await apiGetInvestigationHistory(limit, offset, filters);
      return result.data ?? mockData.getInvestigationHistory(limit, offset, filters);
    }
    return mockData.getInvestigationHistory(limit, offset, filters);
  },

  /** Single persisted investigation detail. */
  getInvestigationById: async (
    id: string,
  ): Promise<InvestigationHistoryDetail | null> => {
    if (getMode() === 'api') {
      const result = await apiGetInvestigationById(id);
      return result.data ?? mockData.getInvestigationById(id);
    }
    return mockData.getInvestigationById(id);
  },

  /** Compare two investigations. */
  compareInvestigations: async (
    baseId: string,
    compareId: string,
  ): Promise<BackendComparisonResponse | null> => {
    if (getMode() === 'api') {
      const result = await apiCompareInvestigations(baseId, compareId);
      return result.data ?? mockData.compareInvestigations(baseId, compareId);
    }
    return mockData.compareInvestigations(baseId, compareId);
  },
};
