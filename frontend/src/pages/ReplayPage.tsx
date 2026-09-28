import React from 'react';
import { EventReplay } from '../components/simulation/EventReplay';

export const ReplayPage: React.FC = () => {
  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      <EventReplay />
    </div>
  );
};
