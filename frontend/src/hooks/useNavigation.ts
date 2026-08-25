import { useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useInvestigation } from '../context/InvestigationContext';

export function useNavigation() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const investigation = useInvestigation();

  const navigateToMerchant = useCallback((merchantId: string) => {
    investigation.setMerchant(merchantId);
    investigation.clearPath();
    investigation.pushPath('Mission Control');
    navigate(`/merchants?merchant=${merchantId}`);
  }, [navigate, investigation]);

  const navigateToMerchantFromActivity = useCallback((merchantId: string) => {
    investigation.setMerchant(merchantId);
    investigation.pushPath('Activity');
    navigate(`/merchants?merchant=${merchantId}`);
  }, [navigate, investigation]);

  const navigateToIncident = useCallback((incidentId: string) => {
    investigation.setIncident(incidentId);
    investigation.clearPath();
    investigation.pushPath('Incidents');
    navigate(`/incidents?incident=${incidentId}`);
  }, [navigate, investigation]);

  const navigateToIncidentFromActivity = useCallback((incidentId: string, merchantId?: string) => {
    investigation.setIncident(incidentId);
    if (merchantId) investigation.setMerchant(merchantId);
    investigation.pushPath('Activity');
    navigate(`/incidents?incident=${incidentId}`);
  }, [navigate, investigation]);

  const navigateToActivity = useCallback((merchantId?: string, eventId?: string) => {
    if (merchantId) investigation.setMerchant(merchantId);
    if (eventId) investigation.setActivityEvent(eventId);
    const params = new URLSearchParams();
    if (merchantId) params.set('merchant', merchantId);
    if (eventId) params.set('event', eventId);
    investigation.pushPath('Activity');
    navigate(`/activity${params.toString() ? '?' + params.toString() : ''}`);
  }, [navigate, investigation]);

  const navigateToMissionControl = useCallback(() => {
    investigation.clearPath();
    navigate('/');
  }, [navigate, investigation]);

  const getSearchParam = useCallback((key: string): string | null => {
    return searchParams.get(key);
  }, [searchParams]);

  return {
    navigateToMerchant,
    navigateToMerchantFromActivity,
    navigateToIncident,
    navigateToIncidentFromActivity,
    navigateToActivity,
    navigateToMissionControl,
    getSearchParam,
    currentParams: Object.fromEntries(searchParams.entries()),
  };
}
