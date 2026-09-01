/**
 * Transaction Upload API client.
 *
 * Methods for uploading and validating transaction CSVs.
 */

import { apiClient, type ApiResponse } from './client';

// ---------------------------------------------------------------------------
// Backend response types
// ---------------------------------------------------------------------------

export interface TransactionUploadResponse {
  dataset_id: string;
  original_filename: string;
  source_name: string;
  transactions_path: string;
  window_labels_path: string | null;
}

export interface TransactionValidationResponse {
  is_valid: boolean;
  total_rows: number;
  valid_rows: number;
  error_count: number;
  warning_count: number;
  errors: string[];
  warnings: string[];
  unique_merchants: number | null;
  date_range_start: string | null;
  date_range_end: string | null;
  amount_min: number | null;
  amount_max: number | null;
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export async function uploadTransactionCSV(
  file: File,
  windowLabelsFile?: File,
): Promise<ApiResponse<TransactionUploadResponse>> {
  const formData = new FormData();
  formData.append('file', file);
  if (windowLabelsFile) {
    formData.append('window_labels_file', windowLabelsFile);
  }
  return apiClient.upload<TransactionUploadResponse>(
    '/api/v1/transactions/upload',
    formData,
  );
}

export async function validateTransactionCSV(
  file: File,
): Promise<ApiResponse<TransactionValidationResponse>> {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.upload<TransactionValidationResponse>(
    '/api/v1/transactions/validate',
    formData,
  );
}
