import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Camera,
  Video,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  WifiOff,
  Languages,
  Upload,
  RefreshCw,
  X,
  Phone,
  MessageSquare,
  ArrowLeft,
  Info,
  Sun,
  Moon,
} from 'lucide-react';
import { reportService, QueuedOfflineReport } from '../services/reportService';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';

export const CitizenReportPage: React.FC = () => {
  const { isDark, toggleTheme } = useTheme();
  const { success: showSuccessToast, error: showErrorToast } = useToast();
  const [language, setLanguage] = useState<'en' | 'hi'>('hi');
  const [reportedFlood, setReportedFlood] = useState<boolean>(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [caption, setCaption] = useState<string>('');
  const [phone, setPhone] = useState<string>('');

  // GPS state
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [gpsLoading, setGpsLoading] = useState<boolean>(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [manualLocationMode, setManualLocationMode] = useState<boolean>(false);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isOfflineQueued, setIsOfflineQueued] = useState<boolean>(false);

  // Network state
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [queuedCount, setQueuedCount] = useState<number>(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    document.title = 'Hyper-Local FlashFlood Prediction — Report';
  }, []);

  // Dictionary for Bilingual text (Plain, empathetic language)
  const t = {
    title: language === 'hi' ? 'आपदा रिपोर्ट भेजें' : 'Report Flood or Landslide',
    subtitle:
      language === 'hi'
        ? 'गाँव और राहत दल को सतर्क करने के लिए एक फोटो या वीडियो साझा करें'
        : 'Share a photo or video to alert local rescue teams and your village',
    questionTitle:
      language === 'hi' ? 'यहाँ स्थिति कैसी है?' : 'What is the current ground situation?',
    yesFlood: language === 'hi' ? '⚠️ बाढ़ या भूस्खलन है' : '⚠️ Flooding or Landslide Active',
    noFlood: language === 'hi' ? '✅ सुरक्षित है / कोई बाढ़ नहीं' : '✅ Area is Safe / Water Receded',
    photoVideoLabel: language === 'hi' ? 'फोटो या वीडियो जोड़ें' : 'Add Photo or Video',
    chooseFile: language === 'hi' ? 'कैमरा खोलें या गैलरी से चुनें' : 'Open Camera or Choose File',
    fileSizeHint:
      language === 'hi'
        ? 'फोटो या वीडियो (JPG, PNG, MP4) • 60MB तक'
        : 'Photo or video up to 60MB (JPG, PNG, MP4)',
    gpsTitle: language === 'hi' ? 'आपकी लोकेशन (GPS)' : 'Your Location (GPS)',
    gpsFetching: language === 'hi' ? 'GPS से लोकेशन खोजी जा रही है...' : 'Finding your exact location...',
    gpsSuccess: language === 'hi' ? 'सटीक लोकेशन मिल गई' : 'Exact location acquired',
    gpsFallback:
      language === 'hi' ? 'गाँव की सूची से चुनें' : 'Choose village from list',
    captionLabel: language === 'hi' ? 'क्या हो रहा है? (विवरण लिखें)' : 'What is happening? (Optional notes)',
    captionPlaceholder:
      language === 'hi'
        ? 'उदा. सड़क पर मलबा आ गया है, पानी तेजी से बढ़ रहा है...'
        : 'e.g. Water rising rapidly near bridge, boulders on road...',
    phoneLabel: language === 'hi' ? 'मोबाइल नंबर (मदद और संपर्क के लिए)' : 'Mobile Phone (For rescue team callback)',
    phonePlaceholder: language === 'hi' ? '10 अंकों का फोन नंबर' : '10-digit mobile number',
    submitBtn: language === 'hi' ? 'तुरंत रिपोर्ट भेजें' : 'Send Report Now',
    submittingBtn: language === 'hi' ? 'भेजा जा रहा है...' : 'Sending Report...',
    successMsg:
      language === 'hi'
        ? 'धन्यवाद! आपकी रिपोर्ट प्राप्त हो गई है। आपकी सतर्कता से गाँव सुरक्षित रहेगा।'
        : 'Thank you! Your report was received. Your vigilance helps keep your community safe.',
    offlineNotice:
      language === 'hi'
        ? 'इंटरनेट बंद है। आपकी रिपोर्ट फोन में सुरक्षित है और नेटवर्क आते ही अपने आप पहुँच जाएगी।'
        : 'You are offline. Your report is saved locally and will send automatically when online.',
    viewPublicAdvisories: language === 'hi' ? 'गाँव के सुरक्षित आश्रय देखें' : 'View Safe Shelters & Routes',
    submitAnother: language === 'hi' ? 'एक और रिपोर्ट भेजें' : 'Submit Another Report',
    privacyNote:
      language === 'hi'
        ? '🔒 आपकी गोपनीयता सुरक्षित है: व्यक्तिगत जानकारी अपने आप हटा दी जाती है।'
        : '🔒 Privacy Protected: Personal device details are stripped automatically.',
  };

  // Check offline queue count on mount
  useEffect(() => {
    setQueuedCount(reportService.getQueuedOfflineReports().length);

    const handleOnline = () => {
      setIsOnline(true);
      // Auto-flush queued reports
      reportService.flushOfflineReports(() => {
        setQueuedCount(reportService.getQueuedOfflineReports().length);
      });
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Auto-fetch GPS on load
    fetchDeviceGps();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const fetchDeviceGps = () => {
    if (!navigator.geolocation) {
      setGpsError(language === 'hi' ? 'इस डिवाइस में GPS उपलब्ध नहीं है' : 'GPS not supported on this device');
      setManualLocationMode(true);
      return;
    }

    setGpsLoading(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLon(pos.coords.longitude);
        setAccuracy(Math.round(pos.coords.accuracy));
        setGpsLoading(false);
        setManualLocationMode(false);
      },
      (err) => {
        setGpsLoading(false);
        setGpsError(err.message || 'GPS permission denied');
        setManualLocationMode(true);
        // Fallback default: Bhatwari coords
        if (lat === null) {
          setLat(30.814);
          setLon(78.618);
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
    );
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size client-side
    const isPhoto = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');

    if (isPhoto && file.size > 20 * 1024 * 1024) {
      setErrorMessage(language === 'hi' ? 'फोटो 20MB से छोटी होनी चाहिए' : 'Photo must be under 20MB');
      return;
    }
    if (isVideo && file.size > 60 * 1024 * 1024) {
      setErrorMessage(language === 'hi' ? 'वीडियो 60MB से छोटा होना चाहिए' : 'Video must be under 60MB');
      return;
    }

    setErrorMessage(null);
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const removeFile = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!selectedFile) {
      setErrorMessage(
        language === 'hi' ? 'कृपया एक फोटो या वीडियो अपलोड करें' : 'Please capture or select a photo/video'
      );
      return;
    }

    if (lat === null || lon === null) {
      setErrorMessage(
        language === 'hi' ? 'कृपया GPS लोकेशन या पिन दर्ज करें' : 'Please provide location coordinates'
      );
      return;
    }

    setIsSubmitting(true);
    setUploadProgress(10);

    // If offline, save in localStorage
    if (!navigator.onLine) {
      try {
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64Data = reader.result as string;
          const queued: QueuedOfflineReport = {
            id: `OFFLINE_${Date.now()}`,
            latitude: lat,
            longitude: lon,
            accuracy_meters: accuracy || undefined,
            reported_flood: reportedFlood,
            caption: caption || undefined,
            reporter_phone: phone || undefined,
            fileName: selectedFile.name,
            fileType: selectedFile.type,
            fileDataUrl: base64Data,
            timestamp: Date.now(),
          };
          reportService.queueOfflineReport(queued);
          setQueuedCount(reportService.getQueuedOfflineReports().length);
          setIsSubmitting(false);
          setIsOfflineQueued(true);
          setIsSuccess(true);
        };
        reader.readAsDataURL(selectedFile);
        return;
      } catch (err: any) {
        setIsSubmitting(false);
        setErrorMessage(err.message || 'Failed to queue report offline');
        return;
      }
    }

    // Online submission
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('latitude', lat.toString());
      formData.append('longitude', lon.toString());
      if (accuracy) formData.append('accuracy_meters', accuracy.toString());
      formData.append('reported_flood', reportedFlood.toString());
      if (caption.trim()) formData.append('caption', caption.trim());
      if (phone.trim()) formData.append('reporter_phone', phone.trim());

      await reportService.submitCitizenReportMultipart(formData, (pct) => {
        setUploadProgress(Math.max(15, pct));
      });

      setUploadProgress(100);
      setIsSubmitting(false);
      setIsSuccess(true);
      setIsOfflineQueued(false);
      showSuccessToast(t.successMsg, 'Report Submitted');
    } catch (err: any) {
      setIsSubmitting(false);
      const errMsg = err.message || 'Submission error. Please retry.';
      setErrorMessage(errMsg);
      showErrorToast(errMsg, 'Submission Error');
    }
  };

  const resetForm = () => {
    removeFile();
    setCaption('');
    setPhone('');
    setIsSuccess(false);
    setIsOfflineQueued(false);
    setUploadProgress(0);
    fetchDeviceGps();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-orange-500 selection:text-white">
      {/* Top Mobile Bar */}
      <header className="bg-slate-900/90 border-b border-slate-800 px-4 py-3 sticky top-0 z-20 backdrop-blur flex items-center justify-between">
        <Link
          to="/citizen"
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{language === 'hi' ? 'वापस' : 'Back'}</span>
        </Link>

        <h1 className="text-sm font-bold text-slate-100 flex items-center gap-1.5 font-mono">
          <Camera className="w-4 h-4 text-orange-500" />
          <span>{t.title}</span>
        </h1>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors shadow-sm"
            title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            aria-label="Toggle Light and Dark Theme"
          >
            {isDark ? (
              <Sun className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-indigo-400" />
            )}
          </button>

          <button
            onClick={() => setLanguage(language === 'hi' ? 'en' : 'hi')}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-bold text-orange-400 border border-slate-700 transition-colors"
          >
            <Languages className="w-3.5 h-3.5" />
            <span>{language === 'hi' ? 'English' : 'हिन्दी'}</span>
          </button>
        </div>
      </header>

      {/* Network Alert Banner */}
      {!isOnline && (
        <div className="bg-amber-950/90 border-b border-amber-500/50 px-4 py-2 text-xs text-amber-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <WifiOff className="w-4 h-4 animate-pulse text-amber-400" />
            <span>{t.offlineNotice}</span>
          </div>
          {queuedCount > 0 && (
            <span className="bg-amber-500/20 px-2 py-0.5 rounded font-mono font-bold text-[10px]">
              {queuedCount} {language === 'hi' ? 'कतार में' : 'Queued'}
            </span>
          )}
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-lg mx-auto w-full p-4 space-y-4">
        {isSuccess ? (
          // Success State View
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center space-y-5 shadow-2xl animate-fade-in my-auto">
            <div className="w-16 h-16 rounded-full bg-emerald-950 border border-emerald-500/50 flex items-center justify-center mx-auto text-emerald-400 shadow-lg shadow-emerald-950">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div className="space-y-2">
              <h2 className="text-lg font-bold text-slate-100">
                {isOfflineQueued
                  ? language === 'hi'
                    ? 'रिपोर्ट फोन में सुरक्षित हो गई'
                    : 'Report Saved Locally'
                  : language === 'hi'
                  ? 'रिपोर्ट सफलता से प्राप्त हुई'
                  : 'Report Received!'}
              </h2>
              <p className="text-xs text-slate-300 leading-relaxed">
                {isOfflineQueued ? t.offlineNotice : t.successMsg}
              </p>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 text-left font-mono text-[11px] space-y-1.5 text-slate-400">
              <div className="flex justify-between">
                <span>{language === 'hi' ? 'स्थिति:' : 'Status:'}</span>
                <span className={reportedFlood ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
                  {reportedFlood
                    ? language === 'hi'
                      ? 'बाढ़ / भूस्खलन रिपोर्टेड'
                      : 'FLOOD / SLIDE REPORTED'
                    : language === 'hi'
                    ? 'सुरक्षित / कोई बाढ़ नहीं'
                    : 'SAFE / NO FLOOD'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>{language === 'hi' ? 'स्थान:' : 'Coordinates:'}</span>
                <span className="text-slate-200">
                  {lat?.toFixed(4)}°N, {lon?.toFixed(4)}°E
                </span>
              </div>
            </div>

            <div className="pt-2 flex flex-col gap-2.5">
              <button
                onClick={resetForm}
                className="w-full py-3 rounded-xl bg-orange-600 hover:bg-orange-500 text-white font-bold text-xs uppercase tracking-wider transition-colors shadow-lg shadow-orange-950"
              >
                {t.submitAnother}
              </button>
              <Link
                to="/citizen"
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors block text-center"
              >
                {t.viewPublicAdvisories}
              </Link>
            </div>
          </div>
        ) : (
          // Form View
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Step 1: Flood or No Flood Question */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2.5 shadow-md">
              <label className="block text-xs font-bold text-slate-200 font-mono flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-orange-400" />
                <span>{t.questionTitle}</span>
              </label>

              <div className="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => setReportedFlood(true)}
                  className={`py-3.5 px-3 rounded-xl border text-center transition-all font-bold text-xs flex flex-col items-center justify-center gap-1.5 ${
                    reportedFlood
                      ? 'bg-red-950/80 border-red-500 text-red-200 shadow-md shadow-red-950/50 scale-[1.02]'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <span className="text-lg">🌊</span>
                  <span>{t.yesFlood}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setReportedFlood(false)}
                  className={`py-3.5 px-3 rounded-xl border text-center transition-all font-bold text-xs flex flex-col items-center justify-center gap-1.5 ${
                    !reportedFlood
                      ? 'bg-emerald-950/80 border-emerald-500 text-emerald-200 shadow-md shadow-emerald-950/50 scale-[1.02]'
                      : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <span className="text-lg">✅</span>
                  <span>{t.noFlood}</span>
                </button>
              </div>
            </div>

            {/* Step 2: Photo or Video Upload */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3 shadow-md">
              <label className="block text-xs font-bold text-slate-200 font-mono flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Camera className="w-4 h-4 text-orange-400" />
                  <span>{t.photoVideoLabel}</span>
                </span>
                <span className="text-[10px] text-orange-400 font-normal">{language === 'hi' ? 'अनिवार्य' : 'Required'}</span>
              </label>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,video/*"
                capture="environment"
                onChange={handleFileChange}
                className="hidden"
              />

              {!previewUrl ? (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-slate-800 hover:border-orange-500/60 rounded-xl p-6 text-center cursor-pointer transition-colors bg-slate-950/40 hover:bg-slate-950/80 group space-y-2"
                >
                  <div className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 group-hover:border-orange-500/50 flex items-center justify-center mx-auto text-slate-400 group-hover:text-orange-400 transition-colors">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-200 block">{t.chooseFile}</span>
                    <span className="text-[10px] text-slate-500">{t.fileSizeHint}</span>
                  </div>
                </div>
              ) : (
                <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-black aspect-video flex items-center justify-center group">
                  {selectedFile?.type.startsWith('video/') ? (
                    <video src={previewUrl} controls className="max-h-full max-w-full" />
                  ) : (
                    <img src={previewUrl} alt="Preview" className="max-h-full max-w-full object-contain" />
                  )}

                  <button
                    type="button"
                    onClick={removeFile}
                    className="absolute top-2 right-2 bg-slate-900/90 text-red-400 p-1.5 rounded-full border border-slate-700 hover:bg-red-950 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>

                  <div className="absolute bottom-2 left-2 bg-slate-950/80 text-[10px] text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-800 backdrop-blur">
                    {selectedFile?.name} ({(selectedFile ? selectedFile.size / 1024 / 1024 : 0).toFixed(1)} MB)
                  </div>
                </div>
              )}
            </div>

            {/* Step 3: Location / GPS */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2.5 shadow-md">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-200 font-mono flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-orange-400" />
                  <span>{t.gpsTitle}</span>
                </label>
                <button
                  type="button"
                  onClick={fetchDeviceGps}
                  disabled={gpsLoading}
                  className="text-[11px] text-orange-400 hover:text-orange-300 flex items-center gap-1 font-mono"
                >
                  <RefreshCw className={`w-3 h-3 ${gpsLoading ? 'animate-spin' : ''}`} />
                  <span>{language === 'hi' ? 'रीफ्रेश' : 'Refresh GPS'}</span>
                </button>
              </div>

              {gpsLoading ? (
                <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-orange-400" />
                  <span>{t.gpsFetching}</span>
                </div>
              ) : lat !== null && lon !== null && !manualLocationMode ? (
                <div className="p-3 bg-emerald-950/30 border border-emerald-500/40 rounded-xl flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-[11px] font-bold text-emerald-400 block">{t.gpsSuccess}</span>
                    <span className="text-xs text-slate-200 font-mono">
                      {lat.toFixed(5)}°N, {lon.toFixed(5)}°E
                    </span>
                    {accuracy && (
                      <span className="text-[10px] text-slate-400 block">
                        ±{accuracy}m {language === 'hi' ? 'सटीकता' : 'accuracy'}
                      </span>
                    )}
                  </div>
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                </div>
              ) : (
                <div className="space-y-2">
                  {gpsError && (
                    <div className="p-2.5 bg-amber-950/40 border border-amber-500/40 rounded-lg text-[11px] text-amber-300 flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>{gpsError}. {t.gpsFallback}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-[10px] text-slate-400 font-mono block mb-1">Latitude</span>
                      <input
                        type="number"
                        step="any"
                        value={lat ?? ''}
                        onChange={(e) => setLat(parseFloat(e.target.value) || 0)}
                        placeholder="30.8140"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs font-mono text-slate-100"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 font-mono block mb-1">Longitude</span>
                      <input
                        type="number"
                        step="any"
                        value={lon ?? ''}
                        onChange={(e) => setLon(parseFloat(e.target.value) || 0)}
                        placeholder="78.6180"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs font-mono text-slate-100"
                      />
                    </div>
                  </div>

                  {/* Preset Quick Select for Pilot Villages */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <span className="text-[10px] text-slate-500 block w-full">Quick Preset:</span>
                    {[
                      { name: 'Bhatwari', lat: 30.814, lon: 78.618 },
                      { name: 'Harsil', lat: 31.0367, lon: 78.7378 },
                      { name: 'Maneri', lat: 30.765, lon: 78.532 },
                      { name: 'Dharali', lat: 31.045, lon: 78.752 },
                    ].map((p) => (
                      <button
                        key={p.name}
                        type="button"
                        onClick={() => {
                          setLat(p.lat);
                          setLon(p.lon);
                          setAccuracy(20);
                        }}
                        className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-300 font-mono"
                      >
                        {p.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Step 4: Optional Caption and Phone */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3 shadow-md">
              <div>
                <label className="block text-xs font-bold text-slate-200 font-mono mb-1 flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-orange-400" />
                  <span>{t.captionLabel}</span>
                </label>
                <textarea
                  rows={2}
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  placeholder={t.captionPlaceholder}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-orange-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-200 font-mono mb-1 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-orange-400" />
                  <span>{t.phoneLabel}</span>
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder={t.phonePlaceholder}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-100 placeholder-slate-600 font-mono focus:outline-none focus:border-orange-500 transition-colors"
                />
              </div>
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="p-3 bg-red-950/80 border border-red-500/50 rounded-xl text-xs text-red-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Progress Bar */}
            {isSubmitting && (
              <div className="space-y-1">
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-orange-500 h-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>{t.submittingBtn}</span>
                  <span>{uploadProgress}%</span>
                </div>
              </div>
            )}

            {/* Sticky Submit Button for effortless one-handed thumb access */}
            <div className="sticky bottom-3 z-30 pt-2 pb-1 bg-gradient-to-t from-slate-50 via-slate-50/95 to-transparent dark:from-slate-950 dark:via-slate-950/95">
              <button
                type="submit"
                disabled={isSubmitting}
                className={`w-full py-3.5 min-h-[50px] rounded-2xl font-bold text-sm uppercase tracking-wider transition-all shadow-xl flex items-center justify-center gap-2 focus-visible:ring-2 focus-visible:ring-orange-500 ${
                  isSubmitting
                    ? 'bg-slate-300 dark:bg-slate-800 text-slate-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white shadow-orange-950/20 dark:shadow-orange-950/60 active:scale-[0.98]'
                }`}
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>{t.submittingBtn}</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    <span>{t.submitBtn}</span>
                  </>
                )}
              </button>
              <p className="text-[10px] text-center text-slate-500 dark:text-slate-400 mt-2">
                {t.privacyNote}
              </p>
            </div>
          </form>
        )}
      </main>
    </div>
  );
};
