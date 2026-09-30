export type RiskTier = 'NONE' | 'WATCH' | 'WARNING' | 'EVACUATE';

export interface Explanation {
  factorOfSafety: number;
  rainfall72hMm: number;
  currentRainfallRateMmH: number;
  soilSaturationPct: number;
  slopeDeg: number;
  upstreamRainfallIncreasing: boolean;
  analogMatch?: {
    eventName: string;
    similarityPct: number;
    year: number;
    outcomeLandslide: boolean;
    description: string;
  };
}

export interface RiskAssessment {
  villageId: string;
  probability: number;       // [0, 1]
  lowerBound: number;        // Conformal interval lower
  upperBound: number;        // Conformal interval upper
  tier: RiskTier;
  leadTimeMinutes: number;   // Estimated time-to-impact in minutes
  timestamp: string;
  explanation: Explanation;
}

export interface Village {
  id: string;
  name: string;
  district: string;
  lat: number;
  lon: number;
  elevationM: number;
  population: number;
  vulnerablePop: number;
  risk: RiskAssessment;
}

export type SensorType = 'RAIN_GAUGE' | 'SOIL_MOISTURE' | 'RIVER_STAGE' | 'TILT_METER';
export type SensorStatus = 'HEALTHY' | 'WARNING' | 'FAULT' | 'OFFLINE';

export interface Sensor {
  id: string;
  villageId: string;
  villageName: string;
  type: SensorType;
  status: SensorStatus;
  batteryPct: number;
  signalStrengthDbm: number;
  lastUpdated: string;
  currentValue: number;
  unit: string;
  anomalyFlag: boolean;
  anomalyDetails?: string;
  history?: { time: string; value: number }[];
}

export interface Route {
  id: string;
  fromVillageId: string;
  toShelterId: string;
  name: string;
  lengthKm: number;
  estWalkMinutes: number;
  cutRisk: number;            // [0, 1] dynamic severance probability
  isBlocked: boolean;
  isRecommended: boolean;
  description?: string;
  coordinates?: [number, number][]; // LineString [lon, lat] waypoints
  roadType?: 'HIGHWAY' | 'SECONDARY_ROAD' | 'PEDESTRIAN_TRAIL' | '4X4_TRACK';
}

export interface Shelter {
  id: string;
  villageId: string;
  name: string;
  capacity: number;
  currentOccupancy: number;
  lat: number;
  lon: number;
  distanceKm: number;
  amenities: {
    medical: boolean;
    water: boolean;
    food: boolean;
    backupPower: boolean;
  };
  contactPerson: string;
  contactPhone: string;
}

export type AlertChannel = 'CELL_BROADCAST' | 'SMS' | 'IVR' | 'WHATSAPP' | 'VOLUNTEER' | 'SIREN';
export type DeliveryStatus = 'PENDING' | 'SENT' | 'ACKNOWLEDGED' | 'FAILED';

export interface AlertDelivery {
  id: string;
  channel: AlertChannel;
  status: DeliveryStatus;
  sentAt?: string;
  ackedAt?: string;
  error?: string;
}

export interface Alert {
  id: string;
  villageId: string;
  villageName: string;
  tier: RiskTier;
  message: string;
  created_at: string;
  leadTimeMinutes: number;
  targetPopulation: number;
  isDrill?: boolean;
  deliveries: AlertDelivery[];
  reachPct: number;
  ackPct: number;
}

export type TaskStatus = 'PENDING' | 'ACCEPTED' | 'IN_PROGRESS' | 'COMPLETED';

export interface VolunteerTask {
  id: string;
  volunteerId: string;
  volunteerName: string;
  volunteerPhone: string;
  ward: string;
  targetHouseholds: number;
  vulnerableCount: number;
  specialNeeds: string;
  destinationShelter: string;
  recommendedRoute: string;
  priority: 'CRITICAL' | 'HIGH' | 'MODERATE';
  timeRemainingMin: number;
  status: TaskStatus;
}

export interface VulnerableHousehold {
  id: string;
  villageId: string;
  villageName: string;
  headOfHousehold: string;
  contactPhone: string;
  membersCount: number;
  vulnerabilityType: 'Mobility Impaired' | 'Elderly' | 'Bedridden' | 'Infants / Pregnant';
  assignedVolunteerName: string;
  evacuationStatus: 'Safe at Shelter' | 'Evacuating' | 'Needs Assistance' | 'Awaiting Volunteer';
}

export interface CommunityReport {
  id: string;
  villageId?: string;
  villageName?: string;
  lat: number;
  lon: number;
  hazardType: 'Landslide' | 'Flash Flood' | 'Road Blocked' | 'Rising River' | 'Fallen Tree' | 'Debris Chute';
  text: string;
  photoUrl?: string;
  reporterName?: string;
  reporterPhone?: string;
  status: 'PENDING_REVIEW' | 'VERIFIED' | 'REJECTED';
  isGroundTruthCandidate: boolean;
  createdAt: string;
  reviewedBy?: string;
  reviewNotes?: string;
}

export type ScenarioType = 'NORMAL' | 'HEAVY_RAIN' | 'LANDSLIDE_WARNING' | 'FLASH_FLOOD' | 'EVACUATION';

export type UserRole = 'DISTRICT_OFFICER' | 'NDRF_COMMANDER' | 'FIELD_VOLUNTEER' | 'CITIZEN';

export interface OfficerProfile {
  id: string;
  name: string;
  district: string;
  email: string;
  phone?: string;
  role: 'officer' | 'admin';
  designation?: string;
  is_active?: boolean;
  created_at?: string;
  last_login_at?: string;
}

export interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  officer: OfficerProfile;
}
