import { fetchWithFallback, ApiResponse } from './api';
import { Village, RiskAssessment } from '../types';
import { INITIAL_VILLAGES } from './mockData';

export const riskService = {
  async getVillages(): Promise<ApiResponse<Village[]>> {
    return fetchWithFallback<Village[]>(
      '/api/v1/villages',
      { method: 'GET' },
      () => INITIAL_VILLAGES
    );
  },

  async getVillageRisk(villageId: string): Promise<ApiResponse<RiskAssessment | null>> {
    const fallback = () => {
      const match = INITIAL_VILLAGES.find((v) => v.id === villageId);
      return match ? match.risk : null;
    };

    return fetchWithFallback<RiskAssessment | null>(
      `/api/assess/${villageId}`,
      { method: 'POST' },
      fallback
    );
  },
};
