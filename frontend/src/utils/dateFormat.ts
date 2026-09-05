/**
 * Shared date formatting utility for SUS.
 *
 * All dates in the application flow through this module to ensure
 * consistent timezone handling and display format.
 *
 * Backend stores timestamps in UTC (with Z suffix).
 * This module converts them to the browser's local timezone.
 */

/**
 * Format an ISO timestamp for display.
 * Converts UTC to browser-local timezone automatically.
 *
 * Examples (IST):
 *   "2026-09-05T11:32:00Z" → "Sep 5, 2026 · 5:02 PM"
 *   "2025-07-01"            → "Jul 1, 2025"
 */
export function formatDateTime(isoString: string): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    // Check for invalid date
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

/**
 * Format a date-only string (no time component).
 * Used for transaction dates, window dates, etc.
 *
 * Examples:
 *   "2025-07-01" → "Jul 1, 2025"
 */
export function formatDate(isoString: string): string {
  if (!isoString) return '—';
  try {
    // For date-only strings (YYYY-MM-DD), parse as UTC to avoid timezone shifts
    const dateStr = isoString.includes('T') ? isoString : `${isoString}T00:00:00Z`;
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return isoString;
  }
}

/**
 * Format a short date for compact UI (history cards, recent investigations).
 *
 * Examples (IST):
 *   "2026-09-05T11:32:00Z" → "Sep 5, 5:02 PM"
 */
export function formatDateTimeShort(isoString: string): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

/**
 * Format a relative time (e.g., "2 minutes ago", "1 hour ago").
 */
export function formatRelativeTime(isoString: string): string {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHr = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHr / 24);

    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    // Fall back to absolute date for older
    return formatDate(isoString);
  } catch {
    return isoString;
  }
}

/**
 * Get a display-friendly transaction date range from ISO strings.
 *
 * Examples:
 *   ("2025-07-01", "2025-08-24") → "Jul 1 – Aug 24, 2025"
 *   ("2025-07-01", "2025-07-31") → "Jul 1 – Jul 31, 2025"
 *   ("2025-01-01", "2026-01-01") → "Jan 1, 2025 – Jan 1, 2026"
 */
export function formatDateRange(startIso: string, endIso: string): string {
  if (!startIso || !endIso) return '—';
  try {
    const start = new Date(`${startIso}T00:00:00Z`);
    const end = new Date(`${endIso}T00:00:00Z`);
    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      return `${startIso} → ${endIso}`;
    }

    const startYear = start.getFullYear();
    const endYear = end.getFullYear();
    const startStr = start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const endStr = end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    if (startYear === endYear) {
      return `${startStr} – ${endStr}`;
    }
    return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} – ${endStr}`;
  } catch {
    return `${startIso} → ${endIso}`;
  }
}
