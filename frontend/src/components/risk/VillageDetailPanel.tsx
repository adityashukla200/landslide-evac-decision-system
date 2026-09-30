import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Village, Route, Shelter } from '../../types';
import { RiskBadge } from '../common/RiskBadge';
import { RiskTimeline } from './RiskTimeline';
import { reportService, CitizenReportItem } from '../../services/reportService';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { CardSkeleton } from '../common/Skeleton';
import { BACKEND_URL } from '../../services/api';
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
  Sliders,
  Lock,
  Save,
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
  const { isOfficer, officer, openLoginModal, getValidAccessToken } = useAuth();
  const { success, error } = useToast();
  const [citizenReports, setCitizenReports] = useState<CitizenReportItem[]>([]);
  const [loadingReports, setLoadingReports] = useState<boolean>(false);
  const [activeMedia, setActiveMedia] = useState<CitizenReportItem | null>(null);

  // Operational Threshold Calibration state
  const [isEditingThresholds, setIsEditingThresholds] = useState(false);
  const [thresholds, setThresholds] = useState({
    watch_threshold: 0.015,
    warning_threshold: 0.025,
    evacuate_threshold: 0.150,
  });
  const [savingThresholds, setSavingThresholds] = useState(false);
  const [thresholdSuccessMsg, setThresholdSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!village) return;
    setLoadingReports(true);
    reportService.getCitizenReports(village.id).then((reports) => {
      setCitizenReports(reports);
      setLoadingReports(false);
    });
  }, [village?.id]);

  const handleUpdateStatus = async (reportId: string, newStatus: 'verified' | 'rejected') => {
    if (!isOfficer) {
      openLoginModal('Officer authentication required to verify or reject citizen reports.');
      return;
    }
    await reportService.updateCitizenReportStatus(reportId, newStatus, officer?.name || 'DEOC Officer');
    setCitizenReports((prev) =>
      prev.map((r) => (r.id === reportId ? { ...r, status: newStatus } : r))
    );
    success(
      newStatus === 'verified'
        ? 'Ground-truth report verified and marked as trustworthy.'
        : 'Report marked as false alarm.',
      'Report Vetted'
    );
  };

  const handleSaveThresholds = async () => {
    if (!isOfficer) {
      openLoginModal('Officer authentication required to calibrate risk thresholds.');
      return;
    }
    if (!village) return;
    setSavingThresholds(true);
    try {
      const token = await getValidAccessToken();
      const res = await fetch(`${BACKEND_URL}/api/v1/thresholds/${village.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({
          watch_threshold: thresholds.watch_threshold,
          warning_threshold: thresholds.warning_threshold,
          evacuate_threshold: thresholds.evacuate_threshold,
          modified_by: officer?.name || 'District Officer',
          change_reason: 'Recalibrated via Command Center',
        }),
      });
      if (res.ok) {
        success(`Operational thresholds updated for ${village.name}.`, 'Thresholds Saved');
        setThresholdSuccessMsg('Thresholds saved successfully.');
        setTimeout(() => setThresholdSuccessMsg(null), 3000);
        setIsEditingThresholds(false);
      } else {
        const err = await res.json().catch(() => ({ detail: 'Failed to update thresholds' }));
        error(err.detail || 'Failed to update thresholds', 'Calibration Error');
      }
    } catch (e: any) {
      error(e.message || 'Network error updating thresholds', 'Connection Error');
    } finally {
      setSavingThresholds(false);
    }
  };

  if (!village) return null;

  const { risk, explanation } = { risk: village.risk, explanation: village.risk.explanation };

  const villageRoutes = routes.filter((r) => r.fromVillageId === village.id);
  const recommendedRoute = villageRoutes.find((r) => r.isRecommended) || villageRoutes[0];
  const targetShelter = shelters.find((s) => s.id === recommendedRoute?.toShelterId) || shelters[0];

  // Factor of safety color (WCAG AA compliant in both themes)
  const fosColor =
    explanation.factorOfSafety < 1.0
      ? 'text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-950/80 border-red-400 dark:border-red-500/50'
      : explanation.factorOfSafety < 1.2
      ? 'text-orange-700 dark:text-orange-400 bg-orange-100 dark:bg-orange-950/80 border-orange-400 dark:border-orange-500/50'
      : 'text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/80 border-emerald-400 dark:border-emerald-500/50';

  return (
    <div className="w-full sm:w-96 md:w-[420px] max-w-full fixed sm:relative right-0 top-0 sm:top-auto bg-white dark:bg-slate-950 border-l border-slate-200 dark:border-slate-800 h-full flex flex-col justify-between shadow-2xl z-30 font-mono text-xs overflow-y-auto select-none transition-all duration-300 animate-slide-in-right">
      {/* Panel Header */}
      <div>
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/60 sticky top-0 backdrop-blur z-10">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <span className="text-[10px] text-orange-600 dark:text-orange-400 uppercase tracking-widest font-bold block">
                VILLAGE / WARD DOSSIER
              </span>
              <h2 className="text-lg font-black text-slate-900 dark:text-slate-100">{village.name}</h2>
              <div className="flex items-center gap-2 text-[11px] text-slate-600 dark:text-slate-400 mt-0.5">
                <span>{village.district}</span>
                <span>•</span>
                <span>Elev: {village.elevationM}m</span>
                <span>•</span>
                <span>Pop: {village.population.toLocaleString()} ({village.vulnerablePop} vuln)</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between gap-2 mt-2">
            <RiskBadge tier={risk.tier} size="md" />
            <div className="flex items-center gap-1.5 text-red-700 dark:text-red-400 font-bold bg-red-100 dark:bg-red-950/80 px-2.5 py-1 rounded border border-red-400 dark:border-red-500/40">
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

          {/* Operational Risk Threshold Calibration (Officer Gated) */}
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-200 font-bold border-b border-slate-800 pb-1">
              <div className="flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-amber-400" />
                <span>OPERATIONAL THRESHOLDS</span>
              </div>
              <button
                onClick={() => {
                  if (!isOfficer) {
                    openLoginModal('Officer authentication required to calibrate risk thresholds.');
                    return;
                  }
                  setIsEditingThresholds(!isEditingThresholds);
                }}
                className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold transition-colors"
                title={isOfficer ? 'Adjust threshold probabilities' : 'Officer login required'}
              >
                {!isOfficer && <Lock className="w-3 h-3 text-orange-400" />}
                <span>{isEditingThresholds ? 'Cancel' : 'Calibrate'}</span>
              </button>
            </div>

            {thresholdSuccessMsg && (
              <div className="p-1.5 rounded bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-[10px] flex items-center gap-1.5">
                <Check className="w-3.5 h-3.5" />
                <span>{thresholdSuccessMsg}</span>
              </div>
            )}

            {!isEditingThresholds ? (
              <div className="grid grid-cols-3 gap-1.5 text-center text-[10px]">
                <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800">
                  <div className="text-slate-400">WATCH</div>
                  <div className="font-bold text-amber-300">{(thresholds.watch_threshold * 100).toFixed(1)}%</div>
                </div>
                <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800">
                  <div className="text-slate-400">WARNING</div>
                  <div className="font-bold text-orange-400">{(thresholds.warning_threshold * 100).toFixed(1)}%</div>
                </div>
                <div className="p-1.5 rounded bg-slate-950/60 border border-slate-800">
                  <div className="text-slate-400">EVACUATE</div>
                  <div className="font-bold text-red-400">{(thresholds.evacuate_threshold * 100).toFixed(1)}%</div>
                </div>
              </div>
            ) : (
              <div className="space-y-2 pt-1">
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[9px] text-slate-400 uppercase">Watch P</label>
                    <input
                      type="number"
                      step="0.005"
                      min="0.001"
                      max="0.99"
                      value={thresholds.watch_threshold}
                      onChange={(e) => setThresholds({ ...thresholds, watch_threshold: parseFloat(e.target.value) || 0.01 })}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-1.5 py-1 text-slate-200 text-[11px]"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] text-slate-400 uppercase">Warning P</label>
                    <input
                      type="number"
                      step="0.005"
                      min="0.001"
                      max="0.99"
                      value={thresholds.warning_threshold}
                      onChange={(e) => setThresholds({ ...thresholds, warning_threshold: parseFloat(e.target.value) || 0.02 })}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-1.5 py-1 text-slate-200 text-[11px]"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] text-slate-400 uppercase">Evacuate P</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      max="0.99"
                      value={thresholds.evacuate_threshold}
                      onChange={(e) => setThresholds({ ...thresholds, evacuate_threshold: parseFloat(e.target.value) || 0.15 })}
                      className="w-full bg-slate-950 border border-slate-700 rounded px-1.5 py-1 text-slate-200 text-[11px]"
                    />
                  </div>
                </div>

                <button
                  onClick={handleSaveThresholds}
                  disabled={savingThresholds}
                  className="w-full py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{savingThresholds ? 'Saving...' : 'Save Decision Thresholds'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Evacuation Route & Shelter Summary */}
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-200 font-bold border-b border-slate-800 pb-1">
              <div className="flex items-center gap-1.5">
                <Footprints className="w-4 h-4 text-emerald-400" />
                <span>EVACUATION ROUTES ({villageRoutes.length})</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                {recommendedRoute ? 'SAFE ALT READY' : 'NO ROUTE'}
              </span>
            </div>

            {villageRoutes.length > 0 ? (
              <div className="space-y-1.5">
                {villageRoutes.map((r) => (
                  <div
                    key={r.id}
                    className={`p-2 rounded border text-[11px] ${
                      r.isBlocked
                        ? 'bg-red-950/40 border-red-900/60 text-red-200'
                        : 'bg-emerald-950/40 border-emerald-900/60 text-emerald-200'
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold">
                      <span>{r.name}</span>
                      <span className={`text-[9px] px-1.5 py-0.2 rounded font-black ${
                        r.isBlocked ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
                      }`}>
                        {r.isBlocked ? 'BLOCKED' : 'SAFE ROUTE'}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {r.lengthKm} km • ~{r.estWalkMinutes} min walk • Severance Risk: {(r.cutRisk * 100).toFixed(0)}%
                    </div>
                    {r.description && (
                      <div className={`text-[9.5px] mt-1 ${r.isBlocked ? 'text-red-300' : 'text-emerald-300'}`}>
                        {r.description}
                      </div>
                    )}
                  </div>
                ))}
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
              <CardSkeleton rows={2} />
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
                          title={isOfficer ? 'Mark report verified' : 'Officer login required to verify'}
                        >
                          {!isOfficer ? <Lock className="w-3 h-3 text-orange-400" /> : <Check className="w-3 h-3" />}
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
                          title={isOfficer ? 'Reject report' : 'Officer login required to reject'}
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
          onClick={() => {
            if (!isOfficer) {
              openLoginModal('Officer authentication required to issue evacuation directives.');
              return;
            }
            onTriggerAlert(village.id, 'EVACUATE');
          }}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-black tracking-wider transition-colors shadow-lg shadow-red-950 border border-red-400/40 active:scale-98"
          title={isOfficer ? 'Issue official evacuation directive' : 'Officer login required to issue evacuation directive'}
        >
          {!isOfficer ? <Lock className="w-4 h-4 text-white/80" /> : <AlertOctagon className="w-4 h-4" />}
          <span>ISSUE EVACUATION DIRECTIVE</span>
        </button>
      </div>
    </div>
  );
};
