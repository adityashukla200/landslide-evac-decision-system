import React, { createContext, useContext, useState, useCallback } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Info,
  XCircle,
  X,
} from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
}

interface ToastContextType {
  toasts: ToastItem[];
  showToast: (message: string, type?: ToastType, title?: string, duration?: number) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'info', title?: string, duration: number = 4000) => {
      const id = `toast_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      const newToast: ToastItem = { id, type, title, message, duration };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  const success = useCallback(
    (message: string, title?: string) => showToast(message, 'success', title),
    [showToast]
  );
  const error = useCallback(
    (message: string, title?: string) => showToast(message, 'error', title, 5000),
    [showToast]
  );
  const warning = useCallback(
    (message: string, title?: string) => showToast(message, 'warning', title),
    [showToast]
  );
  const info = useCallback(
    (message: string, title?: string) => showToast(message, 'info', title),
    [showToast]
  );

  return (
    <ToastContext.Provider
      value={{
        toasts,
        showToast,
        success,
        error,
        warning,
        info,
        removeToast,
      }}
    >
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

// Internal Toast Container
const ToastContainer: React.FC<{
  toasts: ToastItem[];
  onRemove: (id: string) => void;
}> = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 sm:top-4 sm:bottom-auto z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-3"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const icons = {
          success: <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />,
          error: <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />,
          warning: <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />,
          info: <Info className="w-5 h-5 text-sky-500 shrink-0 mt-0.5" />,
        };

        const bgStyles = {
          success:
            'bg-white dark:bg-slate-900 border-emerald-300 dark:border-emerald-600/50 text-slate-800 dark:text-slate-100 shadow-emerald-950/10',
          error:
            'bg-white dark:bg-slate-900 border-red-300 dark:border-red-600/50 text-slate-800 dark:text-slate-100 shadow-red-950/10',
          warning:
            'bg-white dark:bg-slate-900 border-amber-300 dark:border-amber-600/50 text-slate-800 dark:text-slate-100 shadow-amber-950/10',
          info:
            'bg-white dark:bg-slate-900 border-sky-300 dark:border-sky-600/50 text-slate-800 dark:text-slate-100 shadow-sky-950/10',
        };

        return (
          <div
            key={toast.id}
            role="alert"
            aria-live="polite"
            className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-xl transition-all duration-300 animate-slide-in-right text-xs font-sans ${bgStyles[toast.type]}`}
          >
            {icons[toast.type]}
            <div className="flex-1 space-y-0.5">
              {toast.title && (
                <div className="font-bold font-mono tracking-wide text-xs">
                  {toast.title}
                </div>
              )}
              <div className="text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">
                {toast.message}
              </div>
            </div>
            <button
              onClick={() => onRemove(toast.id)}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors focus-visible:ring-2 focus-visible:ring-orange-500"
              aria-label="Dismiss notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
