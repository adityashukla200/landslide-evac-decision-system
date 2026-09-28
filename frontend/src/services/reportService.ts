import { fetchWithFallback, ApiResponse } from './api';
import { CommunityReport } from '../types';
import { INITIAL_REPORTS } from './mockData';

export interface CreateReportPayload {
  villageId?: string;
  lat: number;
  lon: number;
  hazardType: string;
  text: string;
  photoUrl?: string;
  reporterName?: string;
  reporterPhone?: string;
}

export const reportService = {
  async getReports(): Promise<ApiResponse<CommunityReport[]>> {
    return fetchWithFallback<CommunityReport[]>('/api/reports', { method: 'GET' }, () => INITIAL_REPORTS);
  },

  async submitReport(payload: CreateReportPayload): Promise<ApiResponse<CommunityReport>> {
    const mockCreated = (): CommunityReport => ({
      id: `REP_${Date.now()}`,
      villageId: payload.villageId,
      lat: payload.lat,
      lon: payload.lon,
      hazardType: payload.hazardType as any,
      text: payload.text,
      photoUrl: payload.photoUrl,
      reporterName: payload.reporterName || 'Citizen Reporter',
      reporterPhone: payload.reporterPhone,
      status: 'PENDING_REVIEW',
      isGroundTruthCandidate: true,
      createdAt: 'Just now',
    });

    return fetchWithFallback<CommunityReport>(
      '/api/reports',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      mockCreated
    );
  },

  async reviewReport(
    reportId: string,
    status: 'VERIFIED' | 'REJECTED',
    reviewedBy: string,
    reviewNotes?: string
  ): Promise<ApiResponse<any>> {
    return fetchWithFallback<any>(
      `/api/reports/${reportId}/review`,
      {
        method: 'PUT',
        body: JSON.stringify({
          status,
          reviewed_by: reviewedBy,
          review_notes: reviewNotes,
          is_ground_truth_candidate: status === 'VERIFIED',
        }),
      },
      () => ({ status: 'UPDATED', report_id: reportId, review_status: status })
    );
  },
};
