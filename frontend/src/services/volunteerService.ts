import { fetchWithFallback, ApiResponse } from './api';
import { VolunteerTask, VulnerableHousehold, TaskStatus } from '../types';
import { INITIAL_TASKS, INITIAL_VULNERABLE } from './mockData';

export const volunteerService = {
  async getTasks(): Promise<ApiResponse<VolunteerTask[]>> {
    return fetchWithFallback<VolunteerTask[]>('/api/volunteer/tasks', { method: 'GET' }, () => INITIAL_TASKS);
  },

  async getVulnerableHouseholds(): Promise<ApiResponse<VulnerableHousehold[]>> {
    return fetchWithFallback<VulnerableHousehold[]>(
      '/api/vulnerable/households',
      { method: 'GET' },
      () => INITIAL_VULNERABLE
    );
  },

  async updateTaskStatus(taskId: string, status: TaskStatus): Promise<ApiResponse<any>> {
    return fetchWithFallback<any>(
      `/api/volunteer/tasks/${taskId}`,
      { method: 'PATCH', body: JSON.stringify({ status }) },
      () => ({ success: true, taskId, status })
    );
  },
};
