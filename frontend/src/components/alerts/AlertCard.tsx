import React, { useState } from 'react';
import { Alert } from '../../types';
import { RiskBadge } from '../common/RiskBadge';
import { FallbackLadder } from './FallbackLadder';
import { Modal } from '../common/Modal';
import { alertService } from '../../services/alertService';
import {
  Clock,
  Users,
  Code2,
  ChevronDown,
  ChevronUp,
  Radio,
  FileCode,
} from 'lucide-react';

interface AlertCardProps {
  alert: Alert;
}

export const AlertCard: React.FC<AlertCardProps> = ({ alert }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showCapModal, setShowCapModal] = useState(false);
  const [capXmlContent, setCapXmlContent] = useState<string>('');
  const [loadingCap, setLoadingCap] = useState(false);

  const handleOpenCap = async () => {
    setShowCapModal(true);
    setLoadingCap(true);
    const res = await alertService.getCapXml(alert.id);
    setCapXmlContent(res.data);
    setLoadingCap(false);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs shadow-md transition-all hover:border-slate-700 select-none">
      {/* Card Header */}
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center border ${
              alert.tier === 'EVACUATE'
                ? 'bg-red-950/80 border-red-500 text-red-400'
                : 'bg-orange-950/80 border-orange-500 text-orange-400'
            }`}
          >
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-100">{alert.villageName}</h3>
              <RiskBadge tier={alert.tier} size="sm" />
              {alert.isDrill && (
                <span className="px-1.5 py-0.5 text-[10px] rounded bg-amber-950 text-amber-300 border border-amber-800">
                  EXERCISE / DRILL
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
              <span>ID: {alert.id}</span>
              <span>•</span>
              <span>Issued: {alert.created_at}</span>
            </div>
          </div>
        </div>

        {/* Lead time countdown & Population */}
        <div className="flex items-center gap-2 text-right">
          <div className="bg-slate-950 px-2.5 py-1 rounded border border-slate-800 text-[11px]">
            <span className="flex items-center gap-1 text-slate-400">
              <Users className="w-3.5 h-3.5 text-slate-500" /> {alert.targetPopulation.toLocaleString()}
            </span>
          </div>
          <div className="bg-red-950/80 px-2.5 py-1 rounded border border-red-500/40 text-red-300 font-bold flex items-center gap-1 text-[11px]">
            <Clock className="w-3.5 h-3.5 animate-pulse" />
            <span>~{alert.leadTimeMinutes}m IMPACT</span>
          </div>
        </div>
      </div>

      {/* Message Directive Body */}
      <div className="py-3 text-slate-200 text-xs leading-relaxed font-sans bg-slate-950/40 p-3 rounded-lg my-3 border border-slate-800/60">
        "{alert.message}"
      </div>

      {/* Reach & Delivery Breakdown */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-4 text-[11px]">
          <div>
            <span className="text-slate-500">Citizen Reach: </span>
            <strong className="text-emerald-400 font-bold">{alert.reachPct}%</strong>
          </div>
          <div>
            <span className="text-slate-500">Acknowledgement: </span>
            <strong className="text-blue-400 font-bold">{alert.ackPct}%</strong>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* View CAP 1.2 XML Button */}
          <button
            onClick={handleOpenCap}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors border border-slate-700"
            title="View official OASIS CAP 1.2 standard XML payload"
          >
            <Code2 className="w-3.5 h-3.5 text-orange-400" />
            <span>CAP 1.2 XML</span>
          </button>

          {/* Toggle Fallback Ladder View */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors border border-slate-700"
          >
            <span>{isExpanded ? 'Hide Ladder' : 'View Delivery Chain'}</span>
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Expanded Fallback Ladder View */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-slate-800">
          <FallbackLadder
            deliveries={alert.deliveries}
            reachPct={alert.reachPct}
            ackPct={alert.ackPct}
          />
        </div>
      )}

      {/* CAP 1.2 XML Modal */}
      <Modal
        isOpen={showCapModal}
        onClose={() => setShowCapModal(false)}
        title="OASIS CAP 1.2 XML PROTOCOL"
        subtitle={`Standard Common Alerting Protocol payload for ${alert.villageName}`}
        maxWidth="xl"
      >
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-[11px] text-slate-400 border-b border-slate-800 pb-1">
            <span className="flex items-center gap-1 text-emerald-400">
              <FileCode className="w-3.5 h-3.5" /> OASIS CAP v1.2 Compliant
            </span>
            <span>NDMA / SACHET Format</span>
          </div>

          <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-[11px] overflow-x-auto max-h-96 leading-relaxed">
            {loadingCap ? 'Loading CAP XML from backend...' : capXmlContent}
          </pre>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setShowCapModal(false)}
              className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition-colors"
            >
              CLOSE
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
