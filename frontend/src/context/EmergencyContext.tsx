import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  Village,
  Sensor,
  Route,
  Shelter,
  Alert,
  VolunteerTask,
  CommunityReport,
  ScenarioType,
  RiskTier,
} from '../types';
import {
  INITIAL_VILLAGES,
  INITIAL_SENSORS,
  INITIAL_ROUTES,
  INITIAL_SHELTERS,
  INITIAL_ALERTS,
  INITIAL_TASKS,
  INITIAL_REPORTS,
  getScenarioData,
} from '../services/mockData';
import { alertService } from '../services/alertService';
import { reportService, CreateReportPayload } from '../services/reportService';

interface SimulationParams {
  rainfallIncreasePct: number;    // -50% to +100%
  soilSaturationIncreasePct: number; // -30% to +50%
  upstreamInflowIncreasePct: number; // -50% to +100%
}

interface EmergencyContextType {
  scenario: ScenarioType;
  setScenario: (sc: ScenarioType) => void;
  villages: Village[];
  sensors: Sensor[];
  routes: Route[];
  shelters: Shelter[];
  alerts: Alert[];
  tasks: VolunteerTask[];
  reports: CommunityReport[];
  selectedVillage: Village | null;
  setSelectedVillage: (v: Village | null) => void;
  isOnline: boolean;
  setIsOnline: (online: boolean) => void;
  lastUpdated: string;
  triggerEmergencyAlert: (villageId: string, tier: RiskTier, customMessage?: string) => Promise<void>;
  submitHazardReport: (payload: CreateReportPayload) => Promise<void>;
  updateTaskStatus: (taskId: string, status: VolunteerTask['status']) => void;
  simulationParams: SimulationParams;
  setSimulationParams: React.Dispatch<React.SetStateAction<SimulationParams>>;
  simulatedVillages: Village[];
}

const EmergencyContext = createContext<EmergencyContextType | undefined>(undefined);

export const EmergencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [scenario, setScenarioState] = useState<ScenarioType>('FLASH_FLOOD');
  const [villages, setVillages] = useState<Village[]>(INITIAL_VILLAGES);
  const [sensors, setSensors] = useState<Sensor[]>(INITIAL_SENSORS);
  const [routes, setRoutes] = useState<Route[]>(INITIAL_ROUTES);
  const [shelters, setShelters] = useState<Shelter[]>(INITIAL_SHELTERS);
  const [alerts, setAlerts] = useState<Alert[]>(INITIAL_ALERTS);
  const [tasks, setTasks] = useState<VolunteerTask[]>(INITIAL_TASKS);
  const [reports, setReports] = useState<CommunityReport[]>(INITIAL_REPORTS);
  const [selectedVillage, setSelectedVillage] = useState<Village | null>(INITIAL_VILLAGES[2]); // Default Maneri
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [lastUpdated, setLastUpdated] = useState<string>(new Date().toLocaleTimeString());

  const [simulationParams, setSimulationParams] = useState<SimulationParams>({
    rainfallIncreasePct: 0,
    soilSaturationIncreasePct: 0,
    upstreamInflowIncreasePct: 0,
  });

  // Track online/offline browser events
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Update data based on scenario switch
  const setScenario = (newScenario: ScenarioType) => {
    setScenarioState(newScenario);
    const data = getScenarioData(newScenario);
    setVillages(data.villages);
    setSensors(data.sensors);
    setAlerts(data.alerts);
    setRoutes(data.routes);
    setLastUpdated(new Date().toLocaleTimeString());

    if (selectedVillage) {
      const updated = data.villages.find((v) => v.id === selectedVillage.id);
      if (updated) setSelectedVillage(updated);
    }
  };

  // Trigger emergency alert
  const triggerEmergencyAlert = async (villageId: string, tier: RiskTier, customMessage?: string) => {
    const v = villages.find((item) => item.id === villageId);
    const villageName = v ? v.name : villageId;

    const message = customMessage || `${tier} DIRECTIVE: Severe flash flood threat at ${villageName}. Follow marked ridge routes immediately.`;

    const res = await alertService.triggerAlert({
      villageId,
      tier,
      message,
    });

    const newAlert: Alert = {
      id: res.data.alert_id || `ALT_${Date.now()}`,
      villageId,
      villageName,
      tier,
      message,
      created_at: 'Just now',
      leadTimeMinutes: v ? v.risk.leadTimeMinutes : 30,
      targetPopulation: v ? v.population : 3000,
      reachPct: 95.0,
      ackPct: 65.0,
      deliveries: [
        { id: 'D_CB', channel: 'CELL_BROADCAST', status: 'SENT', sentAt: 'Just now' },
        { id: 'D_SMS', channel: 'SMS', status: 'SENT', sentAt: 'Just now' },
        { id: 'D_IVR', channel: 'IVR', status: 'SENT', sentAt: 'Just now' },
        { id: 'D_VOL', channel: 'VOLUNTEER', status: 'SENT', sentAt: 'Just now' },
        { id: 'D_SIR', channel: 'SIREN', status: tier === 'EVACUATE' ? 'SENT' : 'PENDING', sentAt: 'Just now' },
      ],
    };

    setAlerts((prev) => [newAlert, ...prev]);

    // Update village tier in state
    setVillages((prev) =>
      prev.map((item) => (item.id === villageId ? { ...item, risk: { ...item.risk, tier } } : item))
    );
  };

  // Submit crowd-sourced hazard report
  const submitHazardReport = async (payload: CreateReportPayload) => {
    const res = await reportService.submitReport(payload);
    setReports((prev) => [res.data, ...prev]);
  };

  // Volunteer task status transition
  const updateTaskStatus = (taskId: string, status: VolunteerTask['status']) => {
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status } : t)));
  };

  // Compute simulated villages based on What-If parameters
  const simulatedVillages: Village[] = villages.map((v) => {
    const rainFactor = 1 + simulationParams.rainfallIncreasePct / 100;
    const soilFactor = 1 + simulationParams.soilSaturationIncreasePct / 100;
    const upstreamFactor = 1 + simulationParams.upstreamInflowIncreasePct / 100;

    let baseProb = v.risk.probability;
    let newProb = Math.min(0.99, Math.max(0.01, baseProb * rainFactor * (0.5 + 0.5 * soilFactor) * (0.7 + 0.3 * upstreamFactor)));
    let newFos = Math.max(0.75, v.risk.explanation.factorOfSafety / (rainFactor * 0.5 + soilFactor * 0.5));

    let tier: RiskTier = 'NONE';
    if (newProb >= 0.70 || newFos <= 1.05) tier = 'EVACUATE';
    else if (newProb >= 0.40 || newFos <= 1.20) tier = 'WARNING';
    else if (newProb >= 0.15 || newFos <= 1.45) tier = 'WATCH';

    const simLead = Math.max(15, Math.round(v.risk.leadTimeMinutes / rainFactor));

    return {
      ...v,
      risk: {
        ...v.risk,
        probability: Number(newProb.toFixed(2)),
        tier,
        leadTimeMinutes: simLead,
        explanation: {
          ...v.risk.explanation,
          factorOfSafety: Number(newFos.toFixed(2)),
          currentRainfallRateMmH: Number((v.risk.explanation.currentRainfallRateMmH * rainFactor).toFixed(1)),
          soilSaturationPct: Math.min(100, Number((v.risk.explanation.soilSaturationPct * soilFactor).toFixed(1))),
        },
      },
    };
  });

  return (
    <EmergencyContext.Provider
      value={{
        scenario,
        setScenario,
        villages,
        sensors,
        routes,
        shelters,
        alerts,
        tasks,
        reports,
        selectedVillage,
        setSelectedVillage,
        isOnline,
        setIsOnline,
        lastUpdated,
        triggerEmergencyAlert,
        submitHazardReport,
        updateTaskStatus,
        simulationParams,
        setSimulationParams,
        simulatedVillages,
      }}
    >
      {children}
    </EmergencyContext.Provider>
  );
};

export const useEmergency = () => {
  const context = useContext(EmergencyContext);
  if (!context) throw new Error('useEmergency must be used within an EmergencyProvider');
  return context;
};
