import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useEmergency } from '../context/EmergencyContext';
import {
  ShieldCheck,
  AlertOctagon,
  AlertTriangle,
  BellRing,
  Volume2,
  Footprints,
  Building2,
  PhoneCall,
  CheckCircle2,
  WifiOff,
  Radio,
  Share2,
  Languages,
  Camera,
  Sun,
  Moon,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';

export const CitizenPWA: React.FC = () => {
  const { villages, isOnline, lastUpdated, submitHazardReport } = useEmergency();
  const { isDark, toggleTheme } = useTheme();
  const { success, error } = useToast();
  const [selectedVillageId, setSelectedVillageId] = useState<string>('VIL_UTK_08'); // Default Maneri
  const [language, setLanguage] = useState<'hi' | 'en'>('en');
  const [isPlayingVoice, setIsPlayingVoice] = useState(false);
  const [hasCheckedInSafe, setHasCheckedInSafe] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportText, setReportText] = useState('');

  React.useEffect(() => {
    document.title = 'Hyper-Local FlashFlood Prediction — Citizen Advisory';
  }, []);

  const currentVillage = villages.find((v) => v.id === selectedVillageId) || villages[0];
  const tier = currentVillage.risk.tier;

  const statusConfig = {
    NONE: {
      bg: 'bg-emerald-950 border-emerald-500/50 text-emerald-300',
      icon: ShieldCheck,
      title: language === 'hi' ? 'स्थिति सामान्य / सुरक्षित' : 'ALL CLEAR / SAFE',
      desc:
        language === 'hi'
          ? 'आपके क्षेत्र में कोई आपदा चेतावनी नहीं है। सामान्य दैनिक कार्य जारी रख सकते हैं।'
          : 'No active flash flood or landslide hazard in your village.',
      actionText: language === 'hi' ? 'सतर्क रहें व जानकारी देखें' : 'Stay Informed',
    },
    WATCH: {
      bg: 'bg-amber-950 border-amber-500/50 text-amber-300',
      icon: BellRing,
      title: language === 'hi' ? 'मौसम सलाह (WATCH)' : 'ADVISORY (WATCH)',
      desc:
        language === 'hi'
          ? 'ऊपरी पहाड़ों में भारी बारिश। नदी-नालों और संवेदनशील ढलानों से दूर रहें।'
          : 'Heavy precipitation upstream. Stay clear of swollen streams and unstable slopes.',
      actionText: language === 'hi' ? 'अपडेट्स देखते रहें' : 'Monitor Updates',
    },
    WARNING: {
      bg: 'bg-orange-950 border-orange-500/60 text-orange-300',
      icon: AlertTriangle,
      title: language === 'hi' ? 'चेतावनी: तैयारी करें (WARNING)' : 'WARNING: PREPARE',
      desc:
        language === 'hi'
          ? 'ढलानों पर पानी का दबाव अधिक है। आपातकालीन बैग, दवाइयां व टॉर्च तैयार रखें।'
          : 'High saturation detected. Prepare emergency grab-bags and assist elders.',
      actionText: language === 'hi' ? 'आपातकालीन तैयारी शुरू करें' : 'Prepare for Evacuation',
    },
    EVACUATE: {
      bg: 'bg-red-950 border-red-500 text-red-200 shadow-2xl shadow-red-950 animate-pulse',
      icon: AlertOctagon,
      title: language === 'hi' ? 'तुरंत सुरक्षित स्थान पर जाएं' : 'EVACUATE IMMEDIATELY',
      desc:
        language === 'hi'
          ? 'खतरे का स्तर गंभीर! तुरंत घर खाली करें। मार्ग B (मंदिर रिज) से आश्रय 2 की ओर जाएं।'
          : 'High imminent life threat! Leave your house now. Follow Route B to Shelter 2.',
      actionText: language === 'hi' ? 'सुरक्षित मार्ग से निकलें' : 'START EVACUATION NOW',
    },
  }[tier];

  const StatusIcon = statusConfig.icon;

  const directiveVoiceText =
    language === 'hi'
      ? `आपातकालीन सूचना: ${currentVillage.name} में स्थिति ${tier} है। ${statusConfig.desc}`
      : `Emergency alert: Status for ${currentVillage.name} is ${tier}. ${statusConfig.desc}`;

  const handlePlayVoice = () => {
    setIsPlayingVoice(true);
    if ('speechSynthesis' in window) {
      const u = new SpeechSynthesisUtterance(directiveVoiceText);
      u.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
      u.rate = 0.95;
      u.onend = () => setIsPlayingVoice(false);
      u.onerror = () => setIsPlayingVoice(false);
      window.speechSynthesis.speak(u);
    } else {
      setTimeout(() => setIsPlayingVoice(false), 3000);
    }
  };

  const handleQuickReport = async () => {
    if (!reportText.trim()) return;
    try {
      await submitHazardReport({
        villageId: currentVillage.id,
        hazardType: 'Flash Flood',
        text: reportText,
        lat: currentVillage.lat,
        lon: currentVillage.lon,
        reporterName: 'Mobile Citizen',
      });
      success(
        language === 'hi'
          ? 'आपकी रिपोर्ट प्राप्त हुई। राहत दल को सतर्क कर दिया गया है।'
          : 'Hazard report transmitted. Emergency teams alerted.',
        'Report Sent'
      );
      setReportText('');
      setShowReportModal(false);
    } catch (e: any) {
      error(e.message || 'Failed to submit report', 'Transmission Error');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans flex flex-col justify-between max-w-md mx-auto border-x border-slate-800 shadow-2xl select-none">
      {/* Top Mobile Bar */}
      <div className="p-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-red-600 flex items-center justify-center font-bold text-white text-xs">
            EWS
          </div>
          <div>
            <h1 className="text-xs font-bold font-mono tracking-wide text-slate-200">
              {language === 'hi' ? 'हाइपर-लोकल फ्लैशबाढ़ पूर्वसूचना' : 'HYPER-LOCAL FLASHFLOOD PREDICTION'}
            </h1>
            <span className="text-[10px] text-slate-400 font-mono">Disaster Early Warning Portal</span>
          </div>
        </div>

        {/* Theme, Language & Officer Dashboard Link */}
        <div className="flex items-center gap-1.5 font-mono text-xs">
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
            title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            aria-label="Toggle Light and Dark Theme"
          >
            {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-indigo-400" />}
          </button>
          <button
            onClick={() => setLanguage(language === 'hi' ? 'en' : 'hi')}
            className="flex items-center gap-1 px-2 py-1 rounded bg-slate-800 text-orange-400 border border-slate-700 font-bold"
          >
            <Languages className="w-3.5 h-3.5" />
            <span>{language === 'hi' ? 'English' : 'हिन्दी'}</span>
          </button>
          <Link
            to="/"
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-[11px] font-bold transition-colors"
            title="Return to Officer Mission Control"
          >
            Officer Login
          </Link>
        </div>
      </div>

      {/* Offline Stale Data Warning Banner */}
      {!isOnline && (
        <div className="bg-amber-950/90 border-b border-amber-500/50 p-2 text-amber-300 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <WifiOff className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{language === 'hi' ? 'ऑफ़लाइन मोड (कैश्ड डेटा)' : 'OFFLINE MODE (Cached)'}</span>
          </div>
          <span className="text-[10px] opacity-80">{lastUpdated}</span>
        </div>
      )}

      {/* Main Citizen Action Body */}
      <div className="p-4 space-y-4 flex-1 overflow-y-auto">
        {/* Village Selector Dropdown */}
        <div className="bg-slate-900/80 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between">
          <span className="text-xs text-slate-400 font-mono">
            {language === 'hi' ? 'स्थान चुनें:' : 'Your Location:'}
          </span>
          <select
            value={selectedVillageId}
            onChange={(e) => {
              setSelectedVillageId(e.target.value);
              setHasCheckedInSafe(false);
            }}
            className="bg-slate-950 text-slate-100 text-xs font-bold font-mono px-2 py-1 rounded border border-slate-700 outline-none"
          >
            {villages.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} ({v.risk.tier})
              </option>
            ))}
          </select>
        </div>

        {/* Large 3-Second Status Box */}
        <div className={`p-5 rounded-2xl border-2 text-center space-y-3 ${statusConfig.bg}`}>
          <div className="w-14 h-14 mx-auto rounded-2xl bg-black/40 flex items-center justify-center ring-2 ring-white/20">
            <StatusIcon className="w-8 h-8" />
          </div>

          <div>
            <span className="text-[11px] uppercase tracking-widest font-mono font-bold opacity-80 block">
              {currentVillage.name}
            </span>
            <h2 className="text-xl sm:text-2xl font-black mt-0.5 tracking-tight font-sans">
              {statusConfig.title}
            </h2>
          </div>

          <p className="text-xs leading-relaxed opacity-90 px-2 font-sans font-medium">
            {statusConfig.desc}
          </p>

          {tier === 'EVACUATE' && (
            <div className="inline-block bg-black/50 px-3 py-1.5 rounded-full font-mono font-bold text-xs border border-white/20">
              ⏱️ {language === 'hi' ? 'बचा हुआ समय:' : 'Time Remaining:'} ~{currentVillage.risk.leadTimeMinutes} {language === 'hi' ? 'मिनट' : 'min'}
            </div>
          )}
        </div>

        {/* Audio Directive Voice Button */}
        <button
          onClick={handlePlayVoice}
          disabled={isPlayingVoice}
          className="w-full py-2.5 px-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-cyan-500/50 text-cyan-300 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-98 shadow-md"
        >
          <Volume2 className={`w-4 h-4 text-cyan-400 ${isPlayingVoice ? 'animate-ping' : ''}`} />
          <span>
            {isPlayingVoice
              ? language === 'hi'
                ? 'आवाज बज रही है...'
                : 'Playing voice alert...'
              : language === 'hi'
              ? 'आवाज में सूचना सुनें (Listen)'
              : 'Listen to Audio Directive'}
          </span>
        </button>

        {/* Primary Evacuation Action Button */}
        {tier === 'EVACUATE' || tier === 'WARNING' ? (
          <div className="space-y-2">
            {!hasCheckedInSafe ? (
              <button
                onClick={() => {
                  setHasCheckedInSafe(true);
                  success(
                    language === 'hi'
                      ? 'आपकी सुरक्षित उपस्थिति दर्ज हो गई है। राहत दल को सूचित कर दिया गया है।'
                      : 'Checked in safe. Incident commander notified.',
                    'Status Updated'
                  );
                }}
                className="w-full py-4 min-h-[48px] px-6 rounded-2xl bg-gradient-to-r from-red-600 via-orange-600 to-red-600 text-white font-black text-sm tracking-wider uppercase shadow-xl shadow-red-950 flex items-center justify-center gap-2 active:scale-95 transition-all border border-red-400/40 focus-visible:ring-2 focus-visible:ring-orange-500"
              >
                <Footprints className="w-5 h-5 animate-pulse" />
                <span>{statusConfig.actionText}</span>
              </button>
            ) : (
              <div className="p-3.5 rounded-xl bg-emerald-950 border border-emerald-500 text-emerald-300 font-mono text-xs text-center flex items-center justify-center gap-2 font-bold shadow-md">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>{language === 'hi' ? 'आपकी सुरक्षित उपस्थिति दर्ज हो गई है' : 'Checked In Safe at Shelter'}</span>
              </div>
            )}
          </div>
        ) : null}

        {/* Evacuation Route & Shelter Guide */}
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2 font-mono text-xs">
          <div className="text-[11px] text-slate-400 font-bold uppercase border-b border-slate-800 pb-1 flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-blue-400" />
            <span>{language === 'hi' ? 'निकटतम सुरक्षित आश्रय' : 'Nearest Refuge Shelter'}</span>
          </div>
          <div className="font-bold text-slate-100 text-sm">
            {language === 'hi' ? 'इंटर कॉलेज हाई ग्राउंड हॉल' : 'Inter College High Ground Hall'}
          </div>
          <div className="text-slate-400 text-[11px]">
            {language === 'hi'
              ? 'दूरी: 1.2 किमी • पैदल समय: ~25 मिनट • भोजन, पानी व प्राथमिक चिकित्सा उपलब्ध'
              : 'Distance: 1.2 km • Walk Time: ~25 min • Food, Water, First Aid Available'}
          </div>

          <div className="pt-2 border-t border-slate-800 text-[11px]">
            <span className="text-emerald-400 font-bold">
              {language === 'hi' ? 'अनुशंसित सुरक्षित मार्ग: ' : 'Recommended Safe Route: '}
            </span>
            <span className="text-slate-300">
              {language === 'hi' ? 'मार्ग B (मंदिर रिज पगडंडी - नदी किनारे से बचें)' : 'Route B (Temple Ridge Trail - Avoid River Road)'}
            </span>
          </div>
        </div>

        {/* SOS Emergency Helpline */}
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between font-mono text-xs">
          <div>
            <span className="text-[10px] text-slate-500 block">EMERGENCY SOS HELPLINE</span>
            <span className="font-bold text-red-400">112 / 1077 (DEOC)</span>
          </div>
          <a
            href="tel:112"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs transition-colors"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>CALL SOS</span>
          </a>
        </div>

        {/* Ground-Truth Photo/Video Report Link */}
        <Link
          to="/report"
          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-orange-950/50 transition-all active:scale-[0.99]"
        >
          <Camera className="w-4 h-4" />
          <span>{language === 'hi' ? '📸 जमीनी स्थिति रिपोर्ट करें (फोटो / वीडियो)' : '📸 Report Ground-Truth (Photo / Video)'}</span>
        </Link>
      </div>

      {/* Quick Hazard Report Modal for Citizen */}
      {showReportModal && (
        <div className="fixed inset-0 bg-black/80 z-50 p-4 flex items-center justify-center font-mono text-xs">
          <div className="bg-slate-900 p-4 rounded-xl border border-slate-700 w-full max-w-sm space-y-3">
            <h3 className="font-bold text-slate-100 text-sm">
              {language === 'hi' ? 'घटना की सूचना दें' : 'Report Hazard'}
            </h3>
            <textarea
              rows={3}
              value={reportText}
              onChange={(e) => setReportText(e.target.value)}
              placeholder={
                language === 'hi'
                  ? 'मलबे, सड़क बंद या पानी के स्तर का विवरण लिखें...'
                  : 'Describe debris, blocked road, or stream water height...'
              }
              className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 outline-none resize-none text-xs"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowReportModal(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-400"
              >
                Cancel
              </button>
              <button
                onClick={handleQuickReport}
                className="px-3 py-1.5 rounded bg-orange-600 font-bold text-white"
              >
                Send Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Citizen Mobile Footer */}
      <footer className="p-3 bg-slate-950 border-t border-slate-800 text-center text-[10px] font-mono text-slate-500">
        Disaster Management Authority • SIH 26192 • PWA Active
      </footer>
    </div>
  );
};
