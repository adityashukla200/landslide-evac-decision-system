import React, { useState } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { ScenarioBar } from './components/common/ScenarioBar';
import { AlertCreationModal } from './components/alerts/AlertCreationModal';
import { OfficerLoginModal } from './components/auth/OfficerLoginModal';

// Pages
import { CommandCenter } from './pages/CommandCenter';
import { LiveRiskMapPage } from './pages/LiveRiskMapPage';
import { VillagesPage } from './pages/VillagesPage';
import { AlertsPage } from './pages/AlertsPage';
import { EvacuationPage } from './pages/EvacuationPage';
import { SheltersPage } from './pages/SheltersPage';
import { SensorsPage } from './pages/SensorsPage';
import { VolunteersPage } from './pages/VolunteersPage';
import { VulnerablePage } from './pages/VulnerablePage';
import { SimulatorPage } from './pages/SimulatorPage';
import { ReplayPage } from './pages/ReplayPage';
import { ReportsPage } from './pages/ReportsPage';
import { HealthPage } from './pages/HealthPage';
import { CitizenPWA } from './pages/CitizenPWA';
import { TouristMode } from './pages/TouristMode';
import { CitizenReportPage } from './pages/CitizenReportPage';

const MainLayout: React.FC<{ onOpenAlertModal: () => void }> = ({ onOpenAlertModal }) => {
  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-orange-500 selection:text-white">
      {/* Top Mission Control Header */}
      <Header onOpenAlertModal={onOpenAlertModal} />

      {/* SIH Scenario Controller Bar */}
      <ScenarioBar />

      {/* Main Body with Sidebar + Content Outlet */}
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-4 lg:p-5 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);

  return (
    <>
      <Routes>
        {/* Full-screen Standalone Mobile / Public Experiences */}
        <Route path="/citizen" element={<CitizenPWA />} />
        <Route path="/tourist" element={<TouristMode />} />
        <Route path="/report" element={<CitizenReportPage />} />

        {/* Command Center Operational Routes */}
        <Route
          element={<MainLayout onOpenAlertModal={() => setIsAlertModalOpen(true)} />}
        >
          <Route path="/" element={<CommandCenter />} />
          <Route path="/map" element={<LiveRiskMapPage />} />
          <Route path="/villages" element={<VillagesPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/evacuation" element={<EvacuationPage />} />
          <Route path="/shelters" element={<SheltersPage />} />
          <Route path="/sensors" element={<SensorsPage />} />
          <Route path="/volunteers" element={<VolunteersPage />} />
          <Route path="/vulnerable" element={<VulnerablePage />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="/replay" element={<ReplayPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/health" element={<HealthPage />} />
        </Route>

        {/* Wildcard Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* Global Emergency Alert Dispatch Modal */}
      <AlertCreationModal
        isOpen={isAlertModalOpen}
        onClose={() => setIsAlertModalOpen(false)}
      />

      {/* Officer Authentication Modal */}
      <OfficerLoginModal />
    </>
  );
};

export default App;
