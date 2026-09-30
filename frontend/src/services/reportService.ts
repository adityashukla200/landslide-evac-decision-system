import { fetchWithFallback, ApiResponse, BACKEND_URL } from './api';
import { CommunityReport } from '../types';
import { INITIAL_REPORTS } from './mockData';
import { authService } from './authService';

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

export interface CitizenReportItem {
  id: string;
  village_id?: string | null;
  village_name?: string | null;
  distance_from_village_km?: number | null;
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  media_type: 'photo' | 'video';
  media_url: string;
  thumbnail_url?: string | null;
  caption?: string | null;
  reported_flood: boolean;
  reporter_phone?: string | null;
  status: 'pending' | 'verified' | 'rejected' | 'duplicate';
  created_at?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  audit_log?: any[];
}

export interface QueuedOfflineReport {
  id: string;
  latitude: number;
  longitude: number;
  accuracy_meters?: number;
  reported_flood: boolean;
  caption?: string;
  reporter_phone?: string;
  fileName: string;
  fileType: string;
  fileDataUrl: string; // Base64 data URL
  timestamp: number;
}

const OFFLINE_QUEUE_KEY = 'ews_offline_citizen_reports_queue';

export const reportService = {
  // Legacy Community Reports
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

  // ---------------------------------------------------------
  // Ground-Truth Citizen Reports (Photo/Video Geotagged)
  // ---------------------------------------------------------

  async getCitizenReports(
    villageIdOrOptions?: string | { village_id?: string; villageId?: string; status?: string; limit?: number },
    statusFilter?: string
  ): Promise<CitizenReportItem[]> {
    const targetVillageId =
      typeof villageIdOrOptions === 'object' && villageIdOrOptions !== null
        ? villageIdOrOptions.village_id || villageIdOrOptions.villageId
        : typeof villageIdOrOptions === 'string'
        ? villageIdOrOptions
        : undefined;

    try {
      const params = new URLSearchParams();
      if (typeof villageIdOrOptions === 'object' && villageIdOrOptions !== null) {
        if (targetVillageId) params.append('village_id', targetVillageId);
        if (villageIdOrOptions.status) params.append('status', villageIdOrOptions.status);
        if (villageIdOrOptions.limit) params.append('limit', villageIdOrOptions.limit.toString());
      } else {
        if (typeof villageIdOrOptions === 'string') params.append('village_id', villageIdOrOptions);
        if (statusFilter) params.append('status', statusFilter);
      }

      const url = `${BACKEND_URL}/api/v1/reports${params.toString() ? `?${params.toString()}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return (data as CitizenReportItem[]).map((r) => ({
        ...r,
        media_url: r.media_url.startsWith('http') ? r.media_url : `${BACKEND_URL}${r.media_url}`,
        thumbnail_url: r.thumbnail_url
          ? r.thumbnail_url.startsWith('http')
            ? r.thumbnail_url
            : `${BACKEND_URL}${r.thumbnail_url}`
          : null,
      }));
    } catch {
      // Mock fallback if offline or backend unavailable
      return [
        {
          id: 'CR_MOCK_01',
          village_id: targetVillageId || 'VIL_UTK_07',
          village_name: 'Bhatwari',
          distance_from_village_km: 0.8,
          latitude: 30.816,
          longitude: 78.62,
          accuracy_meters: 10,
          media_type: 'photo',
          media_url: 'https://images.unsplash.com/photo-1547683905-f686c993aae5?auto=format&fit=crop&w=800&q=80',
          thumbnail_url: 'https://images.unsplash.com/photo-1547683905-f686c993aae5?auto=format&fit=crop&w=300&q=80',
          caption: 'Water overflowing over highway bridge culvert.',
          reported_flood: true,
          reporter_phone: '+91 98*** **210',
          status: 'pending',
          created_at: new Date(Date.now() - 25 * 60000).toISOString(),
        },
        {
          id: 'CR_MOCK_02',
          village_id: targetVillageId || 'VIL_UTK_01',
          village_name: 'Harsil',
          distance_from_village_km: 1.4,
          latitude: 31.038,
          longitude: 78.74,
          accuracy_meters: 15,
          media_type: 'photo',
          media_url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80',
          thumbnail_url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=300&q=80',
          caption: 'Stream clear, water normal. False alarm.',
          reported_flood: false,
          reporter_phone: '+91 98*** **842',
          status: 'verified',
          created_at: new Date(Date.now() - 85 * 60000).toISOString(),
        },
      ];
    }
  },

  async submitCitizenReportMultipart(
    formData: FormData,
    onProgress?: (percent: number) => void
  ): Promise<{ status: string; report_id: string; message: string }> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${BACKEND_URL}/api/v1/reports/citizen`);

      if (onProgress && xhr.upload) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            onProgress(pct);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            resolve(data);
          } catch {
            resolve({ status: 'success', report_id: 'CR_OK', message: 'Report received' });
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || `Upload failed with status ${xhr.status}`));
          } catch {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      };

      xhr.onerror = () => {
        reject(new Error('Network error during upload'));
      };

      xhr.send(formData);
    });
  },

  async updateCitizenReportStatus(
    reportId: string,
    newStatus: 'pending' | 'verified' | 'rejected' | 'duplicate',
    reviewedBy: string = 'District Officer',
    notes?: string
  ): Promise<any> {
    try {
      const token = authService.getAccessToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${BACKEND_URL}/api/v1/reports/${reportId}/status`, {
        method: 'PUT',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          status: newStatus,
          reviewed_by: reviewedBy,
          notes,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch {
      return { status: 'success', report_id: reportId, new_status: newStatus };
    }
  },

  // ---------------------------------------------------------
  // Offline Queueing & Sync (PWA Local Storage)
  // ---------------------------------------------------------

  getQueuedOfflineReports(): QueuedOfflineReport[] {
    try {
      const raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  queueOfflineReport(report: QueuedOfflineReport): void {
    const list = this.getQueuedOfflineReports();
    list.push(report);
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(list));
  },

  removeQueuedReport(id: string): void {
    const list = this.getQueuedOfflineReports().filter((r) => r.id !== id);
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(list));
  },

  async flushOfflineReports(
    onReportSynced?: (id: string) => void
  ): Promise<{ synced: number; failed: number }> {
    const queue = this.getQueuedOfflineReports();
    if (queue.length === 0) return { synced: 0, failed: 0 };

    let synced = 0;
    let failed = 0;

    for (const item of queue) {
      try {
        // Convert Base64 data URL back to Blob
        const res = await fetch(item.fileDataUrl);
        const blob = await res.blob();
        const file = new File([blob], item.fileName, { type: item.fileType });

        const formData = new FormData();
        formData.append('file', file);
        formData.append('latitude', item.latitude.toString());
        formData.append('longitude', item.longitude.toString());
        if (item.accuracy_meters) formData.append('accuracy_meters', item.accuracy_meters.toString());
        formData.append('reported_flood', item.reported_flood.toString());
        if (item.caption) formData.append('caption', item.caption);
        if (item.reporter_phone) formData.append('reporter_phone', item.reporter_phone);

        await this.submitCitizenReportMultipart(formData);
        this.removeQueuedReport(item.id);
        synced++;
        if (onReportSynced) onReportSynced(item.id);
      } catch (e) {
        logger_warn(`Failed to flush queued report ${item.id}`, e);
        failed++;
      }
    }

    return { synced, failed };
  },
};

export const getCitizenReports = reportService.getCitizenReports.bind(reportService);
export const submitCitizenReportMultipart = reportService.submitCitizenReportMultipart.bind(reportService);
export const updateCitizenReportStatus = reportService.updateCitizenReportStatus.bind(reportService);

function logger_warn(msg: string, err: any) {
  if (import.meta.env.DEV) {
    console.warn(`[OfflineReportSync] ${msg}`, err);
  }
}

