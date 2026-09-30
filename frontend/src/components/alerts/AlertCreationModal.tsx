import React, { useState } from 'react';
import { useEmergency } from '../../context/EmergencyContext';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { Modal } from '../common/Modal';
import { RiskTier } from '../../types';
import {
  AlertOctagon,
  Smartphone,
  Volume2,
  CheckCircle2,
  ShieldAlert,
  Send,
  Languages,
  Lock,
} from 'lucide-react';

interface AlertCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultVillageId?: string;
  defaultTier?: RiskTier;
}

export const AlertCreationModal: React.FC<AlertCreationModalProps> = ({
  isOpen,
  onClose,
  defaultVillageId,
  defaultTier = 'WARNING',
}) => {
  const { villages, triggerEmergencyAlert } = useEmergency();
  const { isOfficer, openLoginModal } = useAuth();
  const { success, error } = useToast();

  const [selectedVillageId, setSelectedVillageId] = useState<string>(
    defaultVillageId || villages[1]?.id || 'VIL_UTK_07'
  );
  const [tier, setTier] = useState<RiskTier>(defaultTier);
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedVillage = villages.find((v) => v.id === selectedVillageId) || villages[0];

  // Template message generator (Strictly <= 160 chars)
  const getTemplate = (lang: 'en' | 'hi', t: RiskTier, vName: string) => {
    if (lang === 'hi') {
      if (t === 'EVACUATE') {
        return `तुरंत निकलें: ${vName} में भूस्खलन/बाढ़ का गंभीर खतरा। मार्ग B से आश्रय 2 की ओर जाएं। नदी किनारे से बचें।`;
      } else if (t === 'WARNING') {
        return `चेतावनी: ${vName} में भारी वर्षा से ढलान अस्थिर। आपातकालीन बैग तैयार करें और आश्रय जाने को तैयार रहें।`;
      } else {
        return `सलाह: ${vName} के ऊपरी जलग्रहण में वर्षा बढ़ी है। नदी किनारों और नालों से दूर रहें।`;
      }
    } else {
      if (t === 'EVACUATE') {
        return `EVACUATE NOW: High landslide threat at ${vName}. Go via Route B to Shelter 2 immediately. Avoid river banks.`;
      } else if (t === 'WARNING') {
        return `WARNING: Slope instability increasing at ${vName}. Prepare grab-bags and monitor village sirens.`;
      } else {
        return `WATCH: Heavy rain detected upstream of ${vName}. Stay alert and avoid low-lying bridges.`;
      }
    }
  };

  const currentMessage = getTemplate(language, tier, selectedVillage.name).slice(0, 160);

  const handlePlayVoice = () => {
    setIsPlayingAudio(true);
    // Web Speech API fallback or simulated voice synthesis
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(currentMessage);
      utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
      utterance.rate = 0.95;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(utterance);
    } else {
      setTimeout(() => setIsPlayingAudio(false), 3000);
    }
  };

  const handleDispatch = async () => {
    if (!isOfficer) {
      openLoginModal('Officer credentials required to broadcast emergency directives.');
      return;
    }
    setIsSubmitting(true);
    try {
      await triggerEmergencyAlert(selectedVillage.id, tier, currentMessage);
      success(`Emergency ${tier} alert dispatched to ${selectedVillage.name}! Cell Broadcast & Sirens triggered.`, 'Directive Broadcasted');
      setIsSubmitting(false);
      setIsConfirming(false);
      onClose();
    } catch (e) {
      setIsSubmitting(false);
      error('Failed to dispatch alert. Please check your connectivity.', 'Dispatch Error');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="DISPATCH EMERGENCY DIRECTIVE"
      subtitle="Multi-Channel Emergency Dissemination (Cell Broadcast • SMS • IVR • Siren)"
      maxWidth="xl"
    >
      {!isConfirming ? (
        <div className="space-y-4 font-mono text-xs text-slate-800 dark:text-slate-200">
          {/* Target Village & Tier Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-slate-600 dark:text-slate-400 uppercase tracking-wider block mb-1 font-bold">
                Target Village / Ward
              </label>
              <select
                value={selectedVillageId}
                onChange={(e) => setSelectedVillageId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-200 text-xs font-mono outline-none focus:border-orange-500"
              >
                {villages.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} (Pop: {v.population.toLocaleString()})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-600 dark:text-slate-400 uppercase tracking-wider block mb-1 font-bold">
                Directive Severity Tier
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                {(['WATCH', 'WARNING', 'EVACUATE'] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTier(t)}
                    className={`py-2 px-1 rounded-md text-[11px] font-bold border transition-all ${
                      tier === t
                        ? t === 'EVACUATE'
                          ? 'bg-red-600 border-red-500 text-white shadow-md'
                          : t === 'WARNING'
                          ? 'bg-orange-600 border-orange-500 text-white shadow-md'
                          : 'bg-amber-600 border-amber-500 text-white shadow-md'
                        : 'bg-slate-100 dark:bg-slate-950 border-slate-300 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Citizen Screen Preview Box */}
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-1.5">
              <div className="flex items-center gap-1.5 text-orange-600 dark:text-orange-400 font-bold">
                <Smartphone className="w-4 h-4" />
                <span>CITIZEN HANDSET PREVIEW</span>
              </div>

              {/* Language Switcher */}
              <div className="flex items-center gap-1 bg-white dark:bg-slate-900 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-800">
                <Languages className="w-3 h-3 text-slate-500 dark:text-slate-400" />
                <button
                  type="button"
                  onClick={() => setLanguage('hi')}
                  className={`px-1.5 py-0.5 rounded text-[10px] ${
                    language === 'hi' ? 'bg-orange-600 text-white font-bold' : 'text-slate-500 dark:text-slate-400'
                  }`}
                >
                  हिन्दी
                </button>
                <button
                  type="button"
                  onClick={() => setLanguage('en')}
                  className={`px-1.5 py-0.5 rounded text-[10px] ${
                    language === 'en' ? 'bg-orange-600 text-white font-bold' : 'text-slate-500 dark:text-slate-400'
                  }`}
                >
                  EN
                </button>
              </div>
            </div>

            {/* Simulated Mobile SMS bubble */}
            <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 relative">
              <div className="flex items-center gap-1 text-[10px] text-red-600 dark:text-red-400 font-bold uppercase mb-1">
                <AlertOctagon className="w-3.5 h-3.5" />
                <span>GOVT OF INDIA • EMERGENCY CELL BROADCAST</span>
              </div>
              <p className="text-xs leading-relaxed font-sans">{currentMessage}</p>
              <div className="text-[10px] text-right text-slate-500 mt-1 font-mono">
                {currentMessage.length}/160 chars
              </div>
            </div>

            {/* Voice Preview Button */}
            <div className="flex items-center justify-between pt-1 text-[11px]">
              <button
                type="button"
                onClick={handlePlayVoice}
                disabled={isPlayingAudio}
                className="flex items-center gap-1.5 text-cyan-600 dark:text-cyan-400 hover:text-cyan-500 dark:hover:text-cyan-300 font-bold"
              >
                <Volume2 className={`w-3.5 h-3.5 ${isPlayingAudio ? 'animate-ping' : ''}`} />
                <span>{isPlayingAudio ? 'Playing Voice Stream...' : 'Test Audio Broadcast'}</span>
              </button>
              <span className="text-slate-500">Auto-routed via Bhashini TTS</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono transition-colors"
            >
              CANCEL
            </button>
            <button
              type="button"
              onClick={() => setIsConfirming(true)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold font-mono tracking-wider transition-colors shadow-lg shadow-red-950/20 dark:shadow-red-950"
            >
              <Send className="w-3.5 h-3.5" />
              <span>REVIEW & CONFIRM DISPATCH</span>
            </button>
          </div>
        </div>
      ) : (
        /* Error-Prevention Confirmation Dialog */
        <div className="space-y-4 font-mono text-xs text-slate-800 dark:text-slate-200">
          <div className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/60 border border-red-300 dark:border-red-500/50 space-y-2">
            <div className="flex items-center gap-2 text-red-700 dark:text-red-300 font-bold text-sm">
              <ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400 animate-pulse" />
              <span>CRITICAL: CONFIRM EMERGENCY DISPATCH</span>
            </div>
            <p className="text-xs text-slate-700 dark:text-slate-300">
              This action will trigger an immediate emergency broadcast across multiple public channels in{' '}
              <strong className="text-slate-900 dark:text-white">{selectedVillage.name}</strong>.
            </p>

            <div className="grid grid-cols-2 gap-2 text-[11px] pt-2 border-t border-red-200 dark:border-red-800/60">
              <div>
                <span className="text-slate-500 dark:text-slate-400">Target Residents:</span>
                <span className="font-bold text-slate-900 dark:text-white block">{selectedVillage.population.toLocaleString()} citizens</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400">Severity Tier:</span>
                <span className="font-bold text-red-600 dark:text-red-400 block">{tier}</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400">Lead Time Remaining:</span>
                <span className="font-bold text-orange-600 dark:text-orange-400 block">~{selectedVillage.risk.leadTimeMinutes} minutes</span>
              </div>
              <div>
                <span className="text-slate-500 dark:text-slate-400">Primary Refuge:</span>
                <span className="font-bold text-slate-900 dark:text-white block">Inter College Shelter</span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsConfirming(false)}
              className="px-4 py-2 rounded-lg bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs font-mono transition-colors"
            >
              BACK TO EDIT
            </button>
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleDispatch}
              className="flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-black font-mono tracking-wider transition-colors shadow-xl shadow-red-950/20 dark:shadow-red-950"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{isSubmitting ? 'DISPATCHING...' : 'AUTHORIZE & DISPATCH'}</span>
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
};
