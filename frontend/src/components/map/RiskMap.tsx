import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Village, Route, Shelter, Sensor } from '../../types';
import { LayerControl, ActiveLayers } from './LayerControl';
import { MapLegend } from './MapLegend';
import { Maximize2, Minimize2, ZoomIn, ZoomOut, Navigation } from 'lucide-react';
import { getCitizenReports, CitizenReportItem } from '../../services/reportService';

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
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

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

  // Base map style URLs
  const getStyleUrl = (base: string) => {
    switch (base) {
      case 'terrain':
        return 'https://demotiles.maplibre.org/style.json';
      case 'satellite':
      case 'dark':
      default:
        return {
          version: 8,
          sources: {
            'osm-tiles': {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors | SIH 26192',
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
                'raster-opacity': base === 'dark' ? 0.35 : 0.85,
                'raster-contrast': base === 'dark' ? 0.2 : 0,
              },
            },
          ],
        };
    }
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainer.current) return;

    try {
      const mapInstance = new maplibregl.Map({
        container: mapContainer.current,
        style: getStyleUrl(layers.baseLayer) as any,
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

  // Update Village Markers & GeoJSON layers
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;

    // GeoJSON for Villages
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
        },
      })),
    };

    // Add or update source
    if (m.getSource('villages-source')) {
      (m.getSource('villages-source') as maplibregl.GeoJSONSource).setData(villageGeoJson);
    } else {
      m.addSource('villages-source', {
        type: 'geojson',
        data: villageGeoJson,
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

      // Hover Pointer
      m.on('mouseenter', 'villages-circle', () => {
        m.getCanvas().style.cursor = 'pointer';
      });
      m.on('mouseleave', 'villages-circle', () => {
        m.getCanvas().style.cursor = '';
      });
    }
  }, [villages, mapLoaded]);

  // Update Citizen Reports GeoJSON layer
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

  // Sync Citizen Reports visibility with layer toggle
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const m = map.current;
    const vis = layers.citizenReports ? 'visible' : 'none';
    if (m.getLayer('citizen-reports-circle')) {
      m.setLayoutProperty('citizen-reports-circle', 'visibility', vis);
    }
    if (m.getLayer('citizen-reports-glow')) {
      m.setLayoutProperty('citizen-reports-glow', 'visibility', vis);
    }
  }, [layers.citizenReports, mapLoaded]);

  // Fly to selected village
  useEffect(() => {
    if (!map.current || !selectedVillage) return;
    map.current.flyTo({
      center: [selectedVillage.lon, selectedVillage.lat],
      zoom: 12.5,
      essential: true,
      duration: 1200,
    });
  }, [selectedVillage]);

  return (
    <div
      className={`relative w-full h-full bg-slate-950 overflow-hidden ${
        isFullscreen ? 'fixed inset-0 z-50' : ''
      } ${className}`}
    >
      {/* Map Canvas Container */}
      <div ref={mapContainer} className="w-full h-full" />

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
            map.current?.flyTo({ center: [78.4354, 30.7268], zoom: 10.2 });
          }}
          className="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-orange-400 hover:text-orange-300 border border-slate-700 shadow-lg transition-colors font-mono text-[10px] font-bold"
          title="Recenter District"
        >
          RESET
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
