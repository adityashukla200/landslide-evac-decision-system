import React, { useState } from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { Modal } from '../components/common/Modal';
import { reportService } from '../services/reportService';
import { FileSpreadsheet, CheckCircle2, XCircle, Plus, Camera, MapPin, Eye } from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const { reports, submitHazardReport } = useEmergency();
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);

  // Form state
  const [hazardType, setHazardType] = useState('Landslide');
  const [text, setText] = useState('');
  const [reporterName, setReporterName] = useState('');
  const [reporterPhone, setReporterPhone] = useState('');
  const [lat, setLat] = useState('30.7650');
  const [lon, setLon] = useState('78.5320');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    await submitHazardReport({
      hazardType,
      text,
      reporterName: reporterName || 'Citizen Reporter',
      reporterPhone: reporterPhone || '+919876500000',
      lat: parseFloat(lat) || 30.765,
      lon: parseFloat(lon) || 78.532,
    });

    setText('');
    setIsSubmitModalOpen(false);
  };

  const handleReview = async (reportId: string, status: 'VERIFIED' | 'REJECTED') => {
    await reportService.reviewReport(reportId, status, 'DEOC Commander', 'Inspected on field.');
  };

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 font-mono">CROWD-SOURCED COMMUNITY HAZARD REPORTS</h2>
          <p className="text-xs text-slate-400">
            Field observations submitted by citizens and volunteers, vetted by NDRF as ground-truth candidates
          </p>
        </div>

        <button
          onClick={() => setIsSubmitModalOpen(true)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs tracking-wider transition-colors shadow-md shadow-orange-950"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>SUBMIT HAZARD REPORT</span>
        </button>
      </div>

      {/* Reports Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {reports.map((report) => (
          <div
            key={report.id}
            className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-md space-y-3"
          >
            <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-2">
              <div>
                <span className="text-[10px] text-orange-400 font-bold uppercase">{report.hazardType}</span>
                <h3 className="font-bold text-slate-100 text-sm">{report.villageName || 'Field Observation'}</h3>
                <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                  <MapPin className="w-3 h-3" /> {report.lat.toFixed(4)}, {report.lon.toFixed(4)} • {report.createdAt}
                </div>
              </div>

              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  report.status === 'VERIFIED'
                    ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                    : report.status === 'REJECTED'
                    ? 'bg-red-950 text-red-300 border-red-800'
                    : 'bg-amber-950 text-amber-300 border-amber-800'
                }`}
              >
                {report.status}
              </span>
            </div>

            <p className="text-slate-200 text-xs leading-relaxed font-sans bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
              "{report.text}"
            </p>

            {report.photoUrl && (
              <div className="rounded-lg overflow-hidden border border-slate-800 max-h-36">
                <img src={report.photoUrl} alt="Damage evidence" className="w-full h-full object-cover" />
              </div>
            )}

            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-800 text-slate-400">
              <span>Reported by: <strong>{report.reporterName}</strong></span>

              {report.status === 'PENDING_REVIEW' && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleReview(report.id, 'VERIFIED')}
                    className="flex items-center gap-1 px-2 py-1 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 text-[10px] font-bold"
                  >
                    <CheckCircle2 className="w-3 h-3" /> VET GROUND TRUTH
                  </button>
                  <button
                    onClick={() => handleReview(report.id, 'REJECTED')}
                    className="flex items-center gap-1 px-2 py-1 rounded bg-red-950 hover:bg-red-900 text-red-300 border border-red-800 text-[10px]"
                  >
                    <XCircle className="w-3 h-3" /> REJECT
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Submission Modal */}
      <Modal
        isOpen={isSubmitModalOpen}
        onClose={() => setIsSubmitModalOpen(false)}
        title="SUBMIT CITIZEN HAZARD REPORT"
        subtitle="Report live landslides, road blockages, or flash floods"
        maxWidth="md"
      >
        <form onSubmit={handleSubmit} className="space-y-3 font-mono text-xs">
          <div>
            <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
              Hazard Category
            </label>
            <select
              value={hazardType}
              onChange={(e) => setHazardType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 outline-none"
            >
              <option value="Landslide">Landslide / Slope Failure</option>
              <option value="Flash Flood">Flash Flood / Stream Overflow</option>
              <option value="Road Blocked">Road / Trail Severed</option>
              <option value="Debris Chute">Active Debris Chute</option>
              <option value="Rising River">Rising Bhagirathi River</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                Latitude
              </label>
              <input
                type="text"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                Longitude
              </label>
              <input
                type="text"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
              Description / Eye-Witness Details
            </label>
            <textarea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Describe boulders, water height, mudflow, or trail status..."
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 outline-none resize-none"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                Your Name (Optional)
              </label>
              <input
                type="text"
                value={reporterName}
                onChange={(e) => setReporterName(e.target.value)}
                placeholder="Ramesh Rawat"
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1">
                Phone Number
              </label>
              <input
                type="text"
                value={reporterPhone}
                onChange={(e) => setReporterPhone(e.target.value)}
                placeholder="+919876543210"
                className="w-full px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 outline-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsSubmitModalOpen(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              CANCEL
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-bold"
            >
              SUBMIT REPORT
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
