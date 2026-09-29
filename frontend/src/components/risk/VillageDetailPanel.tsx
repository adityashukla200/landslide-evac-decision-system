import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Village, Route, Shelter } from '../../types';
import { RiskBadge } from '../common/RiskBadge';
import { RiskTimeline } from './RiskTimeline';
import { reportService, CitizenReportItem } from '../../services/reportService';
import {
  X,
  AlertOctagon,
  Clock,
  Shield,
  Footprints,
  Building2,
  HelpCircle,
  TrendingUp,
  Mountain,
  Droplets,
  CloudRain,
  Compass,
  Camera,
  Check,
  Play,
  ExternalLink,
} from 'lucide-react';

interface VillageDetailPanelProps {
  village: Village | null;
  routes: Route[];
  shelters: Shelter[];
  onClose: () => void;
  onTriggerAlert: (villageId: string, tier: any) => void;
}

export const VillageDetailPanel: React.FC<VillageDetailPanelProps> = ({
  village,
  routes,
  shelters,
  onClose,
  onTriggerAlert,
}) => {
  const [citizenReports, setCitizenReports] = useState<CitizenReportItem[]>([]);
  const [loadingReports, setLoadingReports] = useState<boolean>(false);
  const [activeMedia, setActiveMedia] = useState<CitizenReportItem | null>(null);

  useEffect(() => {
    if (!village) return;
    setLoadingReports(true);
    reportService.getCitizenReports(village.id).then((reports) => {
      setCitizenReports(reports);
      setLoadingReports(false);
    });
  }, [village?.id]);

  const handleUpdateStatus = async (reportId: string, newStatus: 'verified' | 'rejected') => {
    await reportService.updateCitizenReportStatus(reportId, newStatus, 'DEOC Officer');
    setCitizenReports((prev) =>
      prev.map((r) => (r.id === reportId ? { ...r, status: newStatus } : r))
    );
  };

  if (!village) return null;

  const { risk, explanation } = { risk: village.risk, explanation: village.risk.explanation };

  const villageRoutes = routes.filter((r) => r.fromVillageId === village.id);
  const recommendedRoute = villageRoutes.find((r) => r.isRecommended) || villageRoutes[0];
  const targetShelter = shelters.find((s) => s.id === recommendedRoute?.toShelterId) || shelters[0];

  // Factor of safety color
  const fosColor =
    explanation.factorOfSafety < 1.0
      ? 'text-red-400 bg-red-950/80 border-red-500/50'
      : explanation.factorOfSafety < 1.2
      ? 'text-orange-400 bg-orange-950/80 border-orange-500/50'
      : 'text-emerald-400 bg-emerald-950/80 border-emerald-500/50';

  return (
    <div className="w-96 md:w-[420px] bg-slate-950 border-l border-slate-800 h-full flex flex-col justify-between shadow-2xl z-30 font-mono text-xs overflow-y-auto select-none">
      {/* Panel Header */}
      <div>
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 sticky top-0 backdrop-blur z-10">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <span className="text-[10px] text-orange-400 uppercase tracking-widest font-bold block">
                VILLAGE / WARD DOSSIER
              </span>
              <h2 className="text-lg font-black text-slate-100">{village.name}</h2>
              <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                <span>{village.district}</span>
                <span>•</span>
                <span>Elev: {village.elevationM}m</span>
                <span>•</span>
                <span>Pop: {village.population.toLocaleString()} ({village.vulnerablePop} vuln)</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded bg-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between gap-2 mt-2">
            <RiskBadge tier={risk.tier} size="md" />
            <div className="flex items-center gap-1.5 text-red-400 font-bold bg-red-950/80 px-2.5 py-1 rounded border border-red-500/40">
              <Clock className="w-3.5 h-3.5 animate-pulse" />
              <span>LEAD TIME: ~{risk.leadTimeMinutes} MIN</span>
            </div>
          </div>
        </div>

        {/* Core Risk Metrics Grid */}
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-2.5">
            {/* Calibrated Probability */}
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
                <span>CALIBRATED RISK</span>
                <TrendingUp className="w-3.5 h-3.5 text-orange-400" />
              </div>
              <div className="text-xl font-black text-slate-100">
                {(risk.probability * 100).toFixed(0)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                Uncertainty: [{(risk.lowerBound * 100).toFixed(0)}% – {(risk.upperBound * 100).toFixed(0)}%]
              </div>
            </div>

            {/* Factor of Safety (FOS) */}
            <div className={`p-2.5 rounded-lg border ${fosColor}`}>
              <div className="flex items-center justify-between text-[10px] mb-1 opacity-80">
                <span>FACTOR OF SAFETY</span>
                <Mountain className="w-3.5 h-3.5" />
              </div>
              <div className="text-xl font-black">
                {explanation.factorOfSafety.toFixed(2)}
              </div>
              <div className="text-[10px] mt-0.5">
                {explanation.factorOfSafety < 1.0 ? 'CRITICAL FAILURE' : 'STABLE SLOPE'}
              </div>
            </div>
          </div>

          {/* "WHY THIS ALERT FIRED" Explainability Section */}
          <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-200 font-bold mb-2 pb-1 border-b border-slate-800">
              <HelpCircle className="w-4 h-4 text-orange-400" />
              <span>WHY THIS RISK INCREASED</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-slate-300 text-[11px]">
              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <CloudRain className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">72h Rainfall</div>
                  <div className="font-bold text-slate-200">{explanation.rainfall72hMm} mm</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <Droplets className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">Soil Saturation</div>
                  <div className="font-bold text-slate-200">{explanation.soilSaturationPct}%</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <Compass className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">Terrain Slope</div>
                  <div className="font-bold text-slate-200">{explanation.slopeDeg}° (Steep)</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <CloudRain className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">Nowcast Rate</div>
                  <div className="font-bold text-slate-200">{explanation.currentRainfallRateMmH} mm/h</div>
                </div>
              </div>
            </div>

            {/* Analog Event Pattern Match */}
            {explanation.analogMatch && (
              <div className="mt-2.5 p-2 rounded bg-orange-950/40 border border-orange-700/40 text-[11px]">
                <div className="flex items-center justify-between font-bold text-orange-300 mb-0.5">
                  <span>HISTORICAL ANALOG MATCH</span>
                  <span>{explanation.analogMatch.similarityPct}% MATCH</span>
                </div>
                <div className="text-slate-300 font-semibold">{explanation.analogMatch.eventName}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">{explanation.analogMatch.description}</div>
              </div>
            )}
          </div>

          {/* Risk Timeline Observed vs Predicted */}
          <RiskTimeline risk={risk} height={150} />

          {/* Evacuation Route & Shelter Summary */}
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-200 font-bold border-b border-slate-800 pb-1">
              <div className="flex items-center gap-1.5">
                <Footprints className="w-4 h-4 text-emerald-400" />
                <span>RECOMMENDED EVACUATION ROUTE</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                CLEAR
              </span>
            </div>

            {recommendedRoute ? (
              <div>
                <div className="font-bold text-slate-200 text-[11px]">{recommendedRoute.name}</div>
                <div className="text-[10px] text-slate-400">
                  Distance: {recommendedRoute.lengthKm} km • Walk Time: ~{recommendedRoute.estWalkMinutes} min • Severance Risk: {(recommendedRoute.cutRisk * 100).toFixed(0)}%
                </div>
                {recommendedRoute.description && (
                  <div className="text-[10px] text-emerald-400/90 mt-1">{recommendedRoute.description}</div>
                )}
              </div>
            ) : (
              <div className="text-slate-400 text-[10px]">No route mapped</div>
            )}

            {targetShelter && (
              <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 text-slate-300">
                  <Building2 className="w-3.5 h-3.5 text-blue-400" />
                  <span className="truncate max-w-[200px]">{targetShelter.name}</span>
                </div>
                <span className="text-slate-400 text-[10px]">
                  Cap: {targetShelter.currentOccupancy}/{targetShelter.capacity}
                </span>
              </div>
            )}
          </div>

          {/* Citizen Ground-Truth Reports Panel */}
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
              <div className="flex items-center gap-1.5 font-bold text-slate-200">
                <Camera className="w-4 h-4 text-orange-400" />
                <span>CITIZEN GROUND-TRUTH REPORTS</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-orange-400 font-mono font-bold">
                {citizenReports.length}
              </span>
            </div>

            {loadingReports ? (
              <div className="text-slate-500 text-[10px] text-center py-3">Loading observations...</div>
            ) : citizenReports.length === 0 ? (
              <div className="text-center py-3 space-y-2">
                <p className="text-slate-500 text-[11px]">No citizen field reports for this village yet.</p>
                <Link
                  to="/report"
                  className="inline-flex items-center gap-1 text-[10px] text-orange-400 hover:text-orange-300 font-bold"
                >
                  <span>Submit Ground-Truth Observation</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            ) : (
              <div className="space-y-2.5">
                {citizenReports.map((report) => (
                  <div
                    key={report.id}
                    className="p-2 rounded-lg bg-slate-950/80 border border-slate-800/80 flex gap-2.5 items-start hover:border-slate-700 transition-colors"
                  >
                    {/* Media Thumbnail */}
                    <div
                      onClick={() => setActiveMedia(report)}
                      className="relative w-16 h-16 rounded-md overflow-hidden bg-black flex-shrink-0 cursor-pointer border border-slate-800 group"
                    >
                      <img
                        src={report.thumbnail_url || report.media_url}
                        alt="Evidence"
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                      {report.media_type === 'video' && (
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                          <Play className="w-4 h-4 text-white fill-white" />
                        </div>
                      )}
                    </div>

                    {/* Metadata & Controls */}
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center justify-between gap-1">
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                            report.reported_flood
                              ? 'bg-red-950 text-red-400 border border-red-800/60'
                              : 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                          }`}
                        >
                          {report.reported_flood ? '🌊 Flood / Slide' : '✅ Safe / No Flood'}
                        </span>

                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-mono ${
                            report.status === 'verified'
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                              : report.status === 'rejected'
                              ? 'bg-red-950/60 text-red-400 border border-red-800'
                              : 'bg-amber-950/60 text-amber-400 border border-amber-800'
                          }`}
                        >
                          {report.status}
                        </span>
                      </div>

                      {report.caption && (
                        <p className="text-[10px] text-slate-300 truncate" title={report.caption}>
                          {report.caption}
                        </p>
                      )}

                      <div className="text-[9px] text-slate-500 flex items-center justify-between">
                        <span>
                          {report.distance_from_village_km !== null
                            ? `${report.distance_from_village_km} km from center`
                            : 'Near village'}
                        </span>
                        <span>
                          {report.created_at
                            ? new Date(report.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                            : ''}
                        </span>
                      </div>

                      {/* Officer Quick Actions: Verify / Reject */}
                      <div className="flex items-center gap-1.5 pt-1">
                        <button
                          type="button"
                          onClick={() => handleUpdateStatus(report.id, 'verified')}
                          disabled={report.status === 'verified'}
                          className={`flex-1 py-1 rounded text-[10px] font-bold flex items-center justify-center gap-1 transition-colors ${
                            report.status === 'verified'
                              ? 'bg-emerald-950/40 text-emerald-600 cursor-not-allowed'
                              : 'bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/60'
                          }`}
                        >
                          <Check className="w-3 h-3" />
                          <span>Verify</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleUpdateStatus(report.id, 'rejected')}
                          disabled={report.status === 'rejected'}
                          className={`flex-1 py-1 rounded text-[10px] font-bold flex items-center justify-center gap-1 transition-colors ${
                            report.status === 'rejected'
                              ? 'bg-red-950/40 text-red-600 cursor-not-allowed'
                              : 'bg-red-950 hover:bg-red-900 text-red-300 border border-red-700/60'
                          }`}
                        >
                          <X className="w-3 h-3" />
                          <span>Reject</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Full Media Lightbox Modal */}
      {activeMedia && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full overflow-hidden shadow-2xl space-y-3 p-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div>
                <h4 className="font-bold text-slate-100 text-xs font-mono">
                  {activeMedia.reported_flood ? '🌊 FLOOD REPORT' : '✅ SAFE REPORT'} — {activeMedia.village_name || 'Observation'}
                </h4>
                <span className="text-[10px] text-slate-400">
                  {activeMedia.latitude.toFixed(4)}°N, {activeMedia.longitude.toFixed(4)}°E •{' '}
                  {activeMedia.distance_from_village_km} km away
                </span>
              </div>
              <button
                onClick={() => setActiveMedia(null)}
                className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-black rounded-xl overflow-hidden aspect-video flex items-center justify-center">
              {activeMedia.media_type === 'video' ? (
                <video src={activeMedia.media_url} controls autoPlay className="max-h-full max-w-full" />
              ) : (
                <img src={activeMedia.media_url} alt="Evidence" className="max-h-full max-w-full object-contain" />
              )}
            </div>

            {activeMedia.caption && (
              <p className="text-xs text-slate-300 italic bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                "{activeMedia.caption}"
              </p>
            )}

            <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
              <span>Status: <strong className="text-slate-200 uppercase">{activeMedia.status}</strong></span>
              <span>Reporter: {activeMedia.reporter_phone || 'Anonymous'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Action Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/90 sticky bottom-0">
        <button
          onClick={() => onTriggerAlert(village.id, 'EVACUATE')}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-black tracking-wider transition-colors shadow-lg shadow-red-950 border border-red-400/40 active:scale-98"
        >
          <AlertOctagon className="w-4 h-4" />
          <span>ISSUE EVACUATION DIRECTIVE</span>
        </button>
      </div>
    </div>
  );
};
