import React from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { VolunteerTask, TaskStatus } from '../types';
import { Users, Clock, CheckCircle2, Play, AlertCircle, Phone, MapPin } from 'lucide-react';

export const VolunteersPage: React.FC = () => {
  const { tasks, updateTaskStatus } = useEmergency();

  const handleAdvanceStatus = (task: VolunteerTask) => {
    const nextStatusMap: Record<TaskStatus, TaskStatus> = {
      PENDING: 'ACCEPTED',
      ACCEPTED: 'IN_PROGRESS',
      IN_PROGRESS: 'COMPLETED',
      COMPLETED: 'COMPLETED',
    };
    updateTaskStatus(task.id, nextStatusMap[task.status]);
  };

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-base font-bold text-slate-100 font-mono">VOLUNTEER TASK DISPATCH & AAPDA MITRA</h2>
        <p className="text-xs text-slate-400">
          Last-mile evacuation assistance cards assigned to registered Aapda Mitra volunteers
        </p>
      </div>

      {/* Tasks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {tasks.map((task) => {
          const statusConfig = {
            PENDING: { bg: 'bg-amber-950 text-amber-300 border-amber-800', label: 'PENDING ACCEPTANCE' },
            ACCEPTED: { bg: 'bg-blue-950 text-blue-300 border-blue-800', label: 'ACCEPTED' },
            IN_PROGRESS: { bg: 'bg-orange-950 text-orange-300 border-orange-800 animate-pulse', label: 'IN PROGRESS' },
            COMPLETED: { bg: 'bg-emerald-950 text-emerald-300 border-emerald-800', label: 'COMPLETED' },
          }[task.status];

          return (
            <div
              key={task.id}
              className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-md space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-2">
                  <div>
                    <span className="text-[10px] text-slate-500 font-bold block">{task.id}</span>
                    <h3 className="font-bold text-slate-100 text-sm">{task.volunteerName}</h3>
                    <div className="text-[10px] text-slate-400 flex items-center gap-1">
                      <Phone className="w-3 h-3 text-slate-500" /> {task.volunteerPhone}
                    </div>
                  </div>

                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${statusConfig.bg}`}>
                    {statusConfig.label}
                  </span>
                </div>

                {/* Location & Details */}
                <div className="space-y-1 text-[11px] text-slate-300">
                  <div className="flex items-center gap-1.5 font-bold text-orange-400">
                    <MapPin className="w-3.5 h-3.5" />
                    <span>{task.ward}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Target: </span>
                    <strong>{task.targetHouseholds} Households ({task.vulnerableCount} citizens)</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Destination: </span>
                    <strong className="text-blue-400">{task.destinationShelter}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Safe Route: </span>
                    <strong className="text-emerald-400">{task.recommendedRoute}</strong>
                  </div>
                </div>

                {/* Special Needs Box */}
                <div className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-400">
                  <span className="text-amber-400 font-bold block text-[10px]">Special Assistance Note:</span>
                  <p className="mt-0.5 leading-tight">{task.specialNeeds}</p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-slate-800 flex items-center justify-between gap-2">
                <span className="text-orange-400 font-bold text-[11px] flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> ~{task.timeRemainingMin}m left
                </span>

                {task.status !== 'COMPLETED' && (
                  <button
                    onClick={() => handleAdvanceStatus(task)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-bold text-[11px] transition-colors"
                  >
                    {task.status === 'PENDING' ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5" /> ACCEPT TASK
                      </>
                    ) : task.status === 'ACCEPTED' ? (
                      <>
                        <Play className="w-3.5 h-3.5" /> START EVACUATION
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5" /> MARK COMPLETED
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
