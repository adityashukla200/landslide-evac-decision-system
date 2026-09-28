import { fetchWithFallback, ApiResponse } from './api';
import { Alert, RiskTier } from '../types';
import { INITIAL_ALERTS } from './mockData';

export interface TriggerAlertPayload {
  villageId: string;
  tier: RiskTier;
  message?: string;
  isDrill?: boolean;
  overrideCooldown?: boolean;
}

export const alertService = {
  async getAlerts(): Promise<ApiResponse<Alert[]>> {
    return fetchWithFallback<Alert[]>(
      '/api/alerts',
      { method: 'GET' },
      () => INITIAL_ALERTS
    );
  },

  async triggerAlert(payload: TriggerAlertPayload): Promise<ApiResponse<any>> {
    const mockSuccess = () => ({
      status: 'DISPATCHED',
      alert_id: `ALT_${Date.now()}`,
      village_id: payload.villageId,
      tier: payload.tier,
      message: payload.message || `Emergency ${payload.tier} Directive issued.`,
      is_drill: Boolean(payload.isDrill),
      ladder_execution: {
        status: 'COMPLETED',
        deliveries_count: 5,
      },
    });

    return fetchWithFallback<any>(
      '/api/alerts/trigger',
      {
        method: 'POST',
        body: JSON.stringify({
          village_id: payload.villageId,
          tier: payload.tier,
          message: payload.message,
          is_drill: payload.isDrill || false,
          override_cooldown: payload.overrideCooldown || false,
        }),
      },
      mockSuccess
    );
  },

  async acknowledgeAlert(alertId: string, recipientId: string): Promise<ApiResponse<any>> {
    return fetchWithFallback<any>(
      '/api/alerts/ack',
      {
        method: 'POST',
        body: JSON.stringify({ alert_id: alertId, recipient_id: recipientId }),
      },
      () => ({ status: 'ACKNOWLEDGED', alert_id: alertId, recipient_id: recipientId })
    );
  },

  async getCapXml(alertId: string): Promise<ApiResponse<string>> {
    const mockXml = `<?xml version="1.0" encoding="utf-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>IN-UK-UTK-${alertId}</identifier>
  <sender>deoc.uttarkashi@uk.gov.in</sender>
  <sent>${new Date().toISOString()}</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <language>en-IN</language>
    <category>Geo</category>
    <event>Landslide / Flash Flood Directive</event>
    <urgency>Immediate</urgency>
    <severity>Extreme</severity>
    <certainty>Observed</certainty>
    <headline>EVACUATE DIRECTIVE: Uttarkashi District</headline>
    <description>Move immediately to designated refuge shelters via marked ridge footpaths.</description>
    <instruction>Avoid valley bottoms and riverbanks.</instruction>
  </info>
</alert>`;

    return fetchWithFallback<string>(
      `/api/alerts/${alertId}/cap`,
      { method: 'GET' },
      () => mockXml
    );
  },
};
