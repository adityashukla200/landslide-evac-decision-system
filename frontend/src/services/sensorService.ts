import { fetchWithFallback, ApiResponse } from './api';
import { Sensor } from '../types';
import { INITIAL_SENSORS } from './mockData';

export const sensorService = {
  async getSensors(): Promise<ApiResponse<Sensor[]>> {
    return fetchWithFallback<Sensor[]>('/api/sensors', { method: 'GET' }, () => INITIAL_SENSORS);
  },
};
