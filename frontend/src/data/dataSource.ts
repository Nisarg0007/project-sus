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
import { runInvestigation as apiRunInvestigation } from '../services/investigationService';
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
    return mockData.getMerchants();
  },

  /** Merchant directory items for the sidebar. */
  getMerchantDirectory: async (): Promise<MerchantDirectoryItem[]> => {
    return mockData.getMerchantDirectory();
  },

  /** Full merchant profile with behavioral fingerprint. */
  getMerchantProfile: async (id: string): Promise<MerchantProfile | null> => {
    return mockData.getMerchantProfile(id);
  },

  /** Investigation anomalies for Mission Control. */
  getInvestigationAnomalies: async (): Promise<InvestigationAnomaly[]> => {
    return mockData.getInvestigationAnomalies();
  },

  /** Activity feed events. */
  getActivityEvents: async (): Promise<ActivityEvent[]> => {
    return mockData.getActivityEvents();
  },

  /** Full incidents with investigation details. */
  getFullIncidents: async (): Promise<FullIncident[]> => {
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
};
