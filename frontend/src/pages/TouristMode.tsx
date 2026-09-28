import React, { useState } from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { 
  Compass, AlertTriangle, ShieldCheck, MapPin, PhoneCall, Navigation, 
  ArrowRight, Info, CloudRain, Mountain, CheckCircle2, ChevronRight, Languages
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const TouristMode: React.FC = () => {
  const { scenario, alerts, shelters, villages } = useEmergency();
  const [lang, setLang] = useState<'en' | 'hi'>('en');
  const [selectedLocation, setSelectedLocation] = useState<string>('Harsil (Gangotri Route)');

  const isHazardActive = scenario !== 'NORMAL';

  const t = {
    en: {
      title: 'Char Dham Yatra & Tourist Safety Advisory',
      subtitle: 'Official Real-Time Disaster & Route Guidance for Uttarkashi District',
      switchLang: 'हिंदी में देखें',
      locationPrompt: 'Your Current Tourist Location:',
      safeBadge: 'Route Open & Normal',
      warningBadge: 'Landslide / Flash Flood Watch Active',
      dangerBadge: 'Yatra Caution: Restrict Riverbank Access',
      nearestShelter: 'Nearest Emergency Shelter / High Ground',
      capacity: 'Refuge Capacity',
      status: 'Status',
      open: 'Open & Ready',
      yatraStatusTitle: 'Highway & Sector Operational Status',
      sosTitle: 'Emergency Helplines (Toll-Free 24x7)',
      guidelinesTitle: 'Essential Himalayan Safety Rules',
      switchPwa: 'Switch to Villager PWA',
      switchCommand: 'Command Center',
      sos112: '112 - National Emergency Services',
      sos1077: '1077 - Uttarkashi District Disaster Control Room',
      sos1070: '1070 - Uttarakhand State Emergency Operations',
      rules: [
        'Stay at least 150 meters away from Bhagirathi, Yamuna, and mountain torrents.',
        'Never attempt to drive or walk through overflowing culverts or rockfall zones.',
        'If caught in sudden downpours, move immediately uphill towards reinforced stone shelters.',
        'Obey local police / SDRF checkpoints and route diversions without delay.'
      ],
      routes: [
        { name: 'NH-34 (Uttarkashi - Gangotri Highway)', status: isHazardActive ? 'Caution / Intermittent Falling Stones' : 'Open / Traffic Clear', ok: !isHazardActive },
        { name: 'NH-134 (Dharasu - Yamunotri Highway)', status: 'Open / Caution near Barkot', ok: true },
        { name: 'Harsil - Gangotri Sector', status: isHazardActive ? 'Restricted Movement - High Landslide Hazard' : 'Open', ok: !isHazardActive },
        { name: 'Bhatwari - Maneri Gorge', status: isHazardActive ? 'Watch Active - Monitor Water Level' : 'Open', ok: !isHazardActive }
      ]
    },
    hi: {
      title: 'चार धाम यात्रा एवं पर्यटक सुरक्षा निर्देशिका',
      subtitle: 'उत्तरकाशी जिला आपदा प्रबंधन वास्तविक समय सुरक्षा पोर्टल',
      switchLang: 'View in English',
      locationPrompt: 'आपका वर्तमान स्थान चुनें:',
      safeBadge: 'मार्ग खुला एवं सामान्य',
      warningBadge: 'भूस्खलन / जलभराव चेतावनी सक्रिय',
      dangerBadge: 'यात्रा चेतावनी: नदी तटों से दूर रहें',
      nearestShelter: 'निकटतम सुरक्षित शरणस्थल / ऊँचा स्थान',
      capacity: 'शरण क्षमता',
      status: 'स्थिति',
      open: 'सक्रिय एवं तैयार',
      yatraStatusTitle: 'राजमार्ग एवं यात्रा सेक्टर स्थिति',
      sosTitle: 'आपातकालीन हेल्पलाइन (24x7 निःशुल्क)',
      guidelinesTitle: 'आवश्यक हिमालयी सुरक्षा नियम',
      switchPwa: 'ग्रामीण PWA पर जाएँ',
      switchCommand: 'कमांड सेंटर',
      sos112: '112 - राष्ट्रीय आपातकालीन सेवा',
      sos1077: '1077 - जिला आपदा नियंत्रण कक्ष (उत्तरकाशी)',
      sos1070: '1070 - राज्य आपातकालीन परिचालन केंद्र',
      rules: [
        'भागीरथी, यमुना एवं पहाड़ी बरसाती नालों से कम से कम 150 मीटर दूर रहें।',
        'बहते पानी अथवा संभावित पत्थर गिरने वाले क्षेत्रों को पार करने का प्रयास न करें।',
        'अचानक मूसलाधार बारिश होने पर तुरंत ऊँचे पक्के भवनों/शरणस्थलों की ओर जाएँ।',
        'पुलिस व SDRF के चेकपोस्ट व डायवर्जन निर्देशों का कड़ाई से पालन करें।'
      ],
      routes: [
        { name: 'NH-34 (उत्तरकाशी - गंगोत्री राष्ट्रीय राजमार्ग)', status: isHazardActive ? 'सावधानी / पत्थर गिरने की संभावना' : 'यातायात सुचारु', ok: !isHazardActive },
        { name: 'NH-134 (धरासू - यमुनोत्री राष्ट्रीय राजमार्ग)', status: 'यातायात सुचारु (बड़कोट के पास सतर्क रहें)', ok: true },
        { name: 'हर्षिल - गंगोत्री सेक्टर', status: isHazardActive ? 'नियंत्रित आवागमन - भूस्खलन खतरा' : 'खुला', ok: !isHazardActive },
        { name: 'भटवाड़ी - मनेरी मार्ग', status: isHazardActive ? 'जलस्तर निगरानी जारी' : 'खुला', ok: !isHazardActive }
      ]
    }
  };

  const text = t[lang];
  const primaryShelter = shelters[0] || {
    name: 'GMVN Tourist Complex Harsil (High Ground)',
    capacity: 250,
    current_occupancy: 42,
    has_power: true,
    has_water: true,
    has_medical: true
  };

  return (
    <div className="min-h-screen bg-surface-950 text-surface-100 flex flex-col justify-between">
      {/* Top Header */}
      <header className="bg-surface-900 border-b border-surface-800 sticky top-0 z-30 shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-900/50 border border-primary-500/40 rounded-lg text-primary-400">
              <Compass className="w-6 h-6 animate-spin-slow" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
                {lang === 'en' ? 'Yatra Tourist Safety Guard' : 'चार धाम पर्यटक सुरक्षा'}
                <span className="px-2 py-0.5 text-xs bg-accent-500/20 text-accent-300 rounded border border-accent-500/30">
                  GPS Live
                </span>
              </h1>
              <p className="text-xs text-surface-400">Uttarkashi • Gangotri & Yamunotri Axis</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
              className="flex items-center gap-1 px-3 py-1.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg text-xs font-semibold text-primary-400 transition"
            >
              <Languages className="w-3.5 h-3.5" />
              {text.switchLang}
            </button>
            <Link
              to="/citizen"
              className="hidden sm:inline-block px-3 py-1.5 bg-surface-800 hover:bg-surface-700 border border-surface-700 rounded-lg text-xs text-surface-300 transition"
            >
              {text.switchPwa}
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-4xl mx-auto w-full px-4 py-6 space-y-6 flex-1">
        
        {/* Status Hero Card */}
        <div className={`p-5 rounded-2xl border ${
          isHazardActive 
            ? 'bg-gradient-to-br from-warning-950/60 to-surface-900 border-warning-500/50 shadow-lg shadow-warning-950/40' 
            : 'bg-gradient-to-br from-safe-950/50 to-surface-900 border-safe-500/40 shadow-lg'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`p-3 rounded-xl ${
                isHazardActive ? 'bg-warning-500/20 text-warning-400' : 'bg-safe-500/20 text-safe-400'
              }`}>
                {isHazardActive ? <AlertTriangle className="w-8 h-8 animate-pulse" /> : <ShieldCheck className="w-8 h-8" />}
              </div>
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-surface-400">
                  {lang === 'en' ? 'Current Catchment Advisory' : 'वर्तमान आपदा स्थिति'}
                </span>
                <h2 className="text-xl font-bold text-white mt-0.5">
                  {isHazardActive ? text.warningBadge : text.safeBadge}
                </h2>
                <p className="text-xs text-surface-300 mt-1 max-w-xl">
                  {isHazardActive
                    ? (lang === 'en' 
                        ? 'Heavy rainfall upstream in Bhagirathi basin. River discharge elevating. Pilgrims are advised to halt at designated safe tourist complexes.'
                        : 'भागीरथी बेसिन में भारी वर्षा जारी। नदी का जलस्तर बढ़ रहा है। तीर्थयात्रियों को सुरक्षित पर्यटक आवासों में ठहरने की सलाह दी जाती है।')
                    : (lang === 'en'
                        ? 'Weather conditions favorable. River gauges and slope sensors normal across Gangotri and Yamunotri routes.'
                        : 'मौसम अनुकूल है। गंगोत्री एवं यमुनोत्री मार्ग पर नदी का जलस्तर एवं पहाड़ की स्थिति सामान्य है।')}
                </p>
              </div>
            </div>

            {/* Location selector */}
            <div className="bg-surface-900/90 border border-surface-800 rounded-xl p-3 sm:w-64">
              <label className="text-xs text-surface-400 font-medium block mb-1">
                {text.locationPrompt}
              </label>
              <select
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value)}
                aria-label={text.locationPrompt}
                className="w-full bg-surface-950 border border-surface-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-primary-500"
              >
                <option value="Harsil (Gangotri Route)">Harsil (Gangotri Route)</option>
                <option value="Bhatwari (Central Uttarkashi)">Bhatwari (Central)</option>
                <option value="Gangotri Shrine Area">Gangotri Shrine Area</option>
                <option value="Barkot (Yamunotri Route)">Barkot (Yamunotri)</option>
                <option value="Uttarkashi District Town">Uttarkashi District Town</option>
              </select>
            </div>
          </div>
        </div>

        {/* Nearest Safe Shelter Card */}
        <div className="bg-surface-900 border border-surface-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-accent-400" />
              <h3 className="text-base font-bold text-white">{text.nearestShelter}</h3>
            </div>
            <span className="px-2.5 py-0.5 text-xs rounded-full bg-safe-500/20 text-safe-300 border border-safe-500/30">
              {text.open}
            </span>
          </div>

          <div className="p-4 bg-surface-950 border border-surface-800/80 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-semibold text-white">{primaryShelter.name}</h4>
              <p className="text-xs text-surface-400 mt-1 flex items-center gap-3">
                <span>Elevation: <strong>2,420 m (High Ground)</strong></span>
                <span>•</span>
                <span>Distance: <strong>450 m (6 min walk)</strong></span>
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-safe-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Emergency Power
                </span>
                <span className="text-xs text-safe-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Clean Water
                </span>
                <span className="text-xs text-safe-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> First Aid Post
                </span>
              </div>
            </div>

            <button 
              onClick={() => alert(`Starting turn-by-turn navigation to ${primaryShelter.name}`)}
              className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition shadow-md"
            >
              <Navigation className="w-4 h-4" />
              {lang === 'en' ? 'Start GPS Walk Navigation' : 'रास्ता देखें (GPS)'}
            </button>
          </div>
        </div>

        {/* Highway & Route Sector Status */}
        <div className="bg-surface-900 border border-surface-800 rounded-xl p-5">
          <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
            <Mountain className="w-5 h-5 text-primary-400" />
            {text.yatraStatusTitle}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {text.routes.map((rt, idx) => (
              <div 
                key={idx} 
                className={`p-3.5 rounded-lg border flex items-center justify-between ${
                  rt.ok 
                    ? 'bg-surface-950/80 border-surface-800 text-surface-200' 
                    : 'bg-warning-950/40 border-warning-500/30 text-warning-300'
                }`}
              >
                <div>
                  <div className="text-xs font-semibold text-white">{rt.name}</div>
                  <div className="text-xs mt-0.5 opacity-90">{rt.status}</div>
                </div>
                <div className={`w-3 h-3 rounded-full ${rt.ok ? 'bg-safe-400' : 'bg-warning-400 animate-pulse'}`} />
              </div>
            ))}
          </div>
        </div>

        {/* Himalayan Safety Rules */}
        <div className="bg-surface-900 border border-surface-800 rounded-xl p-5">
          <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
            <Info className="w-5 h-5 text-accent-400" />
            {text.guidelinesTitle}
          </h3>
          <ul className="space-y-2.5">
            {text.rules.map((rule, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs text-surface-300">
                <ChevronRight className="w-4 h-4 text-primary-400 flex-shrink-0 mt-0.5" />
                <span>{rule}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* SOS Emergency Helpline Quick Dials */}
        <div className="bg-critical-950/40 border border-critical-500/40 rounded-xl p-5">
          <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
            <PhoneCall className="w-5 h-5 text-critical-400" />
            {text.sosTitle}
          </h3>
          <p className="text-xs text-surface-300 mb-4">
            {lang === 'en' 
              ? 'Works even in low mobile connectivity. Tap any number to call immediately.'
              : 'कम नेटवर्क में भी काम करेगा। तुरंत संपर्क करने हेतु नीचे दिए गए नंबर पर टैप करें।'}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <a
              href="tel:112"
              className="flex items-center justify-between p-3.5 bg-critical-900/60 hover:bg-critical-800 border border-critical-600 rounded-xl text-white font-bold text-xs transition shadow"
            >
              <div className="flex items-center gap-2.5">
                <PhoneCall className="w-4 h-4 text-critical-300" />
                <span>112 - National Emergency</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5" />
            </a>

            <a
              href="tel:1077"
              className="flex items-center justify-between p-3.5 bg-surface-900 hover:bg-surface-800 border border-surface-700 rounded-xl text-white font-bold text-xs transition shadow"
            >
              <div className="flex items-center gap-2.5">
                <PhoneCall className="w-4 h-4 text-warning-400" />
                <span>1077 - Disaster Control</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5" />
            </a>

            <a
              href="tel:1070"
              className="flex items-center justify-between p-3.5 bg-surface-900 hover:bg-surface-800 border border-surface-700 rounded-xl text-white font-bold text-xs transition shadow"
            >
              <div className="flex items-center gap-2.5">
                <PhoneCall className="w-4 h-4 text-primary-400" />
                <span>1070 - State SEOC</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-surface-900 border-t border-surface-800 py-4 px-4 text-center text-xs text-surface-400">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Uttarakhand State Disaster Management Authority (USDMA) & NDRF</span>
          <div className="flex items-center gap-4">
            <Link to="/citizen" className="text-primary-400 hover:underline">{text.switchPwa}</Link>
            <span>•</span>
            <Link to="/" className="text-primary-400 hover:underline">{text.switchCommand}</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default TouristMode;
