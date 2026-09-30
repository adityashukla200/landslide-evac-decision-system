export interface HazardZone {
  id: string;
  name: string;
  type: 'LANDSLIDE' | 'FLASH_FLOOD' | 'DEBRIS_FLOW';
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE';
  color: string;
  description: string;
  triggerThreshold: string;
  coordinates: [number, number][];
}

export interface HazardPoint {
  id: string;
  name: string;
  type: 'LANDSLIDE' | 'FLASH_FLOOD' | 'ROCKFALL';
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE';
  lat: number;
  lon: number;
  description: string;
  historicalEvent?: string;
}

export const HAZARD_ZONES: HazardZone[] = [
  // 1. Joshiyara Barrage Flash Flood Inundation Zone
  {
    id: 'HZ_JSH_FLOOD_01',
    name: 'Joshiyara Barrage Flash Flood Inundation Zone',
    type: 'FLASH_FLOOD',
    severity: 'CRITICAL',
    color: '#0284c7', // Sky blue flood fill
    description: 'Low-lying riverbank plain vulnerable to 1.5m - 2.5m flash inundation when Bhagirathi river surges or barrage gates release.',
    triggerThreshold: 'Rainfall > 35 mm/h or River Stage > 3.8m',
    coordinates: [
      [78.4265, 30.7185],
      [78.4285, 30.7202],
      [78.4312, 30.7225],
      [78.4330, 30.7238],
      [78.4315, 30.7250],
      [78.4290, 30.7230],
      [78.4268, 30.7205],
      [78.4265, 30.7185],
    ],
  },

  // 2. Tambakhani Tunnel Active Landslide Scarp
  {
    id: 'HZ_UTK_SLIDE_02',
    name: 'Tambakhani Active Landslide & Scree Zone',
    type: 'LANDSLIDE',
    severity: 'CRITICAL',
    color: '#dc2626', // Crimson red
    description: 'High-slope (48°) fractured metamorphic rock face prone to rotational slope failure and debris avalanche into the valley.',
    triggerThreshold: 'Factor of Safety < 1.05, Saturation > 85%',
    coordinates: [
      [78.4360, 30.7275],
      [78.4395, 30.7295],
      [78.4420, 30.7320],
      [78.4390, 30.7335],
      [78.4355, 30.7305],
      [78.4360, 30.7275],
    ],
  },

  // 3. Gangori Assi Ganga Flash Flood Confluence Fan
  {
    id: 'HZ_GNG_FLOOD_03',
    name: 'Gangori - Assi Ganga Flash Flood Confluence Fan',
    type: 'FLASH_FLOOD',
    severity: 'CRITICAL',
    color: '#0284c7',
    description: 'Catastrophic flash surge channel (historical 2012 cloudburst zone) with violent boulder transport and bank erosion.',
    triggerThreshold: 'Upstream catchment cloudburst > 50 mm/h',
    coordinates: [
      [78.4470, 30.7410],
      [78.4520, 30.7445],
      [78.4560, 30.7490],
      [78.4530, 30.7510],
      [78.4480, 30.7460],
      [78.4470, 30.7410],
    ],
  },

  // 4. Maneri Dam Bypass Rockfall & Mudflow Chute
  {
    id: 'HZ_MNR_SLIDE_04',
    name: 'Maneri Dam Bypass Debris Chute & Rockfall Zone',
    type: 'DEBRIS_FLOW',
    severity: 'HIGH',
    color: '#ea580c', // Orange-red
    description: 'Active debris flow chute cutting Route A (Dam Access Road) during sudden downpours.',
    triggerThreshold: 'Rainfall > 25 mm/h',
    coordinates: [
      [78.5325, 30.7635],
      [78.5355, 30.7655],
      [78.5385, 30.7680],
      [78.5365, 30.7695],
      [78.5330, 30.7665],
      [78.5325, 30.7635],
    ],
  },

  // 5. Bhatwari Active Subsidence & Slide Chute
  {
    id: 'HZ_BHT_SLIDE_05',
    name: 'Bhatwari Sinking Zone & Mudflow Hazard',
    type: 'LANDSLIDE',
    severity: 'CRITICAL',
    color: '#dc2626',
    description: 'Deep-seated slope movement and progressive subsidence cutting lower riverbank paths.',
    triggerThreshold: 'Continuous rainfall > 48h or Infiltration > 60%',
    coordinates: [
      [78.6175, 30.8160],
      [78.6210, 30.8180],
      [78.6240, 30.8205],
      [78.6220, 30.8225],
      [78.6180, 30.8195],
      [78.6175, 30.8160],
    ],
  },
];

export const HAZARD_POINTS: HazardPoint[] = [
  {
    id: 'HP_JSH_01',
    name: 'Joshiyara Low Barrage Causeway (Route A Severed Point)',
    type: 'FLASH_FLOOD',
    severity: 'CRITICAL',
    lat: 30.7215,
    lon: 78.4302,
    description: 'Direct inundation breach point across the river causeway. ROUTE A IS BLOCKED HERE.',
    historicalEvent: '2013 Bhagirathi river crest submerged barrage by 1.8m',
  },
  {
    id: 'HP_UTK_02',
    name: 'Tambakhani Rockfall Chute',
    type: 'ROCKFALL',
    severity: 'HIGH',
    lat: 30.7300,
    lon: 78.4385,
    description: 'Active scree slope with frequent boulder falls onto valley road.',
    historicalEvent: 'Recurring monsoon highway blockage',
  },
  {
    id: 'HP_MNR_03',
    name: 'Maneri Tunnel Inlet Debris Severance (Route A Cut)',
    type: 'LANDSLIDE',
    severity: 'CRITICAL',
    lat: 30.7665,
    lon: 78.5348,
    description: 'Slumping mud and boulders blocking dam access road. ROUTE A IS SEVERED.',
    historicalEvent: '2012 Maneri Dam cloudburst flash flood',
  },
  {
    id: 'HP_BHT_04',
    name: 'Bhatwari Culvert #4 Stream Overflow (Route A Cut)',
    type: 'FLASH_FLOOD',
    severity: 'CRITICAL',
    lat: 30.8188,
    lon: 78.6202,
    description: 'Mountain torrent washing away culvert approach. ROUTE A IS UNPASSABLE.',
    historicalEvent: 'Monsoon debris torrential washout',
  },
  {
    id: 'HP_GNG_05',
    name: 'Gangnani Thermal Footbridge Submergence Point',
    type: 'FLASH_FLOOD',
    severity: 'HIGH',
    lat: 30.9105,
    lon: 78.6828,
    description: 'Lower thermal hot spring crossing swept away by torrent.',
    historicalEvent: 'River flash flood overtopping hot spring banks',
  },
];
