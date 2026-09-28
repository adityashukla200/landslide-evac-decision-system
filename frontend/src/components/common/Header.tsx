import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useEmergency } from '../../context/EmergencyContext';
import { useAuth } from '../../context/AuthContext';
import { StatusIndicator } from './StatusIndicator';
import {
  ShieldAlert,
  Smartphone,
  MapPin,
  Clock,
  User,
  Radio,
  Compass,
} from 'lucide-react';
import { UserRole } from '../../types';

interface HeaderProps {
  onOpenAlertModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenAlertModal }) => {
  const { isOnline, alerts, lastUpdated } = useEmergency();
  const { role, setRole, userName, badgeNumber } = useAuth();
  const [currentTime, setCurrentTime] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleDateString('en-IN', {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        }) +
          ' ' +
          now.toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
          }) +
          ' IST'
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const activeIncidents = alerts.filter(
    (a) => a.tier === 'EVACUATE' || a.tier === 'WARNING'
  ).length;

  return (
    <header className="bg-slate-950/95 border-b border-slate-800/80 sticky top-0 z-40 backdrop-blur px-4 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Brand & Region */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-600 via-orange-600 to-amber-600 flex items-center justify-center shadow-md shadow-red-950/60 ring-1 ring-white/20">
            <ShieldAlert className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-black tracking-wider text-slate-100 uppercase font-mono">
                SIH-26192 <span className="text-orange-500">DISASTER EWS</span>
              </h1>
              <span className="hidden md:inline-block px-1.5 py-0.5 text-[10px] font-bold rounded bg-red-950 text-red-400 border border-red-800/60 uppercase tracking-widest font-mono">
                MHA / NDRF
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="flex items-center gap-1 text-slate-300 font-medium">
                <MapPin className="w-3 h-3 text-orange-400" /> Uttarkashi District, Uttarakhand
              </span>
              <span className="text-slate-600">•</span>
              <span className="flex items-center gap-1 text-slate-400 text-[11px] font-mono">
                <Clock className="w-3 h-3 text-slate-500" /> {currentTime || 'Loading...'}
              </span>
            </div>
          </div>
        </div>

        {/* Center: Live Status & Incidents */}
        <div className="hidden lg:flex items-center gap-3">
          <StatusIndicator isOnline={isOnline} activeIncidentsCount={activeIncidents} />
          <span className="text-[11px] font-mono text-slate-500 bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800">
            Sync: {lastUpdated}
          </span>
        </div>

        {/* Right: Actions, Citizen Toggle & Role Switcher */}
        <div className="flex items-center gap-2.5">
          {/* Quick Dispatch Alert Button (for officers) */}
          {onOpenAlertModal && (
            <button
              onClick={onOpenAlertModal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-red-600 hover:bg-red-500 text-white text-xs font-bold font-mono tracking-wider transition-colors shadow-md shadow-red-950/60 border border-red-400/30 active:scale-95"
            >
              <Radio className="w-3.5 h-3.5 animate-pulse" />
              <span>DISPATCH ALERT</span>
            </button>
          )}

          {/* Tourist Mode Quick Link */}
          <button
            onClick={() => navigate('/tourist')}
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-mono border border-slate-700 transition-colors"
            title="Simplified location-aware guidance for pilgrims & tourists"
          >
            <Compass className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline">Tourist / Pilgrim</span>
          </button>

          {/* Citizen App Toggle */}
          <Link
            to="/citizen"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-emerald-950/80 hover:bg-emerald-900/90 text-emerald-300 text-xs font-mono font-bold border border-emerald-500/40 transition-colors"
            title="Open ultra-simplified mobile citizen emergency interface"
          >
            <Smartphone className="w-3.5 h-3.5 text-emerald-400" />
            <span>CITIZEN PWA</span>
          </Link>

          {/* Role Switcher Pill */}
          <div className="flex items-center gap-1.5 bg-slate-900 px-2 py-1 rounded-md border border-slate-800 text-xs font-mono">
            <User className="w-3.5 h-3.5 text-orange-400" />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="bg-transparent text-slate-200 text-xs font-mono outline-none cursor-pointer"
              title="Switch user operational profile"
            >
              <option value="DISTRICT_OFFICER" className="bg-slate-900 text-white">
                Officer: {badgeNumber}
              </option>
              <option value="NDRF_COMMANDER" className="bg-slate-900 text-white">
                NDRF: Cmdt. Bhardwaj
              </option>
              <option value="FIELD_VOLUNTEER" className="bg-slate-900 text-white">
                Volunteer: Aapda Mitra
              </option>
              <option value="CITIZEN" className="bg-slate-900 text-white">
                Citizen View
              </option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
