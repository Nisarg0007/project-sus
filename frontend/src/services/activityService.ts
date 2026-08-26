/**
 * Activity Service (Frontend)
 */

import { getActivityEvents } from '../api/activity';
import { mapActivityEvent } from '../api/mappers/activityMapper';
import type { ActivityEvent } from '../types';
import type { ServiceResult } from './investigationService';

export async function fetchActivityEvents(params?: {
  merchantId?: string;
  dateFrom?: string;
  dateTo?: string;
  status?: string;
  limit?: number;
}): Promise<ServiceResult<ActivityEvent[]>> {
  const response = await getActivityEvents(params);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch activity events' } };
  }
  return {
    data: response.data.events.map(mapActivityEvent),
    error: null,
  };
}
