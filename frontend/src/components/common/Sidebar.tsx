import React from 'react';
import { NavLink } from 'react-router-dom';
import { useEmergency } from '../../context/EmergencyContext';
import {
  LayoutDashboard,
  Map as MapIcon,
  Home,
  BellRing,
  Footprints,
  Activity,
  Building2,
  Users,
  HeartHandshake,
  Sliders,
  History,
  FileSpreadsheet,
  Cpu,
  Compass,
} from 'lucide-react';

interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const { alerts, villages } = useEmergency();

  const evacuateCount = villages.filter((v) => v.risk.tier === 'EVACUATE').length;
  const warningCount = villages.filter((v) => v.risk.tier === 'WARNING').length;
  const activeAlerts = alerts.filter((a) => a.tier === 'EVACUATE' || a.tier === 'WARNING').length;

  const links = [
    { to: '/', label: 'Command Center', icon: LayoutDashboard, exact: true },
    {
      to: '/map',
      label: 'Live Risk Map',
      icon: MapIcon,
      badge: evacuateCount > 0 ? `${evacuateCount} EVAC` : warningCount > 0 ? `${warningCount} WARN` : undefined,
      badgeColor: evacuateCount > 0 ? 'bg-red-950 text-red-400 border-red-800' : 'bg-orange-950 text-orange-400 border-orange-800',
    },
    { to: '/villages', label: 'Villages & Wards', icon: Home },
    {
      to: '/alerts',
      label: 'Alert Management',
      icon: BellRing,
      badge: activeAlerts > 0 ? `${activeAlerts}` : undefined,
      badgeColor: 'bg-red-950 text-red-400 border-red-800 animate-pulse',
    },
    { to: '/evacuation', label: 'Evacuation & Routes', icon: Footprints },
    { to: '/shelters', label: 'Shelters & Capacity', icon: Building2 },
    { to: '/sensors', label: 'Sensors & Telemetry', icon: Activity },
    { to: '/volunteers', label: 'Volunteer Tasks', icon: Users },
    { to: '/vulnerable', label: 'Vulnerable Citizens', icon: HeartHandshake },
    { to: '/simulator', label: 'What-If Simulator', icon: Sliders },
    { to: '/replay', label: 'Disaster Replay Mode', icon: History },
    { to: '/reports', label: 'Community Reports', icon: FileSpreadsheet },
    { to: '/tourist', label: 'Tourist / Pilgrim Guide', icon: Compass },
    { to: '/health', label: 'System Health & AI Logs', icon: Cpu },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between shrink-0 select-none">
      <div className="py-3 overflow-y-auto">
        <div className="px-4 mb-2 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">
          Mission Control Navigation
        </div>
        <nav className="space-y-0.5 px-2">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.exact}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-md text-xs font-mono tracking-wide transition-all ${
                    isActive
                      ? 'bg-orange-950/80 border border-orange-500/40 text-orange-300 font-bold shadow-sm shadow-orange-950/50'
                      : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200 border border-transparent'
                  }`
                }
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{link.label}</span>
                </div>
                {link.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded border font-mono font-bold ${
                      link.badgeColor || 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {link.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer District Status Pill */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/80">
        <div className="p-2.5 rounded-md bg-slate-900/80 border border-slate-800 text-xs font-mono">
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span>PILOT DISTRICT:</span>
            <span className="font-bold text-slate-200">UTTARKASHI</span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
            <span>25 VILLAGES:</span>
            <span className="text-emerald-400 font-bold">100% MONITORED</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
