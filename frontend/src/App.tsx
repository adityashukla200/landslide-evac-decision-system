import React, { useState, lazy, Suspense } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { AlertCreationModal } from './components/alerts/AlertCreationModal';
import { OfficerLoginModal } from './components/auth/OfficerLoginModal';
import { AppLoadingScreen } from './components/common/AppLoadingScreen';

// Lazy-loaded pages for high performance and minimal initial bundle size
const CommandCenter = lazy(() => import('./pages/CommandCenter').then((m) => ({ default: m.CommandCenter })));
const LiveRiskMapPage = lazy(() => import('./pages/LiveRiskMapPage').then((m) => ({ default: m.LiveRiskMapPage })));
const VillagesPage = lazy(() => import('./pages/VillagesPage').then((m) => ({ default: m.VillagesPage })));
const AlertsPage = lazy(() => import('./pages/AlertsPage').then((m) => ({ default: m.AlertsPage })));
const EvacuationPage = lazy(() => import('./pages/EvacuationPage').then((m) => ({ default: m.EvacuationPage })));
const SheltersPage = lazy(() => import('./pages/SheltersPage').then((m) => ({ default: m.SheltersPage })));
const SensorsPage = lazy(() => import('./pages/SensorsPage').then((m) => ({ default: m.SensorsPage })));
const VolunteersPage = lazy(() => import('./pages/VolunteersPage').then((m) => ({ default: m.VolunteersPage })));
const VulnerablePage = lazy(() => import('./pages/VulnerablePage').then((m) => ({ default: m.VulnerablePage })));
const SimulatorPage = lazy(() => import('./pages/SimulatorPage').then((m) => ({ default: m.SimulatorPage })));
const ReplayPage = lazy(() => import('./pages/ReplayPage').then((m) => ({ default: m.ReplayPage })));
const ReportsPage = lazy(() => import('./pages/ReportsPage').then((m) => ({ default: m.ReportsPage })));
const HealthPage = lazy(() => import('./pages/HealthPage').then((m) => ({ default: m.HealthPage })));
const CitizenPWA = lazy(() => import('./pages/CitizenPWA').then((m) => ({ default: m.CitizenPWA })));
const TouristMode = lazy(() => import('./pages/TouristMode').then((m) => ({ default: m.TouristMode })));
const CitizenReportPage = lazy(() => import('./pages/CitizenReportPage').then((m) => ({ default: m.CitizenReportPage })));

const MainLayout: React.FC<{ onOpenAlertModal: () => void }> = ({ onOpenAlertModal }) => {
  return (
    <div className="flex flex-col min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans selection:bg-orange-500 selection:text-white transition-colors duration-200">
      {/* Top Mission Control Header */}
      <Header onOpenAlertModal={onOpenAlertModal} />

      {/* Main Body with Sidebar + Content Outlet */}
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-4 lg:p-5 bg-gradient-to-b from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 transition-colors duration-200">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);

  return (
    <Suspense fallback={<AppLoadingScreen />}>
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
    </Suspense>
  );
};

export default App;
