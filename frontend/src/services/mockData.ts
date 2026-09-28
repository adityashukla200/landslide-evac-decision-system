import {
  Village,
  Sensor,
  Route,
  Shelter,
  Alert,
  VolunteerTask,
  VulnerableHousehold,
  CommunityReport,
  ScenarioType,
} from '../types';

export const INITIAL_VILLAGES: Village[] = [
  {
    id: 'VIL_UTK_01',
    name: 'Harsil',
    district: 'Uttarkashi',
    lat: 31.0345,
    lon: 78.7382,
    elevationM: 2745,
    population: 1850,
    vulnerablePop: 240,
    risk: {
      villageId: 'VIL_UTK_01',
      probability: 0.12,
      lowerBound: 0.08,
      upperBound: 0.18,
      tier: 'WATCH',
      leadTimeMinutes: 180,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 1.42,
        rainfall72hMm: 68.5,
        currentRainfallRateMmH: 12.4,
        soilSaturationPct: 62.0,
        slopeDeg: 36.5,
        upstreamRainfallIncreasing: true,
        analogMatch: {
          eventName: 'Bhagirathi Monsoon Surge 2021',
          similarityPct: 84.5,
          year: 2021,
          outcomeLandslide: false,
          description: 'High tributary discharge with localized bank scouring.',
        },
      },
    },
  },
  {
    id: 'VIL_UTK_07',
    name: 'Bhatwari',
    district: 'Uttarkashi',
    lat: 30.8172,
    lon: 78.6189,
    elevationM: 1218,
    population: 4218,
    vulnerablePop: 620,
    risk: {
      villageId: 'VIL_UTK_07',
      probability: 0.74,
      lowerBound: 0.62,
      upperBound: 0.86,
      tier: 'WARNING',
      leadTimeMinutes: 48,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 1.04,
        rainfall72hMm: 218.4,
        currentRainfallRateMmH: 38.6,
        soilSaturationPct: 91.5,
        slopeDeg: 41.2,
        upstreamRainfallIncreasing: true,
        analogMatch: {
          eventName: 'Bhatwari Debris Slide 2013',
          similarityPct: 92.1,
          year: 2013,
          outcomeLandslide: true,
          description: 'Severe toe erosion along NH-108 with multiple debris chutes activating.',
        },
      },
    },
  },
  {
    id: 'VIL_UTK_08',
    name: 'Maneri',
    district: 'Uttarkashi',
    lat: 30.7645,
    lon: 78.5321,
    elevationM: 1290,
    population: 3100,
    vulnerablePop: 410,
    risk: {
      villageId: 'VIL_UTK_08',
      probability: 0.88,
      lowerBound: 0.79,
      upperBound: 0.94,
      tier: 'EVACUATE',
      leadTimeMinutes: 28,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 0.94,
        rainfall72hMm: 265.0,
        currentRainfallRateMmH: 52.0,
        soilSaturationPct: 96.8,
        slopeDeg: 44.0,
        upstreamRainfallIncreasing: true,
        analogMatch: {
          eventName: 'Maneri Dam Flash Flood 2012',
          similarityPct: 94.8,
          year: 2012,
          outcomeLandslide: true,
          description: 'Rapid catchment saturation triggering rotational slope failure into reservoir.',
        },
      },
    },
  },
  {
    id: 'VIL_UTK_10',
    name: 'Uttarkashi Town (HQ)',
    district: 'Uttarkashi',
    lat: 30.7268,
    lon: 78.4354,
    elevationM: 1158,
    population: 17470,
    vulnerablePop: 2150,
    risk: {
      villageId: 'VIL_UTK_10',
      probability: 0.38,
      lowerBound: 0.28,
      upperBound: 0.48,
      tier: 'WATCH',
      leadTimeMinutes: 115,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 1.28,
        rainfall72hMm: 112.0,
        currentRainfallRateMmH: 22.0,
        soilSaturationPct: 74.5,
        slopeDeg: 28.0,
        upstreamRainfallIncreasing: true,
        analogMatch: {
          eventName: 'Tambakhani Slope Creep 2019',
          similarityPct: 79.2,
          year: 2019,
          outcomeLandslide: false,
          description: 'Rising water level in Bhagirathi; rockfall netting holding stable.',
        },
      },
    },
  },
  {
    id: 'VIL_UTK_11',
    name: 'Joshiyara',
    district: 'Uttarkashi',
    lat: 30.7198,
    lon: 78.4289,
    elevationM: 1150,
    population: 5800,
    vulnerablePop: 780,
    risk: {
      villageId: 'VIL_UTK_11',
      probability: 0.68,
      lowerBound: 0.54,
      upperBound: 0.81,
      tier: 'WARNING',
      leadTimeMinutes: 52,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 1.08,
        rainfall72hMm: 186.0,
        currentRainfallRateMmH: 34.5,
        soilSaturationPct: 88.0,
        slopeDeg: 34.0,
        upstreamRainfallIncreasing: true,
        analogMatch: {
          eventName: 'Joshiyara Barrage Inundation 2013',
          similarityPct: 88.4,
          year: 2013,
          outcomeLandslide: true,
          description: 'Low-lying riverbank settlement inundation and sediment deposition.',
        },
      },
    },
  },
  {
    id: 'VIL_UTK_15',
    name: 'Barkot',
    district: 'Uttarkashi',
    lat: 30.8123,
    lon: 78.2045,
    elevationM: 1220,
    population: 6710,
    vulnerablePop: 890,
    risk: {
      villageId: 'VIL_UTK_15',
      probability: 0.05,
      lowerBound: 0.02,
      upperBound: 0.10,
      tier: 'NONE',
      leadTimeMinutes: 360,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 1.85,
        rainfall72hMm: 32.0,
        currentRainfallRateMmH: 4.2,
        soilSaturationPct: 41.0,
        slopeDeg: 22.0,
        upstreamRainfallIncreasing: false,
      },
    },
  },
  {
    id: 'VIL_UTK_17',
    name: 'Purola',
    district: 'Uttarkashi',
    lat: 30.8745,
    lon: 78.0789,
    elevationM: 1524,
    population: 4920,
    vulnerablePop: 630,
    risk: {
      villageId: 'VIL_UTK_17',
      probability: 0.04,
      lowerBound: 0.01,
      upperBound: 0.08,
      tier: 'NONE',
      leadTimeMinutes: 400,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 1.92,
        rainfall72hMm: 28.0,
        currentRainfallRateMmH: 3.1,
        soilSaturationPct: 38.0,
        slopeDeg: 19.5,
        upstreamRainfallIncreasing: false,
      },
    },
  },
  {
    id: 'VIL_UTK_06',
    name: 'Gangnani',
    district: 'Uttarkashi',
    lat: 30.9082,
    lon: 78.6812,
    elevationM: 1855,
    population: 1420,
    vulnerablePop: 190,
    risk: {
      villageId: 'VIL_UTK_06',
      probability: 0.58,
      lowerBound: 0.44,
      upperBound: 0.72,
      tier: 'WARNING',
      leadTimeMinutes: 65,
      timestamp: new Date().toISOString(),
      explanation: {
        factorOfSafety: 1.12,
        rainfall72hMm: 164.0,
        currentRainfallRateMmH: 29.5,
        soilSaturationPct: 84.0,
        slopeDeg: 39.0,
        upstreamRainfallIncreasing: true,
      },
    },
  },
];

export const INITIAL_SENSORS: Sensor[] = [
  {
    id: 'SNS_RG_BHT_01',
    villageId: 'VIL_UTK_07',
    villageName: 'Bhatwari',
    type: 'RAIN_GAUGE',
    status: 'HEALTHY',
    batteryPct: 88,
    signalStrengthDbm: -68,
    lastUpdated: 'Just now',
    currentValue: 38.6,
    unit: 'mm/h',
    anomalyFlag: false,
  },
  {
    id: 'SNS_SM_BHT_02',
    villageId: 'VIL_UTK_07',
    villageName: 'Bhatwari',
    type: 'SOIL_MOISTURE',
    status: 'WARNING',
    batteryPct: 74,
    signalStrengthDbm: -78,
    lastUpdated: '1 min ago',
    currentValue: 91.5,
    unit: '% saturation',
    anomalyFlag: false,
  },
  {
    id: 'SNS_RS_MNR_01',
    villageId: 'VIL_UTK_08',
    villageName: 'Maneri',
    type: 'RIVER_STAGE',
    status: 'WARNING',
    batteryPct: 92,
    signalStrengthDbm: -64,
    lastUpdated: 'Just now',
    currentValue: 4.82,
    unit: 'meters (gauge)',
    anomalyFlag: false,
  },
  {
    id: 'SNS_TL_MNR_02',
    villageId: 'VIL_UTK_08',
    villageName: 'Maneri',
    type: 'TILT_METER',
    status: 'HEALTHY',
    batteryPct: 81,
    signalStrengthDbm: -72,
    lastUpdated: '2 min ago',
    currentValue: 2.14,
    unit: 'degrees tilt',
    anomalyFlag: false,
  },
  {
    id: 'SNS_SM_JSH_01',
    villageId: 'VIL_UTK_11',
    villageName: 'Joshiyara',
    type: 'SOIL_MOISTURE',
    status: 'FAULT',
    batteryPct: 18,
    signalStrengthDbm: -95,
    lastUpdated: '18 min ago',
    currentValue: 12.0,
    unit: '% saturation',
    anomalyFlag: true,
    anomalyDetails: 'Sensor reading differs significantly (-76%) from 3 adjacent ridge telemetry nodes.',
  },
  {
    id: 'SNS_RG_HRS_01',
    villageId: 'VIL_UTK_01',
    villageName: 'Harsil',
    type: 'RAIN_GAUGE',
    status: 'HEALTHY',
    batteryPct: 95,
    signalStrengthDbm: -60,
    lastUpdated: 'Just now',
    currentValue: 12.4,
    unit: 'mm/h',
    anomalyFlag: false,
  },
];

export const INITIAL_SHELTERS: Shelter[] = [
  {
    id: 'SHL_BHT_01',
    villageId: 'VIL_UTK_07',
    name: 'Bhatwari Inter College High Ground Hall',
    capacity: 450,
    currentOccupancy: 185,
    lat: 30.8210,
    lon: 78.6225,
    distanceKm: 1.2,
    amenities: { medical: true, water: true, food: true, backupPower: true },
    contactPerson: 'Master Virender Rawat',
    contactPhone: '+919412087654',
  },
  {
    id: 'SHL_MNR_02',
    villageId: 'VIL_UTK_08',
    name: 'Maneri Community Center Ridge Shelter',
    capacity: 350,
    currentOccupancy: 280,
    lat: 30.7690,
    lon: 78.5380,
    distanceKm: 1.8,
    amenities: { medical: true, water: true, food: true, backupPower: true },
    contactPerson: 'Smt. Anita Devi (Gram Pradhan)',
    contactPhone: '+919412098765',
  },
  {
    id: 'SHL_JSH_03',
    villageId: 'VIL_UTK_11',
    name: 'Joshiyara Government Polytechnic Campus',
    capacity: 600,
    currentOccupancy: 120,
    lat: 30.7240,
    lon: 78.4320,
    distanceKm: 0.9,
    amenities: { medical: true, water: true, food: true, backupPower: true },
    contactPerson: 'Er. Rajesh Pant',
    contactPhone: '+919876501234',
  },
  {
    id: 'SHL_HRS_04',
    villageId: 'VIL_UTK_01',
    name: 'Harsil GMVN High Ridge Tourist Lodge',
    capacity: 250,
    currentOccupancy: 45,
    lat: 31.0380,
    lon: 78.7420,
    distanceKm: 0.8,
    amenities: { medical: false, water: true, food: true, backupPower: true },
    contactPerson: 'Sundar Singh Rana',
    contactPhone: '+919876543201',
  },
];

export const INITIAL_ROUTES: Route[] = [
  {
    id: 'ROT_BHT_01_A',
    fromVillageId: 'VIL_UTK_07',
    toShelterId: 'SHL_BHT_01',
    name: 'Route A (Riverbank Valley Trail)',
    lengthKm: 1.1,
    estWalkMinutes: 22,
    cutRisk: 0.85,
    isBlocked: true,
    isRecommended: false,
    description: 'Blocked due to active mudflow & stream overflow across culvert #4.',
  },
  {
    id: 'ROT_BHT_01_B',
    fromVillageId: 'VIL_UTK_07',
    toShelterId: 'SHL_BHT_01',
    name: 'Route B (Upper Hillside Pine Forest Ridge Trail)',
    lengthKm: 1.8,
    estWalkMinutes: 34,
    cutRisk: 0.12,
    isBlocked: false,
    isRecommended: true,
    description: 'Clear, stable bedrock footpath with safety railings installed.',
  },
  {
    id: 'ROT_MNR_02_A',
    fromVillageId: 'VIL_UTK_08',
    toShelterId: 'SHL_MNR_02',
    name: 'Route A (Dam Access Road)',
    lengthKm: 2.1,
    estWalkMinutes: 40,
    cutRisk: 0.72,
    isBlocked: true,
    isRecommended: false,
    description: 'Heavy seepage and rockfall risk near bypass tunnel inlet.',
  },
  {
    id: 'ROT_MNR_02_B',
    fromVillageId: 'VIL_UTK_08',
    toShelterId: 'SHL_MNR_02',
    name: 'Route B (Old Temple Ridge Footway)',
    lengthKm: 1.6,
    estWalkMinutes: 28,
    cutRisk: 0.18,
    isBlocked: false,
    isRecommended: true,
    description: 'Highest safety margin, steered clear of debris chutes.',
  },
];

export const INITIAL_ALERTS: Alert[] = [
  {
    id: 'ALT_20260928_MNR_01',
    villageId: 'VIL_UTK_08',
    villageName: 'Maneri',
    tier: 'EVACUATE',
    message: 'Leave now. Go via Route B (Temple Ridge) to Shelter 2. Estimated impact in 28 minutes. Avoid the dam road.',
    created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    leadTimeMinutes: 28,
    targetPopulation: 3100,
    isDrill: false,
    reachPct: 94.2,
    ackPct: 76.8,
    deliveries: [
      { id: 'D1', channel: 'CELL_BROADCAST', status: 'SENT', sentAt: '12m ago' },
      { id: 'D2', channel: 'SMS', status: 'ACKNOWLEDGED', sentAt: '12m ago', ackedAt: '8m ago' },
      { id: 'D3', channel: 'IVR', status: 'ACKNOWLEDGED', sentAt: '7m ago', ackedAt: '4m ago' },
      { id: 'D4', channel: 'VOLUNTEER', status: 'SENT', sentAt: '5m ago' },
      { id: 'D5', channel: 'SIREN', status: 'SENT', sentAt: '10m ago' },
    ],
  },
  {
    id: 'ALT_20260928_BHT_02',
    villageId: 'VIL_UTK_07',
    villageName: 'Bhatwari',
    tier: 'WARNING',
    message: 'WARNING: Slope instability increasing. Prepare emergency grab-bags. Move vulnerable elders to Shelter 1 via Route B.',
    created_at: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    leadTimeMinutes: 48,
    targetPopulation: 4218,
    isDrill: false,
    reachPct: 91.0,
    ackPct: 62.4,
    deliveries: [
      { id: 'D6', channel: 'CELL_BROADCAST', status: 'SENT', sentAt: '25m ago' },
      { id: 'D7', channel: 'SMS', status: 'ACKNOWLEDGED', sentAt: '25m ago', ackedAt: '18m ago' },
      { id: 'D8', channel: 'IVR', status: 'SENT', sentAt: '20m ago' },
      { id: 'D9', channel: 'VOLUNTEER', status: 'SENT', sentAt: '15m ago' },
      { id: 'D10', channel: 'SIREN', status: 'PENDING' },
    ],
  },
];

export const INITIAL_TASKS: VolunteerTask[] = [
  {
    id: 'TSK_101',
    volunteerId: 'VOL_01',
    volunteerName: 'Deepak Semwal',
    volunteerPhone: '+919876500101',
    ward: 'Maneri Ward 03 (Lower Basti)',
    targetHouseholds: 3,
    vulnerableCount: 5,
    specialNeeds: '2 elderly bedridden citizens needing stretcher assist',
    destinationShelter: 'Maneri Ridge Shelter',
    recommendedRoute: 'Route B (Old Temple Ridge)',
    priority: 'CRITICAL',
    timeRemainingMin: 22,
    status: 'IN_PROGRESS',
  },
  {
    id: 'TSK_102',
    volunteerId: 'VOL_02',
    volunteerName: 'Pooja Bisht',
    volunteerPhone: '+919876500102',
    ward: 'Bhatwari Ward 01',
    targetHouseholds: 4,
    vulnerableCount: 6,
    specialNeeds: '1 pregnant mother, 3 infants needing safe transport',
    destinationShelter: 'Bhatwari Inter College',
    recommendedRoute: 'Route B (Pine Forest Trail)',
    priority: 'HIGH',
    timeRemainingMin: 38,
    status: 'ACCEPTED',
  },
  {
    id: 'TSK_103',
    volunteerId: 'VOL_03',
    volunteerName: 'Manoj Negi',
    volunteerPhone: '+919876500103',
    ward: 'Joshiyara Ward 04',
    targetHouseholds: 2,
    vulnerableCount: 2,
    specialNeeds: 'Wheelchair assistance required for elderly couple',
    destinationShelter: 'Polytechnic Campus',
    recommendedRoute: 'Main Highway Link',
    priority: 'MODERATE',
    timeRemainingMin: 46,
    status: 'PENDING',
  },
];

export const INITIAL_VULNERABLE: VulnerableHousehold[] = [
  {
    id: 'VUL_HH_01',
    villageId: 'VIL_UTK_08',
    villageName: 'Maneri',
    headOfHousehold: 'Govind Ram (Age 82)',
    contactPhone: '+919411012345',
    membersCount: 3,
    vulnerabilityType: 'Elderly',
    assignedVolunteerName: 'Deepak Semwal',
    evacuationStatus: 'Awaiting Volunteer',
  },
  {
    id: 'VUL_HH_02',
    villageId: 'VIL_UTK_08',
    villageName: 'Maneri',
    headOfHousehold: 'Kamla Devi (Age 76)',
    contactPhone: '+919411012346',
    membersCount: 2,
    vulnerabilityType: 'Mobility Impaired',
    assignedVolunteerName: 'Deepak Semwal',
    evacuationStatus: 'Needs Assistance',
  },
  {
    id: 'VUL_HH_03',
    villageId: 'VIL_UTK_07',
    villageName: 'Bhatwari',
    headOfHousehold: 'Rameshwar Bhatt (Age 79)',
    contactPhone: '+919411012399',
    membersCount: 4,
    vulnerabilityType: 'Infants / Pregnant',
    assignedVolunteerName: 'Pooja Bisht',
    evacuationStatus: 'Evacuating',
  },
];

export const INITIAL_REPORTS: CommunityReport[] = [
  {
    id: 'REP_20260928_01',
    villageId: 'VIL_UTK_07',
    villageName: 'Bhatwari',
    lat: 30.8195,
    lon: 78.6205,
    hazardType: 'Debris Chute',
    text: 'Large boulders rolling across the lower terrace near Bhagirathi bend after cloudburst.',
    photoUrl: 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=600&q=80',
    reporterName: 'Kailash Chand',
    reporterPhone: '+919876543999',
    status: 'VERIFIED',
    isGroundTruthCandidate: true,
    createdAt: '35m ago',
    reviewedBy: 'NDRF Control Officer #02',
    reviewNotes: 'Verified against satellite stream. 40m debris fan confirmed.',
  },
  {
    id: 'REP_20260928_02',
    villageId: 'VIL_UTK_08',
    villageName: 'Maneri',
    lat: 30.7660,
    lon: 78.5350,
    hazardType: 'Road Blocked',
    text: 'Mudflow blocking bypass culvert. NH-108 closed for heavy vehicles.',
    reporterName: 'Suraj Singh',
    reporterPhone: '+919876543888',
    status: 'VERIFIED',
    isGroundTruthCandidate: true,
    createdAt: '18m ago',
    reviewedBy: 'DEOC Officer #01',
    reviewNotes: 'Excavator dispatched. Route marked as Severed in EWS routing.',
  },
];

export function getScenarioData(scenario: ScenarioType): {
  villages: Village[];
  sensors: Sensor[];
  alerts: Alert[];
  routes: Route[];
} {
  const villages = JSON.parse(JSON.stringify(INITIAL_VILLAGES)) as Village[];
  const sensors = JSON.parse(JSON.stringify(INITIAL_SENSORS)) as Sensor[];
  const alerts = JSON.parse(JSON.stringify(INITIAL_ALERTS)) as Alert[];
  const routes = JSON.parse(JSON.stringify(INITIAL_ROUTES)) as Route[];

  switch (scenario) {
    case 'NORMAL':
      villages.forEach((v) => {
        v.risk.tier = 'NONE';
        v.risk.probability = 0.02;
        v.risk.leadTimeMinutes = 480;
        v.risk.explanation.soilSaturationPct = 32.0;
        v.risk.explanation.currentRainfallRateMmH = 1.5;
        v.risk.explanation.factorOfSafety = 1.95;
      });
      routes.forEach((r) => {
        r.isBlocked = false;
        r.cutRisk = 0.02;
      });
      return { villages, sensors, alerts: [], routes };

    case 'HEAVY_RAIN':
      villages.forEach((v) => {
        if (v.id === 'VIL_UTK_01' || v.id === 'VIL_UTK_06' || v.id === 'VIL_UTK_07') {
          v.risk.tier = 'WATCH';
          v.risk.probability = 0.28;
          v.risk.leadTimeMinutes = 140;
          v.risk.explanation.currentRainfallRateMmH = 26.5;
          v.risk.explanation.soilSaturationPct = 72.0;
          v.risk.explanation.factorOfSafety = 1.34;
        } else {
          v.risk.tier = 'NONE';
        }
      });
      return { villages, sensors, alerts: alerts.filter((a) => a.tier === 'WATCH'), routes };

    case 'LANDSLIDE_WARNING':
      villages.forEach((v) => {
        if (v.id === 'VIL_UTK_07') {
          v.risk.tier = 'WARNING';
          v.risk.probability = 0.74;
          v.risk.leadTimeMinutes = 48;
          v.risk.explanation.factorOfSafety = 1.04;
        } else if (v.id === 'VIL_UTK_08') {
          v.risk.tier = 'WARNING';
          v.risk.probability = 0.65;
          v.risk.leadTimeMinutes = 60;
          v.risk.explanation.factorOfSafety = 1.10;
        }
      });
      return { villages, sensors, alerts: alerts.filter((a) => a.tier === 'WARNING'), routes };

    case 'FLASH_FLOOD':
    case 'EVACUATION':
    default:
      return { villages, sensors, alerts, routes };
  }
}
