import React from 'react';
import { AlertDelivery } from '../../types';
import { Radio, MessageSquare, PhoneCall, Users, Volume2, CheckCircle2, Clock, XCircle } from 'lucide-react';

interface FallbackLadderProps {
  deliveries: AlertDelivery[];
  reachPct?: number;
  ackPct?: number;
}

export const FallbackLadder: React.FC<FallbackLadderProps> = ({
  deliveries,
  reachPct = 92.5,
  ackPct = 74.0,
}) => {
  const steps: { channel: AlertDelivery['channel']; label: string; icon: any; desc: string }[] = [
    { channel: 'CELL_BROADCAST', label: '1. Cell Broadcast', icon: Radio, desc: 'Geo-fenced BTS tower flood' },
    { channel: 'SMS', label: '2. Telecom SMS', icon: MessageSquare, desc: 'Direct handset SMS directive' },
    { channel: 'IVR', label: '3. IVR Voice Call', icon: PhoneCall, desc: 'Automated voice call + DTMF ack' },
    { channel: 'VOLUNTEER', label: '4. Volunteer Task', icon: Users, desc: 'Last-mile Aapda Mitra visit' },
    { channel: 'SIREN', label: '5. Village Siren', icon: Volume2, desc: '120dB high-decibel acoustic horn' },
  ];

  const getDelivery = (channel: string) => deliveries.find((d) => d.channel === channel);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs select-none">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
        <div>
          <span className="text-[10px] text-orange-400 font-bold uppercase tracking-widest block">
            CASCADING MULTI-CHANNEL DISSEMINATION
          </span>
          <h4 className="text-sm font-bold text-slate-100">Fallback Alert Ladder</h4>
        </div>
        <div className="text-right">
          <div className="text-xs font-bold text-emerald-400">{reachPct}% REACH</div>
          <div className="text-[10px] text-slate-400">{ackPct}% ACKNOWLEDGED</div>
        </div>
      </div>

      {/* Ladder Pipeline Steps */}
      <div className="space-y-2 relative">
        {steps.map((step, idx) => {
          const delivery = getDelivery(step.channel);
          const status = delivery?.status || 'PENDING';
          const Icon = step.icon;

          const statusConfig = {
            ACKNOWLEDGED: {
              badge: 'bg-emerald-950 text-emerald-300 border-emerald-500/50',
              icon: CheckCircle2,
              text: 'ACKNOWLEDGED',
            },
            SENT: {
              badge: 'bg-blue-950 text-blue-300 border-blue-500/50',
              icon: CheckCircle2,
              text: 'DELIVERED',
            },
            PENDING: {
              badge: 'bg-slate-950 text-slate-500 border-slate-800',
              icon: Clock,
              text: 'PENDING LADDER',
            },
            FAILED: {
              badge: 'bg-red-950 text-red-400 border-red-500/50',
              icon: XCircle,
              text: 'FALLBACK TRIGGERED',
            },
          }[status];

          const StatusIcon = statusConfig.icon;

          return (
            <div key={step.channel} className="relative">
              <div
                className={`flex items-center justify-between p-2.5 rounded-lg border transition-all ${
                  status === 'ACKNOWLEDGED' || status === 'SENT'
                    ? 'bg-slate-950/80 border-slate-700'
                    : status === 'FAILED'
                    ? 'bg-red-950/30 border-red-800/40'
                    : 'bg-slate-950/40 border-slate-800/40 opacity-70'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
                      status === 'ACKNOWLEDGED'
                        ? 'bg-emerald-950/80 border-emerald-500 text-emerald-400'
                        : status === 'SENT'
                        ? 'bg-blue-950/80 border-blue-500 text-blue-400'
                        : 'bg-slate-900 border-slate-800 text-slate-400'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="font-bold text-slate-200 text-xs">{step.label}</div>
                    <div className="text-[10px] text-slate-500">{step.desc}</div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded border ${statusConfig.badge}`}
                  >
                    <StatusIcon className="w-3 h-3" />
                    <span>{statusConfig.text}</span>
                  </span>
                </div>
              </div>

              {/* Connecting Down Arrow between steps */}
              {idx < steps.length - 1 && (
                <div className="flex justify-start ml-6 my-0.5">
                  <div className="w-0.5 h-2 bg-slate-800" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
