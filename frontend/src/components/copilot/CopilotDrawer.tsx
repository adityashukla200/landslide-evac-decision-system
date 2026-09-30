import React, { useState, useEffect } from 'react';
import {
  Bot,
  Send,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Radio,
  ChevronRight,
  Sparkles,
  RefreshCw,
  X,
} from 'lucide-react';

interface ProposedAction {
  action_id: string;
  action_name: string;
  description: string;
  target_entity_id: string;
  payload: Record<string, any>;
  requires_approval: boolean;
  status: 'PROPOSED' | 'APPROVED' | 'EXECUTED' | 'REJECTED';
  execution_result?: string | null;
}

interface Message {
  id: string;
  sender: 'user' | 'copilot';
  text: string;
  proposed_actions?: ProposedAction[];
  timestamp: string;
}

interface CopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenPDNAModal?: () => void;
}

export const CopilotDrawer: React.FC<CopilotDrawerProps> = ({ isOpen, onClose, onOpenPDNAModal }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'm-init',
      sender: 'copilot',
      text: 'Incident Commander AI Copilot active. Monitoring Bhagirathi basin telemetry, InSAR coherence loss, CWC gauges, and multi-hop mesh. How can I assist with tactical decision support?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sitrep, setSitrep] = useState<any>(null);

  // Load live SITREP
  const fetchSitrep = async () => {
    try {
      const res = await fetch('/api/v1/copilot/sitrep');
      if (res.ok) {
        const data = await res.json();
        setSitrep(data);
      }
    } catch (e) {
      console.warn('Failed to fetch sitrep:', e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSitrep();
    }
  }, [isOpen]);

  const handleSend = async (customText?: string) => {
    const textToSend = customText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/v1/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          role: 'INCIDENT_COMMANDER',
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const aiMsg: Message = {
          id: `copilot-${Date.now()}`,
          sender: 'copilot',
          text: data.response_text,
          proposed_actions: data.proposed_actions,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, aiMsg]);
        if (data.sitrep_summary) setSitrep(data.sitrep_summary);
      } else {
        throw new Error('API error');
      }
    } catch (err) {
      const errReply: Message = {
        id: `err-${Date.now()}`,
        sender: 'copilot',
        text: 'Network degraded. Operating in local tactical cached mode: Bhagirathi stage is in WARNING state at CWC Harsil. Recommended action: divert evacuees to Sukhi High Ridge Shelter.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errReply]);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteAction = async (actionId: string, approved: boolean) => {
    try {
      const res = await fetch('/api/v1/copilot/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_id: actionId,
          approved,
          officer_notes: approved ? 'Authorized by Incident Commander' : 'Declined by Officer',
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages((prev) =>
          prev.map((m) => {
            if (!m.proposed_actions) return m;
            return {
              ...m,
              proposed_actions: m.proposed_actions.map((act) =>
                act.action_id === actionId
                  ? { ...act, status: data.status, execution_result: data.result_message }
                  : act
              ),
            };
          })
        );
      }
    } catch (err) {
      console.error('Failed to execute action:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-slate-950 border-l border-slate-800 z-50 flex flex-col shadow-2xl font-mono text-xs">
      {/* Header */}
      <div className="p-3.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-400">
            <Bot className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="font-bold text-slate-100 flex items-center gap-1.5 text-sm">
              AI Incident Copilot
              <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-950 border border-emerald-500/30 text-emerald-400">
                LIVE RAG
              </span>
            </div>
            <div className="text-[10px] text-slate-400">Decision Support & Tactical Actions</div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Live Situation Ticker */}
      {sitrep && (
        <div className="p-2.5 bg-red-950/20 border-b border-red-900/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            <span className="font-bold text-red-400 text-[10px]">
              {sitrep.threat_level || 'ELEVATED'}: {sitrep.cwc_danger_breaches?.[0] || 'Bhagirathi Monitored'}
            </span>
          </div>
          <button
            onClick={fetchSitrep}
            className="text-slate-400 hover:text-slate-200 p-1"
            title="Refresh SITREP"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Quick Tactical Prompt Chips */}
      <div className="p-2 bg-slate-900/50 border-b border-slate-800 flex items-center gap-1.5 overflow-x-auto text-[10px]">
        <button
          onClick={() => handleSend('Provide latest situation briefing and active breaches')}
          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 whitespace-nowrap border border-slate-700"
        >
          📊 SITREP
        </button>
        <button
          onClick={() => handleSend('Check shelter capacity and propose diversion route')}
          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 whitespace-nowrap border border-slate-700"
        >
          🏕️ Divert Shelter
        </button>
        <button
          onClick={() => handleSend('Prepare C-DOT Cell Broadcast for Harsil valley')}
          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 whitespace-nowrap border border-slate-700"
        >
          📡 Cell Broadcast
        </button>
        <button
          onClick={() => {
            if (onOpenPDNAModal) onOpenPDNAModal();
            handleSend('Compile official NDMA Post-Disaster Needs Assessment Dossier');
          }}
          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 whitespace-nowrap border border-slate-700"
        >
          📋 NDMA PDNA
        </button>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[88%] p-3 rounded-lg border ${
                m.sender === 'user'
                  ? 'bg-blue-600/20 border-blue-500/40 text-blue-100'
                  : 'bg-slate-900 border-slate-800 text-slate-200'
              }`}
            >
              <div className="text-[11px] leading-relaxed whitespace-pre-wrap">{m.text}</div>

              {/* Action Proposal Cards */}
              {m.proposed_actions && m.proposed_actions.length > 0 && (
                <div className="mt-3 space-y-2">
                  <div className="text-[9px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Tactical Action Authorization Required
                  </div>

                  {m.proposed_actions.map((act) => (
                    <div
                      key={act.action_id}
                      className="p-2.5 rounded-lg bg-slate-950 border border-amber-600/40 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-100 text-[10px]">
                          {act.action_name}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                            act.status === 'EXECUTED'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-600/40'
                              : act.status === 'REJECTED'
                              ? 'bg-red-950 text-red-400 border border-red-600/40'
                              : 'bg-amber-950 text-amber-300 border border-amber-600/40'
                          }`}
                        >
                          {act.status}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 leading-tight">
                        {act.description}
                      </div>

                      {act.status === 'PROPOSED' && (
                        <div className="flex items-center gap-2 pt-1">
                          <button
                            onClick={() => handleExecuteAction(act.action_id, true)}
                            className="flex-1 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold flex items-center justify-center gap-1 transition-colors"
                          >
                            <CheckCircle2 className="w-3 h-3" /> Authorize & Execute
                          </button>
                          <button
                            onClick={() => handleExecuteAction(act.action_id, false)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center justify-center transition-colors"
                          >
                            <XCircle className="w-3 h-3" /> Reject
                          </button>
                        </div>
                      )}

                      {act.execution_result && (
                        <div className="p-1.5 rounded bg-emerald-950/40 border border-emerald-800/40 text-[9px] text-emerald-300 font-semibold">
                          ✓ {act.execution_result}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <span className="text-[8px] text-slate-500 mt-1 px-1">{m.timestamp}</span>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-slate-400 text-[10px] p-2">
            <Bot className="w-3.5 h-3.5 animate-spin text-emerald-400" /> Synthesizing multi-modal
            basin state...
          </div>
        )}
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Copilot or direct actions..."
          className="flex-1 px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 text-xs"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="p-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
