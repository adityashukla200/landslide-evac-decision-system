import { fetchWithFallback, ApiResponse } from './api';
import { Route, Shelter } from '../types';
import { INITIAL_ROUTES, INITIAL_SHELTERS } from './mockData';

export interface EvacuationAssessment {
  villageId: string;
  timeToImpactLikelyMinutes: number;
  timeToEvacuateMinutes: number;
  availableMarginMinutes: number;
  alertStage: string;
  recommendedRoute: Route;
  targetShelter: Shelter;
  messages: {
    en: string;
    hi: string;
    gbm: string;
  };
}

export const evacuationService = {
  async getRoutes(): Promise<ApiResponse<Route[]>> {
    return fetchWithFallback<Route[]>('/api/routes', { method: 'GET' }, () => INITIAL_ROUTES);
  },

  async getShelters(): Promise<ApiResponse<Shelter[]>> {
    return fetchWithFallback<Shelter[]>('/api/shelters', { method: 'GET' }, () => INITIAL_SHELTERS);
  },

  async assessVillage(villageId: string): Promise<ApiResponse<EvacuationAssessment>> {
    const fallback = (): EvacuationAssessment => {
      const route = INITIAL_ROUTES.find((r) => r.fromVillageId === villageId && r.isRecommended) || INITIAL_ROUTES[1];
      const shelter = INITIAL_SHELTERS.find((s) => s.id === route.toShelterId) || INITIAL_SHELTERS[0];

      return {
        villageId,
        timeToImpactLikelyMinutes: 48,
        timeToEvacuateMinutes: route.estWalkMinutes,
        availableMarginMinutes: Math.max(0, 48 - route.estWalkMinutes),
        alertStage: 'WARNING',
        recommendedRoute: route,
        targetShelter: shelter,
        messages: {
          en: `Leave now. Go via ${route.name} to ${shelter.name}. You have about 28 minutes.`,
          hi: `तुरंत निकलें। ${route.name} से ${shelter.name} की ओर जाएं। आपके पास लगभग 28 मिनट हैं।`,
          gbm: `अबल ही निकलो। ${route.name} से ${shelter.name} जांवा।`,
        },
      };
    };

    return fetchWithFallback<EvacuationAssessment>(
      `/api/assess/${villageId}`,
      { method: 'POST' },
      fallback
    );
  },
};
