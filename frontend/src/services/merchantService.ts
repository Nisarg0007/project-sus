/**
 * Merchant Service (Frontend)
 *
 * High-level service for merchant data access.
 */

import { getMerchants, getMerchantProfile } from '../api/merchants';
import {
  mapMerchantListItem,
  mapMerchantDirectoryItem,
  mapMerchantProfile,
} from '../api/mappers/merchantMapper';
import type { Merchant, MerchantDirectoryItem, MerchantProfile } from '../types';
import type { ServiceResult } from './investigationService';

export async function fetchMerchants(): Promise<ServiceResult<Merchant[]>> {
  const response = await getMerchants();
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch merchants' } };
  }
  return {
    data: response.data.merchants.map(mapMerchantListItem),
    error: null,
  };
}

export async function fetchMerchantDirectory(): Promise<ServiceResult<MerchantDirectoryItem[]>> {
  const response = await getMerchants();
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch merchant directory' } };
  }
  return {
    data: response.data.merchants.map(mapMerchantDirectoryItem),
    error: null,
  };
}

export async function fetchMerchantProfile(id: string): Promise<ServiceResult<MerchantProfile>> {
  const response = await getMerchantProfile(id);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: `Failed to fetch merchant profile: ${id}` } };
  }
  return {
    data: mapMerchantProfile(response.data),
    error: null,
  };
}
