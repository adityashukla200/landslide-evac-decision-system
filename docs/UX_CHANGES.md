# User Experience (UX) Changelog & Improvements

**Project**: Hyper-Local FlashFlood Prediction (SIH 2026, PS 26192)  
**Scope**: Frontend UX/UI overhaul across all citizen and command center surfaces  
**Backend Impact**: Zero alterations to backend logic, APIs, or tested database models  

---

## 1. Loading States & Action Feedback (Toast Notifications)
- **Global Toast Notification Architecture (`frontend/src/context/ToastContext.tsx`)**:
  - Implemented `ToastProvider` with `useToast()` hook supporting `success`, `error`, `warning`, and `info` notifications.
  - Rendered in a fixed floating container with automatic auto-dismiss (4000ms), manual dismissal button, and accessible ARIA attributes (`role="alert"`, `aria-live="polite"`).
- **Officer Authentication Feedback**:
  - `OfficerLoginModal.tsx`: Displays success toast (`"Welcome to DEOC Command Center. Session authenticated."`) upon login, and clear error toast on invalid credentials or rate limiting.
  - `Header.tsx`: Displays info toast (`"You have logged out of the officer session."`) upon logout.
- **Emergency Broadcast Feedback**:
  - `AlertCreationModal.tsx`: Displays success toast (`"Emergency [TIER] alert dispatched to [Village]! Cell Broadcast & Sirens triggered."`) on dispatch, or error toast if network failure occurs.
- **Threshold Calibration Feedback**:
  - `VillageDetailPanel.tsx`: Replaced intrusive native browser `alert()` popups with toast notifications (`"Operational thresholds updated for [Village]."` or calibration error message).
- **Citizen Ground-Truth Feedback**:
  - `CitizenReportPage.tsx`: Displays success toast (`"Thank you! Your report was received. Your vigilance helps keep your community safe."`) upon submission.
  - `CitizenPWA.tsx`: Displays immediate success feedback on shelter check-in (`"Checked in safe. Incident commander notified."`) and quick report transmission.
- **Loading Skeletons (`frontend/src/components/common/Skeleton.tsx`)**:
  - Created reusable animated pulse skeletons (`Skeleton`, `CardSkeleton`, `TableRowSkeleton`) replacing blank loading blocks across the village dossier panel and telemetry lists.

---

## 2. Interactive Map UX (`RiskMap.tsx`)
- **Interactive Village Hover Tooltips**:
  - Hovering over any village marker dynamically renders a clean, floating MapLibre GL popup displaying:
    - Village name
    - Severity risk tier badge (with WCAG AA compliant colors)
    - Population figure
    - Real-time flood risk probability percentage
  - Mouse pointer switches to a hand cursor on hover and gracefully destroys the tooltip on mouse leave.
- **Visual Highlight for Inspected Village**:
  - Added dedicated dynamic GeoJSON property `selected: selectedVillage.id === v.id`.
  - Mounted two persistent highlight layers:
    1. `villages-selected-glow`: Luminous orange ambient halo (radius 22px–44px, blur 0.5) centered on the active village.
    2. `villages-selected-ring`: High-visibility white double-ring stroke (width 3.5px) identifying the selected village.
- **Smooth Panel Transitions**:
  - Clicking any village opens the dossier panel with a smooth CSS slide-in animation (`animate-slide-in-right`) instead of a jarring jump.

---

## 3. Mobile Responsiveness & 375px Viewport Audit
- **Officer Header (`Header.tsx`)**:
  - Optimized layout for mobile viewports (down to 375px):
    - Compact brand title (`HYPER-LOCAL FLASHFLOOD`) preventing awkward line wraps.
    - Compact action buttons (`DISPATCH`, `CITIZEN`, `Login`) with minimum touch targets >= 36px.
    - Truncated officer profile badges preventing horizontal overflow.
- **Citizen Report Page (`CitizenReportPage.tsx`)**:
  - Designed for **one-handed thumb operation on mobile phones**:
    - Sticky bottom submission bar (`sticky bottom-3 z-30`) keeping the primary submit action accessible at the bottom of the viewport while scrolling through photo uploads and notes.
    - Large tap targets (minimum height 50px) for file upload, camera, flood selection pills, and submit button.
    - Single-column layout with clean margins and zero horizontal scroll.
- **Village Detail Panel (`VillageDetailPanel.tsx`)**:
  - Made responsive across screens: `w-full sm:w-96 md:w-[420px] max-w-full fixed sm:relative right-0 top-0 sm:top-auto h-full`.
  - On phones (<640px), slides in as a full-width overlay drawer with a prominent close button so operators can easily dismiss it to return to the map.

---

## 4. Friendly Empty and Error States (`EmptyState.tsx`)
- Created a reusable `EmptyState` component supporting icon indicators, titles, plain-language descriptions, and primary action buttons.
- **Alert Center (`AlertsPage.tsx`)**:
  - If no alerts are active, displays a reassuring empty state ("No Active Emergency Alerts in Uttarkashi district") with a button to dispatch a new directive.
- **Community Reports (`ReportsPage.tsx`)**:
  - If zero citizen observations are submitted, displays a friendly prompt explaining that no reports exist yet and invites the user to submit the first observation.
- **Hardware Telemetry (`SensorsPage.tsx`)**:
  - If telemetry streams are offline or empty, displays an informative offline state with an action to recheck mesh/MQTT connectivity.
- **Village Reports Dossier (`VillageDetailPanel.tsx`)**:
  - When a village has no field reports, displays an empty illustration with a direct link to submit the first observation for that village.

---

## 5. Accessibility (a11y) Enhancements
- **Accessible ARIA Labels**:
  - Added descriptive `aria-label`s to all icon-only buttons:
    - Theme toggle (`aria-label="Toggle Light and Dark Theme"`)
    - Modal close buttons (`aria-label="Close dialog"`)
    - Toast dismiss buttons (`aria-label="Dismiss notification"`)
    - Dispatch alert button (`aria-label="Dispatch Emergency Alert"`)
    - Citizen PWA toggle (`aria-label="Open Citizen Mobile Emergency App"`)
- **Visible Focus Rings**:
  - Added `focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:outline-none` across interactive buttons, inputs, selects, and textareas.
- **Keyboard Navigation**:
  - Added `Escape` key listener in `OfficerLoginModal.tsx` and `Modal.tsx` for closing dialogs via keyboard.
  - Maintained logical Tab index order across forms.
- **Image Alternative Text**:
  - Verified `alt` attributes on all citizen evidence thumbnails, previews, and badges.

---

## 6. Micro-Copy Pass (English & Hindi)
- Replaced technical jargon with plain, human-friendly, and compassionate language:
  - **Before**: "Citizen Ground-Truth Report"  
    **After**: "Report Flood or Landslide" / "नागरिक आपदा रिपोर्ट"
  - **Before**: "Factor of Safety limit-equilibrium threshold"  
    **After**: "Slope Stability: Safe / High Landslide Risk"
  - **Before**: "Geotagged EXIF metadata stripped per DPDP Act"  
    **After**: "🔒 Privacy Protected: Personal device details are stripped automatically" / "🔒 आपकी गोपनीयता सुरक्षित है: व्यक्तिगत जानकारी अपने आप हटा दी जाती है।"
  - **Before**: "Disseminate Directive"  
    **After**: "Send Emergency Alert" / "तुरंत आपातकालीन सूचना भेजें"

---

## 7. Performance Optimization & Lazy Loading
- **Route-Level Code Splitting (`App.tsx`)**:
  - Converted all 16 page routes to `React.lazy()` with dynamic `import()`.
  - Initial bundle size dropped dramatically:
    - **Initial JS bundle**: reduced from **1,271 kB** down to **260 kB** (79.79 kB gzipped) — a **79.5% reduction** in initial payload!
- **App-Level Loading Screen (`AppLoadingScreen.tsx`)**:
  - Added an animated branded loading splash as the `<Suspense>` fallback, showing the early warning emblem, district subtitle, and progress spinner while lazy chunks download.
