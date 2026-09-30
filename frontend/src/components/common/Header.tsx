import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useEmergency } from '../../context/EmergencyContext';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useToast } from '../../context/ToastContext';
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
  Sun,
  Moon,
} from 'lucide-react';
import { UserRole } from '../../types';

interface HeaderProps {
  onOpenAlertModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenAlertModal }) => {
  const { isOnline, alerts, lastUpdated } = useEmergency();
  const { isDark, toggleTheme } = useTheme();
  const { info } = useToast();
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

  const handleLogout = () => {
    logout();
    info('You have logged out of the officer session.', 'Session Ended');
  };

  return (
    <header className="bg-white/95 dark:bg-slate-950/95 border-b border-slate-200 dark:border-slate-800/80 sticky top-0 z-40 backdrop-blur px-3 sm:px-4 py-2 transition-colors">
      <div className="flex flex-wrap items-center justify-between gap-2 sm:gap-3">
        {/* Left: Brand & Region */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-br from-red-600 via-orange-600 to-amber-600 flex items-center justify-center shadow-md shadow-red-950/60 ring-1 ring-white/20 shrink-0">
            <ShieldAlert className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xs sm:text-base font-black tracking-wider text-slate-900 dark:text-slate-100 uppercase font-mono">
                HYPER-LOCAL <span className="text-orange-500">FLASHFLOOD</span>
              </h1>
            </div>
            <div className="flex items-center gap-2 text-[10px] sm:text-xs text-slate-600 dark:text-slate-400">
              <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400 text-[10px] sm:text-[11px] font-mono">
                <Clock className="w-3 h-3 text-slate-500" /> {currentTime || 'Loading...'}
              </span>
            </div>
          </div>
        </div>

        {/* Center: Live Status & Incidents */}
        <div className="hidden lg:flex items-center gap-3">
          <StatusIndicator isOnline={isOnline} activeIncidentsCount={activeIncidents} />
          <span className="text-[11px] font-mono text-slate-600 dark:text-slate-500 bg-slate-100 dark:bg-slate-900/60 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-800">
            Sync: {lastUpdated}
          </span>
        </div>

        {/* Right: Actions, Citizen Toggle & Role Switcher */}
        <div className="flex items-center gap-1.5 sm:gap-2.5">
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
              aria-label="Dispatch Emergency Alert"
              className="flex items-center gap-1 sm:gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md bg-red-600 hover:bg-red-500 text-white text-[11px] sm:text-xs font-bold font-mono tracking-wider transition-colors shadow-md shadow-red-950/60 border border-red-400/30 active:scale-95 min-h-[36px]"
            >
              <Radio className="w-3.5 h-3.5 animate-pulse shrink-0" />
              <span className="hidden xs:inline sm:inline">DISPATCH</span>
            </button>
          )}

          {/* Tourist Mode Quick Link */}
          <button
            onClick={() => navigate('/tourist')}
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white text-xs font-mono border border-slate-300 dark:border-slate-700 transition-colors min-h-[36px]"
            title="Simplified location-aware guidance for pilgrims & tourists"
            aria-label="Open Tourist and Pilgrim Mode"
          >
            <Compass className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />
            <span>Tourist</span>
          </button>

          {/* Citizen App Toggle */}
          <Link
            to="/citizen"
            className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-md bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-950/80 dark:hover:bg-emerald-900/90 text-emerald-800 dark:text-emerald-300 text-[11px] sm:text-xs font-mono font-bold border border-emerald-400 dark:border-emerald-500/40 transition-colors min-h-[36px]"
            title="Open ultra-simplified mobile citizen emergency interface"
            aria-label="Open Citizen Mobile Emergency App"
          >
            <Smartphone className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>CITIZEN</span>
          </Link>

          {/* Officer Login / Logged In State */}
          {isAuthenticated && officer ? (
            <div className="flex items-center gap-1.5 sm:gap-2 bg-slate-100 dark:bg-slate-900/90 pl-2 sm:pl-2.5 pr-1.5 py-1 rounded-md border border-emerald-500/50 text-xs font-mono shadow-sm min-h-[36px]">
              <span className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse shrink-0" />
              <div className="flex flex-col text-left">
                <span className="text-slate-900 dark:text-slate-100 font-bold leading-tight truncate max-w-[80px] sm:max-w-[140px] text-[11px] sm:text-xs">
                  {officer.name}
                </span>
                <span className="text-[9px] sm:text-[10px] text-emerald-700 dark:text-emerald-400 leading-tight font-bold">
                  {officer.role.toUpperCase()}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="ml-1 p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors focus-visible:ring-2 focus-visible:ring-orange-500"
                title="Logout officer session"
                aria-label="Logout officer session"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => openLoginModal()}
              className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 rounded-md bg-gradient-to-r from-orange-500/20 to-amber-500/20 dark:from-orange-600/30 dark:to-amber-600/30 hover:from-orange-500/30 hover:to-amber-500/30 text-orange-900 dark:text-orange-300 hover:text-orange-950 dark:hover:text-white border border-orange-400 dark:border-orange-500/50 text-[11px] sm:text-xs font-mono font-bold transition-all shadow-sm active:scale-95 min-h-[36px]"
              title="Authenticate as District / NDRF / State Officer"
              aria-label="Officer Login"
            >
              <Shield className="w-3.5 h-3.5 text-orange-600 dark:text-orange-400 shrink-0" />
              <span>Login</span>
            </button>
          )}

          {/* Role Switcher Pill */}
          <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-900 px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-800 text-xs font-mono">
            <User className="w-3.5 h-3.5 text-orange-600 dark:text-orange-400" />
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
              className="bg-transparent text-slate-800 dark:text-slate-200 text-xs font-mono outline-none cursor-pointer"
              title="Switch user role mode"
            >
              <option value="DISTRICT_OFFICER" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Officer View
              </option>
              <option value="CITIZEN" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Citizen View
              </option>
              <option value="NDRF_COMMANDER" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                NDRF View
              </option>
              <option value="FIELD_VOLUNTEER" className="bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                Volunteer View
              </option>
            </select>
          </div>

          {/* Theme Toggle Button (Light / Dark) */}
          <button
            onClick={toggleTheme}
            className="flex items-center justify-center p-2 rounded-md bg-slate-100 hover:bg-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white border border-slate-300 dark:border-slate-800 transition-colors shadow-sm active:scale-95"
            title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            aria-label="Toggle Light and Dark Theme"
          >
            {isDark ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-600" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
