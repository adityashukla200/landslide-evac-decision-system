import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useEmergency } from '../../context/EmergencyContext';
import { useAuth } from '../../context/AuthContext';
import { StatusIndicator } from './StatusIndicator';
import {
  ShieldAlert,
  Smartphone,
  Clock,
  User,
  Radio,
  Compass,
  LogOut,
  Shield,
  Lock,
} from 'lucide-react';
import { UserRole } from '../../types';

interface HeaderProps {
  onOpenAlertModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenAlertModal }) => {
  const { isOnline, alerts, lastUpdated } = useEmergency();
  const {
    role,
    setRole,
    userName,
    badgeNumber,
    isAuthenticated,
    isOfficer,
    officer,
    logout,
    openLoginModal,
  } = useAuth();
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
                HYPER-LOCAL <span className="text-orange-500">FLASHFLOOD PREDICTION</span>
              </h1>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
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
              onClick={() => {
                if (!isOfficer) {
                  openLoginModal('Officer login required to dispatch emergency directives.');
                  return;
                }
                onOpenAlertModal();
              }}
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

          {/* Officer Login / Logged In State */}
          {isAuthenticated && officer ? (
            <div className="flex items-center gap-2 bg-slate-900/90 pl-2.5 pr-1.5 py-1 rounded-md border border-emerald-500/40 text-xs font-mono shadow-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <div className="flex flex-col text-left">
                <span className="text-slate-100 font-bold leading-tight truncate max-w-[110px] sm:max-w-[140px]">
                  {officer.name}
                </span>
                <span className="text-[10px] text-emerald-400 leading-tight">
                  {officer.role.toUpperCase()} • {officer.district}
                </span>
              </div>
              <button
                onClick={() => logout()}
                className="ml-1 p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-red-400 transition-colors"
                title="Logout officer session"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => openLoginModal()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gradient-to-r from-orange-600/30 to-amber-600/30 hover:from-orange-600/50 hover:to-amber-600/50 text-orange-300 hover:text-white border border-orange-500/50 text-xs font-mono font-bold transition-all shadow-sm active:scale-95"
              title="Authenticate as District / NDRF / State Officer"
            >
              <Shield className="w-3.5 h-3.5 text-orange-400" />
              <span>Officer Login</span>
            </button>
          )}

          {/* Role Switcher Pill */}
          <div className="flex items-center gap-1.5 bg-slate-900 px-2.5 py-1.5 rounded-md border border-slate-800 text-xs font-mono">
            <User className="w-3.5 h-3.5 text-orange-400" />
            <select
              value={role}
              onChange={(e) => {
                const newRole = e.target.value as UserRole;
                if ((newRole === 'DISTRICT_OFFICER' || newRole === 'NDRF_COMMANDER') && !isAuthenticated) {
                  openLoginModal('Officer authentication required to access official command features.');
                  return;
                }
                setRole(newRole);
                if (newRole === 'CITIZEN') {
                  navigate('/citizen');
                } else if (window.location.pathname === '/citizen') {
                  navigate('/');
                }
              }}
              className="bg-transparent text-slate-200 text-xs font-mono outline-none cursor-pointer"
              title="Switch user role mode"
            >
              <option value="DISTRICT_OFFICER" className="bg-slate-900 text-white">
                Officer View
              </option>
              <option value="CITIZEN" className="bg-slate-900 text-white">
                Citizen View
              </option>
              <option value="NDRF_COMMANDER" className="bg-slate-900 text-white">
                NDRF View
              </option>
              <option value="FIELD_VOLUNTEER" className="bg-slate-900 text-white">
                Volunteer View
              </option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
