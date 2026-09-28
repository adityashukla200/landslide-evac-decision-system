import React from 'react';
import { useAuth } from '../context/AuthContext';
import { INITIAL_VULNERABLE } from '../services/mockData';
import { HeartHandshake, ShieldAlert, Phone, UserCheck, AlertTriangle } from 'lucide-react';

export const VulnerablePage: React.FC = () => {
  const { isOfficer } = useAuth();

  if (!isOfficer) {
    return (
      <div className="flex-1 p-8 bg-slate-950 flex flex-col items-center justify-center font-mono text-center select-none">
        <ShieldAlert className="w-12 h-12 text-red-400 mb-3" />
        <h3 className="text-base font-bold text-slate-100">RESTRICTED PRIVACY ACCESS</h3>
        <p className="text-xs text-slate-400 max-w-md mt-1">
          Vulnerable citizen registries contain sensitive personal health and mobility records. Access is restricted to authorized Disaster Management Officers and NDRF personnel.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          <HeartHandshake className="w-5 h-5 text-red-400" />
          <h2 className="text-base font-bold text-slate-100 font-mono">VULNERABLE CITIZEN & HOUSEHOLD REGISTRY</h2>
        </div>
        <p className="text-xs text-slate-400">
          Priority tracking for elderly, bedridden, mobility-impaired, and pregnant citizens requiring dedicated volunteer escort
        </p>
      </div>

      {/* Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-md">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px]">
            <tr>
              <th className="py-2.5 px-4">Household Head</th>
              <th className="px-4">Village</th>
              <th className="px-4">Vulnerability Category</th>
              <th className="px-4">Members</th>
              <th className="px-4">Assigned Volunteer</th>
              <th className="px-4">Evacuation Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-slate-200">
            {INITIAL_VULNERABLE.map((hh) => {
              const statusConfig = {
                'Safe at Shelter': 'bg-emerald-950 text-emerald-300 border-emerald-800',
                Evacuating: 'bg-orange-950 text-orange-300 border-orange-800 animate-pulse',
                'Needs Assistance': 'bg-red-950 text-red-300 border-red-800 font-bold',
                'Awaiting Volunteer': 'bg-amber-950 text-amber-300 border-amber-800',
              }[hh.evacuationStatus];

              return (
                <tr key={hh.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-bold text-slate-100">{hh.headOfHousehold}</div>
                    <div className="text-[10px] text-slate-500 flex items-center gap-1">
                      <Phone className="w-3 h-3 text-slate-500" /> {hh.contactPhone}
                    </div>
                  </td>
                  <td className="px-4 font-bold text-slate-300">{hh.villageName}</td>
                  <td className="px-4">
                    <span className="px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800 text-[11px]">
                      {hh.vulnerabilityType}
                    </span>
                  </td>
                  <td className="px-4 font-bold">{hh.membersCount} citizens</td>
                  <td className="px-4">
                    <div className="flex items-center gap-1 text-slate-300 font-bold">
                      <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>{hh.assignedVolunteerName}</span>
                    </div>
                  </td>
                  <td className="px-4">
                    <span className={`px-2 py-0.5 rounded border text-[10px] ${statusConfig}`}>
                      {hh.evacuationStatus}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
