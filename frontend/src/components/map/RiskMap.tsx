import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Village, Route, Shelter, Sensor } from '../../types';
import { LayerControl, ActiveLayers } from './LayerControl';
import { MapLegend } from './MapLegend';
import { Maximize2, Minimize2, ZoomIn, ZoomOut, Navigation } from 'lucide-react';

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
    sensors: true,
    routes: true,
    shelters: true,
    rainHeatmap: true,
    baseLayer: 'dark',
  });

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

      {/* Floating Header Banner */}
      <div className="absolute top-3 left-3 z-20 pointer-events-none flex items-center gap-2">
        <div className="bg-slate-950/90 border border-slate-800 backdrop-blur px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300 shadow-xl pointer-events-auto flex items-center gap-2">
          <Navigation className="w-3.5 h-3.5 text-orange-400" />
          <span>UTTARKASHI CATCHMENT GIS</span>
          <span className="text-slate-600">|</span>
          <span className="text-emerald-400 font-bold">25 WARDS ACTIVE</span>
        </div>
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
