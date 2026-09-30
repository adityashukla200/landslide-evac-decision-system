import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Village, Route, Shelter, Sensor } from '../../types';
import { LayerControl, ActiveLayers } from './LayerControl';
import { MapLegend } from './MapLegend';
import {
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  Navigation,
  Footprints,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Shield,
  Tent,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { getCitizenReports, CitizenReportItem } from '../../services/reportService';
import { useTheme } from '../../context/ThemeContext';

interface RiskMapProps {
  villages: Village[];
  routes: Route[];
  shelters: Shelter[];
  sensors: Sensor[];
  selectedVillage: Village | null;
  onSelectVillage: (village: Village) => void;
  className?: string;
}

export const RiskMap: React.FC<RiskMapProps> = ({
  villages,
  routes,
  shelters,
  sensors,
  selectedVillage,
  onSelectVillage,
  className = '',
}) => {
  const { isDark } = useTheme();
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const hoverPopup = useRef<maplibregl.Popup | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [is3DMode, setIs3DMode] = useState(false);
  const [isEvacGuideMinimized, setIsEvacGuideMinimized] = useState(false);

  const [layers, setLayers] = useState<ActiveLayers>({
    villages: true,
    citizenReports: true,
    sensors: true,
    routes: true,
    shelters: true,
    rainHeatmap: true,
    baseLayer: 'dark',
  });

  const [citizenReports, setCitizenReports] = useState<CitizenReportItem[]>([]);

  // Fetch live citizen reports
  useEffect(() => {
    let mounted = true;
    const fetchReports = async () => {
      try {
        const res = await getCitizenReports({ limit: 100 });
        if (mounted && res && res.items) {
          setCitizenReports(res.items);
        }
      } catch (err) {
        console.warn('Failed to load citizen reports for map:', err);
      }
    };
    fetchReports();
    const interval = setInterval(fetchReports, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'EVACUATE':
        return '#ef4444';
      case 'WARNING':
        return '#f97316';
      case 'WATCH':
        return '#f59e0b';
      case 'NONE':
      default:
        return '#10b981';
    }
  };

  // Base map style URLs (Light vs Dark thematic basemaps)
  const getStyleUrl = (base: string, isDarkMode: boolean) => {
    switch (base) {
      case 'terrain':
        return 'https://demotiles.maplibre.org/style.json';
      case 'satellite':
        return {
          version: 8,
          sources: {
            'satellite-tiles': {
              type: 'raster',
              tiles: [
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
              ],
              tileSize: 256,
              attribution: '© Esri, Maxar, Earthstar Geographics',
            },
          },
          layers: [
            {
              id: 'satellite-layer',
              type: 'raster',
              source: 'satellite-tiles',
              minzoom: 0,
              maxzoom: 19,
            },
          ],
        };
      case 'dark':
      default: {
        const tileUrl = isDarkMode
          ? 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
          : 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png';
        return {
          version: 8,
          sources: {
            'osm-tiles': {
              type: 'raster',
              tiles: [tileUrl],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors, © CARTO | SIH 26192',
            },
          },
          layers: [
            {
              id: 'osm-layer',
              type: 'raster',
              source: 'osm-tiles',
              minzoom: 0,
              maxzoom: 19,
              paint: {
                'raster-opacity': isDarkMode ? 0.85 : 0.95,
                'raster-contrast': 0,
              },
            },
          ],
        };
      }
    }
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainer.current) return;

    try {
      const mapInstance = new maplibregl.Map({
        container: mapContainer.current,
        style: getStyleUrl(layers.baseLayer, isDark) as any,
        center: [78.4354, 30.7268], // Uttarkashi Town HQ
        zoom: 10.2,
        maxZoom: 16,
        minZoom: 7,
      });

      mapInstance.on('load', () => {
        map.current = mapInstance;
        setMapLoaded(true);
      });

      return () => {
        mapInstance.remove();
        map.current = null;
      };
    } catch (e) {
      console.warn('MapLibre GL initialized in fallback mode', e);
    }
  }, []);

  // Dynamically update basemap tile source when theme switches (instant, no page reload)
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;
    if (layers.baseLayer === 'terrain' || layers.baseLayer === 'satellite') return;

    const source = m.getSource('osm-tiles') as any;
    const targetTile = isDark
      ? 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
      : 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png';

    if (source && typeof source.setTiles === 'function') {
      source.setTiles([targetTile]);
    }
  }, [isDark, mapLoaded, layers.baseLayer]);

  // 1. Update Evacuation Routes & Road Network GeoJSON Layer
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    const routesGeoJson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: routes
        .map((r) => {
          let coords = r.coordinates;
          if (!coords || coords.length < 2) {
            const v = villages.find((item) => item.id === r.fromVillageId);
            const s = shelters.find((item) => item.id === r.toShelterId);
            if (v && s) {
              const midLon = (v.lon + s.lon) / 2 + (r.isRecommended ? 0.004 : -0.004);
              const midLat = (v.lat + s.lat) / 2 + (r.isRecommended ? 0.003 : -0.003);
              coords = [[v.lon, v.lat], [midLon, midLat], [s.lon, s.lat]];
            }
          }
          if (!coords || coords.length < 2) return null;

          const isSelected = selectedVillage ? r.fromVillageId === selectedVillage.id : false;
          let color = '#10b981'; // Safe evacuation green
          let casingColor = '#064e3b';
          let statusText = 'RECOMMENDED SAFE EVACUATION TRAIL';

          if (r.isBlocked) {
            color = '#ef4444'; // Severed / flooded red
            casingColor = '#7f1d1d';
            statusText = 'BLOCKED / SEVERED BY FLOOD OR MUD';
          } else if (r.roadType === 'HIGHWAY') {
            color = '#38bdf8'; // Arterial highway blue
            casingColor = '#0c4a6e';
            statusText = 'ARTERIAL VALLEY HIGHWAY CORRIDOR';
          } else if (r.cutRisk > 0.4) {
            color = '#f59e0b'; // Caution amber
            casingColor = '#78350f';
            statusText = 'HIGH RISK / ADVISORY CAUTION';
          }

          return {
            type: 'Feature',
            geometry: {
              type: 'LineString',
              coordinates: coords,
            },
            properties: {
              id: r.id,
              name: r.name,
              roadType: r.roadType || 'PEDESTRIAN_TRAIL',
              color,
              casingColor,
              statusText,
              isBlocked: r.isBlocked,
              isRecommended: r.isRecommended,
              cutRisk: Math.round(r.cutRisk * 100),
              lengthKm: r.lengthKm,
              estWalkMinutes: r.estWalkMinutes,
              description: r.description || '',
              isSelected,
            },
          };
        })
        .filter(Boolean) as GeoJSON.Feature[],
    };

    if (m.getSource('routes-source')) {
      (m.getSource('routes-source') as maplibregl.GeoJSONSource).setData(routesGeoJson);
    } else {
      m.addSource('routes-source', {
        type: 'geojson',
        data: routesGeoJson,
      });

      // Casing / Glow outline
      m.addLayer({
        id: 'routes-casing',
        type: 'line',
        source: 'routes-source',
        paint: {
          'line-color': ['get', 'casingColor'],
          'line-width': [
            'case',
            ['get', 'isSelected'],
            10,
            ['interpolate', ['linear'], ['zoom'], 8, 4, 14, 8],
          ],
          'line-opacity': 0.8,
          'line-blur': 1.5,
        },
      });

      // Core Road / Trail Line
      m.addLayer({
        id: 'routes-line',
        type: 'line',
        source: 'routes-source',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': [
            'case',
            ['get', 'isSelected'],
            5,
            ['interpolate', ['linear'], ['zoom'], 8, 2.5, 14, 4.5],
          ],
          'line-dasharray': ['case', ['get', 'isBlocked'], ['literal', [2, 2]], ['literal', [1]]],
        },
      });

      // Line Label
      m.addLayer({
        id: 'routes-label',
        type: 'symbol',
        source: 'routes-source',
        layout: {
          'symbol-placement': 'line',
          'text-field': ['get', 'name'],
          'text-size': 10,
          'text-offset': [0, -1],
          'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
        },
        paint: {
          'text-color': '#f8fafc',
          'text-halo-color': '#020617',
          'text-halo-width': 2,
        },
      });

      // Route Click Popup
      m.on('click', 'routes-line', (e) => {
        if (!e.features || !e.features[0]) return;
        const feat = e.features[0];
        const props = feat.properties as any;
        const coords = (feat.geometry as GeoJSON.LineString).coordinates;
        const midPoint = coords[Math.floor(coords.length / 2)] as [number, number];

        const isBlocked = props.isBlocked === true || props.isBlocked === 'true';
        const badgeColor = isBlocked ? '#dc2626' : '#059669';
        const badgeText = isBlocked ? '🚨 SEVERED / BLOCKED' : '✅ SAFE EVACUATION ROUTE';

        new maplibregl.Popup({ offset: 12, maxWidth: '280px', className: 'route-popup' })
          .setLngLat(midPoint)
          .setHTML(`
            <div style="font-family:ui-sans-serif,system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:12px;border-radius:8px;border:1px solid #334155;box-shadow:0 10px 15px -3px rgba(0,0,0,0.5);">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                <span style="background:${badgeColor};color:#ffffff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;">
                  ${badgeText}
                </span>
                <span style="font-size:10px;font-weight:600;color:#94a3b8;background:#1e293b;padding:2px 5px;border-radius:3px;">
                  ${props.roadType || 'TRAIL'}
                </span>
              </div>
              <h4 style="font-size:13px;font-weight:700;margin:0 0 4px 0;color:#f1f5f9;">${props.name}</h4>
              <div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">
                <b>Distance:</b> ${props.lengthKm} km • <b>Walk Time:</b> ~${props.estWalkMinutes} min
              </div>
              <div style="font-size:10px;color:#94a3b8;background:#1e293b;padding:6px;border-radius:4px;line-height:1.4;">
                ${props.description || 'Designated Himalayan disaster evacuation link.'}
              </div>
              <div style="margin-top:6px;font-size:10px;color:#f59e0b;">
                <b>Cut Risk Probability:</b> ${props.cutRisk}%
              </div>
            </div>
          `)
          .addTo(m);
      });

      // Hover Pointer
      m.on('mouseenter', 'routes-line', () => {
        m.getCanvas().style.cursor = 'pointer';
      });
      m.on('mouseleave', 'routes-line', () => {
        m.getCanvas().style.cursor = '';
      });
    }
  }, [routes, villages, shelters, selectedVillage, mapLoaded]);

  // 2. Update High-Ground Relief Shelters GeoJSON Layer
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    const shelterGeoJson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: shelters.map((s) => {
        const occPct = Math.round((s.currentOccupancy / s.capacity) * 100);
        let color = '#0284c7'; // Normal sky blue
        let statusBadge = 'Available Beds';
        if (occPct >= 90) {
          color = '#ef4444'; // Over 90% -> Diverting
          statusBadge = 'Diverting (Over 90%)';
        } else if (occPct >= 75) {
          color = '#f59e0b';
          statusBadge = 'Near Full';
        }

        return {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [s.lon, s.lat],
          },
          properties: {
            id: s.id,
            name: s.name,
            villageId: s.villageId,
            capacity: s.capacity,
            currentOccupancy: s.currentOccupancy,
            occPct,
            distanceKm: s.distanceKm,
            color,
            statusBadge,
            contactPerson: s.contactPerson,
            contactPhone: s.contactPhone,
            medical: s.amenities?.medical ? '✅ Yes' : '❌ No',
            water: s.amenities?.water ? '✅ Yes' : '❌ No',
            food: s.amenities?.food ? '✅ Yes' : '❌ No',
            power: s.amenities?.backupPower ? '✅ Generator/Solar' : '❌ No',
          },
        };
      }),
    };

    if (m.getSource('shelters-source')) {
      (m.getSource('shelters-source') as maplibregl.GeoJSONSource).setData(shelterGeoJson);
    } else {
      m.addSource('shelters-source', {
        type: 'geojson',
        data: shelterGeoJson,
      });

      // Outer Halo Glow
      m.addLayer({
        id: 'shelters-glow',
        type: 'circle',
        source: 'shelters-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 12, 14, 28],
          'circle-color': ['get', 'color'],
          'circle-opacity': 0.35,
          'circle-blur': 0.6,
        },
      });

      // Shelter Pin Circle
      m.addLayer({
        id: 'shelters-circle',
        type: 'circle',
        source: 'shelters-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 7, 14, 11],
          'circle-color': ['get', 'color'],
          'circle-stroke-width': 2.5,
          'circle-stroke-color': '#ffffff',
        },
      });

      // Shelter Label
      m.addLayer({
        id: 'shelters-label',
        type: 'symbol',
        source: 'shelters-source',
        layout: {
          'text-field': [
            'concat',
            '⛺ ',
            ['get', 'name'],
            ' (',
            ['get', 'currentOccupancy'],
            '/',
            ['get', 'capacity'],
            ')',
          ],
          'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
          'text-size': 10,
          'text-offset': [0, 1.4],
          'text-anchor': 'top',
        },
        paint: {
          'text-color': '#38bdf8',
          'text-halo-color': '#020617',
          'text-halo-width': 2,
        },
      });

      // Shelter Click Popup
      m.on('click', 'shelters-circle', (e) => {
        if (!e.features || !e.features[0]) return;
        const feat = e.features[0];
        const props = feat.properties as any;
        const coords = (feat.geometry as GeoJSON.Point).coordinates.slice() as [number, number];

        new maplibregl.Popup({ offset: 12, maxWidth: '290px', className: 'shelter-popup' })
          .setLngLat(coords)
          .setHTML(`
            <div style="font-family:ui-sans-serif,system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:12px;border-radius:8px;border:1px solid #334155;box-shadow:0 10px 15px -3px rgba(0,0,0,0.5);">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                <span style="background:#0284c7;color:#ffffff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;">
                  ⛺ HIGH-GROUND SHELTER
                </span>
                <span style="font-size:10px;font-weight:600;color:#94a3b8;background:#1e293b;padding:2px 5px;border-radius:3px;">
                  ${props.statusBadge}
                </span>
              </div>
              <h4 style="font-size:13px;font-weight:700;margin:0 0 6px 0;color:#f8fafc;">${props.name}</h4>
              <div style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:10px;color:#94a3b8;margin-bottom:2px;">
                  <span>Occupancy</span>
                  <span><b>${props.currentOccupancy}</b> / ${props.capacity} beds (${props.occPct}%)</span>
                </div>
                <div style="width:100%;height:6px;background:#334155;border-radius:3px;overflow:hidden;">
                  <div style="width:${Math.min(100, props.occPct)}%;height:100%;background:${props.color};"></div>
                </div>
              </div>
              <div style="font-size:10px;color:#cbd5e1;background:#1e293b;padding:6px;border-radius:4px;margin-bottom:6px;line-height:1.5;">
                <div><b>🏥 Medical Aid:</b> ${props.medical}</div>
                <div><b>💧 Potable Water:</b> ${props.water}</div>
                <div><b>🍲 Relief Food:</b> ${props.food}</div>
                <div><b>⚡ Backup Power:</b> ${props.power}</div>
              </div>
              <div style="font-size:10px;color:#94a3b8;">
                <b>In-charge:</b> ${props.contactPerson} (${props.contactPhone})
              </div>
            </div>
          `)
          .addTo(m);
      });

      // Hover Pointer
      m.on('mouseenter', 'shelters-circle', () => {
        m.getCanvas().style.cursor = 'pointer';
      });
      m.on('mouseleave', 'shelters-circle', () => {
        m.getCanvas().style.cursor = '';
      });
    }
  }, [shelters, mapLoaded]);

  // 3. Update Village Markers & GeoJSON layers
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    const villageGeoJson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: villages.map((v) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [v.lon, v.lat],
        },
        properties: {
          id: v.id,
          name: v.name,
          tier: v.risk.tier,
          color: getTierColor(v.risk.tier),
          prob: (v.risk.probability * 100).toFixed(0),
          lead: v.risk.leadTimeMinutes,
          pop: v.population,
          selected: selectedVillage ? v.id === selectedVillage.id : false,
        },
      })),
    };

    if (m.getSource('villages-source')) {
      (m.getSource('villages-source') as maplibregl.GeoJSONSource).setData(villageGeoJson);
    } else {
      m.addSource('villages-source', {
        type: 'geojson',
        data: villageGeoJson,
      });

      // Outer Highlight Glow for Selected Village
      m.addLayer({
        id: 'villages-selected-glow',
        type: 'circle',
        source: 'villages-source',
        filter: ['==', ['get', 'selected'], true],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 22, 14, 44],
          'circle-color': '#f97316',
          'circle-opacity': 0.4,
          'circle-blur': 0.5,
        },
      });

      // Selected Village Prominent Ring
      m.addLayer({
        id: 'villages-selected-ring',
        type: 'circle',
        source: 'villages-source',
        filter: ['==', ['get', 'selected'], true],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 12, 14, 22],
          'circle-color': 'transparent',
          'circle-stroke-width': 3.5,
          'circle-stroke-color': '#ffffff',
        },
      });

      // Outer Pulsing Glow Circle for High Risk
      m.addLayer({
        id: 'villages-glow',
        type: 'circle',
        source: 'villages-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 16, 14, 38],
          'circle-color': ['get', 'color'],
          'circle-opacity': 0.25,
          'circle-blur': 0.6,
        },
      });

      // Core Village Pin
      m.addLayer({
        id: 'villages-circle',
        type: 'circle',
        source: 'villages-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 8, 14, 18],
          'circle-color': ['get', 'color'],
          'circle-stroke-width': 2.5,
          'circle-stroke-color': '#0f172a',
        },
      });

      // Village Label
      m.addLayer({
        id: 'villages-label',
        type: 'symbol',
        source: 'villages-source',
        layout: {
          'text-field': ['concat', ['get', 'name'], ' (', ['get', 'prob'], '%)'],
          'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
          'text-size': 11,
          'text-offset': [0, 1.4],
          'text-anchor': 'top',
        },
        paint: {
          'text-color': '#f8fafc',
          'text-halo-color': '#090d16',
          'text-halo-width': 2,
        },
      });

      // Click Interaction
      m.on('click', 'villages-circle', (e) => {
        if (e.features && e.features[0]) {
          const id = e.features[0].properties?.id;
          const match = villages.find((v) => v.id === id);
          if (match) onSelectVillage(match);
        }
      });

      // Hover Tooltip & Pointer
      m.on('mouseenter', 'villages-circle', (e) => {
        m.getCanvas().style.cursor = 'pointer';
        if (!e.features || !e.features[0]) return;
        const feat = e.features[0];
        const props = feat.properties as any;
        const coords = (feat.geometry as GeoJSON.Point).coordinates.slice() as [number, number];

        if (!hoverPopup.current) {
          hoverPopup.current = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
            offset: 14,
            className: 'village-hover-popup',
          });
        }

        const tierColors: Record<string, { bg: string; text: string; border: string }> = {
          EVACUATE: { bg: '#fee2e2', text: '#991b1b', border: '#f87171' },
          WARNING: { bg: '#ffedd5', text: '#9a3412', border: '#fb923c' },
          WATCH: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
          NONE: { bg: '#dcfce7', text: '#166534', border: '#86efac' },
        };
        const tc = tierColors[props.tier] || tierColors.NONE;

        hoverPopup.current
          .setLngLat(coords)
          .setHTML(`
            <div style="font-family:ui-sans-serif,system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:8px 10px;border-radius:8px;border:1px solid #334155;box-shadow:0 10px 15px -3px rgba(0,0,0,0.5);min-width:145px;">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px;">
                <strong style="font-size:12px;color:#f8fafc;">${props.name}</strong>
                <span style="font-size:9px;font-weight:700;padding:1px 5px;border-radius:4px;background:${tc.bg};color:${tc.text};border:1px solid ${tc.border};">
                  ${props.tier}
                </span>
              </div>
              <div style="font-size:10px;color:#94a3b8;display:flex;justify-content:space-between;">
                <span>Population:</span>
                <b style="color:#cbd5e1;">${Number(props.pop).toLocaleString()}</b>
              </div>
              <div style="font-size:10px;color:#94a3b8;display:flex;justify-content:space-between;margin-top:2px;">
                <span>Risk Probability:</span>
                <b style="color:${props.color};">${props.prob}%</b>
              </div>
            </div>
          `)
          .addTo(m);
      });

      m.on('mouseleave', 'villages-circle', () => {
        m.getCanvas().style.cursor = '';
        if (hoverPopup.current) {
          hoverPopup.current.remove();
        }
      });
    }
  }, [villages, selectedVillage, mapLoaded]);

  // 4. Update Citizen Reports GeoJSON layer
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    const citizenGeoJson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: citizenReports.map((r) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [r.longitude, r.latitude],
        },
        properties: {
          id: r.id,
          reported_flood: r.reported_flood,
          color: r.reported_flood ? '#ef4444' : '#10b981',
          status: r.status,
          village_name: r.village_name || 'Ground Report',
          distance: r.distance_from_village_km != null ? `${r.distance_from_village_km} km` : '',
          media_type: r.media_type,
          caption: r.caption || '',
          created_at: r.created_at || '',
          accuracy: r.accuracy_meters ? `${Math.round(r.accuracy_meters)}m` : 'N/A',
          thumbnail_url: r.thumbnail_url || '',
        },
      })),
    };

    if (m.getSource('citizen-reports-source')) {
      (m.getSource('citizen-reports-source') as maplibregl.GeoJSONSource).setData(citizenGeoJson);
    } else {
      m.addSource('citizen-reports-source', {
        type: 'geojson',
        data: citizenGeoJson,
      });

      // Glow layer
      m.addLayer({
        id: 'citizen-reports-glow',
        type: 'circle',
        source: 'citizen-reports-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 10, 14, 20],
          'circle-color': ['get', 'color'],
          'circle-opacity': 0.45,
          'circle-blur': 0.5,
        },
      });

      // Dot pin
      m.addLayer({
        id: 'citizen-reports-circle',
        type: 'circle',
        source: 'citizen-reports-source',
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 6, 14, 9],
          'circle-color': ['get', 'color'],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        },
      });

      // Popup on Click
      m.on('click', 'citizen-reports-circle', (e) => {
        if (!e.features || !e.features[0]) return;
        const feat = e.features[0];
        const props = feat.properties as any;
        const coords = (feat.geometry as GeoJSON.Point).coordinates.slice() as [number, number];

        const isFlood = props.reported_flood === true || props.reported_flood === 'true';
        const badgeColor = isFlood ? '#dc2626' : '#059669';
        const badgeText = isFlood ? '🚨 FLOOD ACTIVE' : '✅ NO FLOOD / SAFE';
        const thumbHtml = props.thumbnail_url
          ? `<div style="overflow:hidden;border-radius:4px;border:1px solid #334155;margin-bottom:6px;"><img src="${props.thumbnail_url}" style="width:100%;height:110px;object-fit:cover;display:block;" /></div>`
          : '';

        new maplibregl.Popup({ offset: 12, maxWidth: '240px', className: 'citizen-popup' })
          .setLngLat(coords)
          .setHTML(`
            <div style="font-family:ui-sans-serif,system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:10px;border-radius:8px;border:1px solid #334155;box-shadow:0 10px 15px -3px rgba(0,0,0,0.5);">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;gap:6px;">
                <span style="background:${badgeColor};color:#ffffff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;">
                  ${badgeText}
                </span>
                <span style="font-size:10px;font-weight:600;color:#94a3b8;text-transform:uppercase;background:#1e293b;padding:2px 5px;border-radius:3px;">
                  ${props.status}
                </span>
              </div>
              ${thumbHtml}
              ${props.caption ? `<p style="font-size:11px;color:#cbd5e1;margin:0 0 6px 0;line-height:1.4;font-style:italic;">"${props.caption}"</p>` : ''}
              <div style="font-size:10px;color:#94a3b8;border-top:1px solid #1e293b;padding-top:4px;line-height:1.4;">
                <div><b>Area:</b> ${props.village_name} ${props.distance ? `(${props.distance})` : ''}</div>
                <div><b>GPS Accuracy:</b> ${props.accuracy}</div>
                <div><b>Time:</b> ${props.created_at ? new Date(props.created_at).toLocaleTimeString() : 'Recent'}</div>
              </div>
            </div>
          `)
          .addTo(m);
      });

      // Hover Pointer
      m.on('mouseenter', 'citizen-reports-circle', () => {
        m.getCanvas().style.cursor = 'pointer';
      });
      m.on('mouseleave', 'citizen-reports-circle', () => {
        m.getCanvas().style.cursor = '';
      });
    }
  }, [citizenReports, mapLoaded]);

  // Sync Layer Visibility with toggles
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    // Routes
    const routeVis = layers.routes ? 'visible' : 'none';
    ['routes-casing', 'routes-line', 'routes-label'].forEach((layerId) => {
      if (m.getLayer(layerId)) m.setLayoutProperty(layerId, 'visibility', routeVis);
    });

    // Shelters
    const shelterVis = layers.shelters ? 'visible' : 'none';
    ['shelters-glow', 'shelters-circle', 'shelters-label'].forEach((layerId) => {
      if (m.getLayer(layerId)) m.setLayoutProperty(layerId, 'visibility', shelterVis);
    });

    // Villages
    const villageVis = layers.villages ? 'visible' : 'none';
    ['villages-glow', 'villages-circle', 'villages-label'].forEach((layerId) => {
      if (m.getLayer(layerId)) m.setLayoutProperty(layerId, 'visibility', villageVis);
    });

    // Citizen Reports
    const citizenVis = layers.citizenReports ? 'visible' : 'none';
    ['citizen-reports-circle', 'citizen-reports-glow'].forEach((layerId) => {
      if (m.getLayer(layerId)) m.setLayoutProperty(layerId, 'visibility', citizenVis);
    });
  }, [layers, mapLoaded]);

  // Fly to selected village
  useEffect(() => {
    if (!map.current || !selectedVillage) return;
    map.current.flyTo({
      center: [selectedVillage.lon, selectedVillage.lat],
      zoom: 12.2,
      essential: true,
      duration: 1200,
    });
  }, [selectedVillage]);

  // Selected village routes & shelter calculation
  const villageRoutes = selectedVillage
    ? routes.filter((r) => r.fromVillageId === selectedVillage.id)
    : [];
  const recommendedRoute = villageRoutes.find((r) => r.isRecommended) || villageRoutes[0];
  const blockedRoute = villageRoutes.find((r) => r.isBlocked);
  const assignedShelter = shelters.find(
    (s) => s.id === recommendedRoute?.toShelterId || s.villageId === selectedVillage?.id
  ) || shelters[0];

  // Action: Focus evacuation path on map
  const handleFocusEvacuationPath = () => {
    if (!map.current || !selectedVillage) return;
    if (assignedShelter) {
      const bounds = new maplibregl.LngLatBounds();
      bounds.extend([selectedVillage.lon, selectedVillage.lat]);
      bounds.extend([assignedShelter.lon, assignedShelter.lat]);
      if (recommendedRoute?.coordinates) {
        recommendedRoute.coordinates.forEach((pt) => bounds.extend(pt));
      }
      map.current.fitBounds(bounds, {
        padding: { top: 80, bottom: 80, left: 100, right: 380 },
        maxZoom: 14.5,
        duration: 1500,
      });
    }
  };

  return (
    <div
      className={`relative w-full h-full bg-slate-950 overflow-hidden ${
        isFullscreen ? 'fixed inset-0 z-50' : ''
      } ${className}`}
    >
      {/* Map Canvas Container */}
      <div ref={mapContainer} className="w-full h-full" />

      {/* Floating Citizen Evacuation Guidance Card (Top Left) */}
      <div className="absolute top-3 left-3 z-20 max-w-xs sm:max-w-sm bg-slate-950/95 backdrop-blur-md border border-slate-800 rounded-xl p-3 shadow-2xl font-mono text-xs select-none">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
          <div className="flex items-center gap-1.5 text-slate-200 font-bold">
            <Footprints className="w-4 h-4 text-emerald-400" />
            <span className="text-[11px] tracking-wider uppercase">Citizen Evacuation Route</span>
          </div>
          <button
            onClick={() => setIsEvacGuideMinimized(!isEvacGuideMinimized)}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={isEvacGuideMinimized ? 'Expand Guide' : 'Collapse Guide'}
          >
            {isEvacGuideMinimized ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronUp className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {!isEvacGuideMinimized && (
          <>
            {selectedVillage ? (
              <div>
                {/* Origin -> Shelter banner */}
                <div className="flex items-center justify-between bg-slate-900/90 p-2 rounded-lg border border-slate-800 mb-2">
                  <div className="truncate pr-1">
                    <div className="text-[8px] text-slate-500 uppercase font-bold">FROM VILLAGE</div>
                    <div className="text-slate-100 font-bold text-xs truncate">{selectedVillage.name}</div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  <div className="text-right truncate pl-1">
                    <div className="text-[8px] text-slate-500 uppercase font-bold">TO HIGH GROUND</div>
                    <div className="text-emerald-400 font-bold text-xs truncate">
                      {assignedShelter ? assignedShelter.name : 'High-Ridge Shelter'}
                    </div>
                  </div>
                </div>

                {/* Recommended Path Details */}
                {recommendedRoute && (
                  <div className="bg-emerald-950/40 border border-emerald-800/50 rounded-lg p-2 mb-2">
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="text-emerald-300 font-bold flex items-center gap-1 truncate">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                        {recommendedRoute.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-emerald-400 font-semibold mb-1">
                      <span>📏 {recommendedRoute.lengthKm} km</span>
                      <span>⏱️ ~{recommendedRoute.estWalkMinutes} min walk</span>
                      <span>🛡️ Safe Ridge Path</span>
                    </div>
                    <p className="text-[9px] text-slate-400 leading-tight">
                      {recommendedRoute.description ||
                        'Elevated hillside trail safely outside active flood inundation contours.'}
                    </p>
                  </div>
                )}

                {/* Severed / Blocked Route Warning */}
                {blockedRoute && (
                  <div className="p-2 rounded-lg bg-red-950/60 border border-red-800/60 mb-2 flex items-start gap-1.5 text-[10px] text-red-300">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-red-200">
                        VALLEY ROUTE BLOCKED: {blockedRoute.name}
                      </span>
                      <div className="text-[9px] text-red-400 leading-tight mt-0.5">
                        {blockedRoute.description || 'Submerged under flood backwaters. Take high ridge trail!'}
                      </div>
                    </div>
                  </div>
                )}

                {/* Focus Button */}
                <button
                  onClick={handleFocusEvacuationPath}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-all text-[11px] shadow-lg active:scale-98"
                >
                  <Navigation className="w-3.5 h-3.5" />
                  <span>Focus Evacuation Path</span>
                </button>
              </div>
            ) : (
              <div className="text-[10px] text-slate-400 leading-relaxed py-1">
                <p className="mb-2">
                  Select any village on the map to inspect its designated citizen evacuation corridor,
                  active road blockages, and high-ground relief shelters.
                </p>
                <div className="text-[9px] text-slate-500 flex items-center gap-2">
                  <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Safe Trail
                  <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500"></span> Severed Cut
                  <span className="inline-block w-2.5 h-2.5 rounded-full bg-sky-400"></span> NH-34 Highway
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Floating Map Navigation Controls (Top Right) */}
      <div className="absolute top-3 right-3 z-20 flex flex-col gap-1.5">
        <button
          onClick={() => map.current?.zoomIn()}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 shadow-lg transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => map.current?.zoomOut()}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 shadow-lg transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            map.current?.flyTo({ center: [78.4354, 30.7268], zoom: 10.2, pitch: 0, bearing: 0 });
            setIs3DMode(false);
          }}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-orange-400 hover:text-orange-300 border border-slate-700 shadow-lg transition-colors font-mono text-[10px] font-bold"
          title="Recenter District"
        >
          RESET
        </button>
        <button
          onClick={() => {
            if (!map.current) return;
            const next3D = !is3DMode;
            setIs3DMode(next3D);
            if (next3D) {
              map.current.easeTo({ pitch: 58, bearing: -22, duration: 1200 });
            } else {
              map.current.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
            }
          }}
          className={`p-2 rounded-lg border shadow-lg transition-colors font-mono text-[10px] font-bold ${
            is3DMode
              ? 'bg-emerald-950/90 text-emerald-400 border-emerald-500/50'
              : 'bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white border-slate-700'
          }`}
          title="Toggle 3D Mountain Perspective"
        >
          3D
        </button>
        <button
          onClick={() => setIsFullscreen(!isFullscreen)}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 shadow-lg transition-colors"
          title="Toggle Fullscreen Map"
        >
          {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>
      </div>

      {/* Layer Control Panel (Bottom Left) */}
      <div className="absolute bottom-4 left-4 z-20">
        <LayerControl
          layers={layers}
          onToggleLayer={(k) => setLayers((prev) => ({ ...prev, [k]: !prev[k] }))}
          onSetBaseLayer={(base) => setLayers((prev) => ({ ...prev, baseLayer: base }))}
        />
      </div>

      {/* Map Legend (Bottom Right) */}
      <div className="absolute bottom-4 right-4 z-20 hidden md:block">
        <MapLegend />
      </div>
    </div>
  );
};
