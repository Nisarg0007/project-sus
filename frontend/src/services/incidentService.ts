/**
 * Incident Service (Frontend)
 */

import { getIncidents } from '../api/incidentList';
import { mapIncidentListItem, mapToFullIncident } from '../api/mappers/incidentMapper';
import type { Incident, FullIncident } from '../types';
import type { ServiceResult } from './investigationService';

export async function fetchIncidents(params?: {
  merchantId?: string;
  severity?: string;
  classification?: string;
  status?: string;
  limit?: number;
}): Promise<ServiceResult<Incident[]>> {
  const response = await getIncidents(params);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch incidents' } };
  }
  return {
    data: response.data.incidents.map(mapIncidentListItem),
    error: null,
  };
}

export async function fetchFullIncidents(params?: {
  merchantId?: string;
  severity?: string;
  classification?: string;
  limit?: number;
}): Promise<ServiceResult<FullIncident[]>> {
  const response = await getIncidents(params);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch incidents' } };
  }
  return {
    data: response.data.incidents.map(mapToFullIncident),
    error: null,
  };
}
