import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Shield,
  Lock,
  Mail,
  AlertCircle,
  CheckCircle,
  Eye,
  EyeOff,
  UserCheck,
  Building2,
} from 'lucide-react';

export const OfficerLoginModal: React.FC = () => {
  const { isLoginModalOpen, closeLoginModal, login, loginPromptReason } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  if (!isLoginModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMessage('Please enter both official email/phone and password.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    const res = await login(username.trim(), password);
    setLoading(false);

    if (res.success) {
      navigate('/');
    } else {
      setErrorMessage(res.error || 'Authentication failed. Please verify credentials.');
    }
  };

  const handleFillDemo = (demoUser: string, demoPass: string) => {
    setUsername(demoUser);
    setPassword(demoPass);
    setErrorMessage(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden font-mono text-xs">
        {/* Top Header */}
        <div className="p-4 bg-slate-950/90 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-orange-600/20 border border-orange-500/40 flex items-center justify-center text-orange-400">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 tracking-wide">
                DEOC OFFICER LOGIN
              </h3>
              <p className="text-[10px] text-slate-400">
                Uttarkashi Disaster Emergency Operations Center
              </p>
            </div>
          </div>
          <button
            onClick={closeLoginModal}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Reason Banner if triggered from gated action */}
        {loginPromptReason && (
          <div className="bg-amber-950/60 border-b border-amber-800/60 p-2.5 px-4 flex items-center gap-2 text-amber-300 text-[11px]">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{loginPromptReason}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Error Banner */}
          {errorMessage && (
            <div className="p-2.5 rounded-lg bg-red-950/80 border border-red-800/80 text-red-300 text-[11px] flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Username / Email Field */}
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
              Official Email or Phone Number
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. ddmo.uttarkashi@uk.gov.in"
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition-all text-xs"
                autoFocus
              />
            </div>
          </div>

          {/* Password Field */}
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full pl-9 pr-10 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition-all text-xs"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Quick Demo Credentials */}
          <div className="pt-1">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 font-bold flex items-center gap-1">
              <span>Quick Demo Accounts (Uttarkashi Pilot):</span>
            </div>
            <div className="grid grid-cols-1 gap-1.5">
              <button
                type="button"
                onClick={() => handleFillDemo('ddmo.uttarkashi@uk.gov.in', 'Uttarkashi@2026')}
                className="w-full text-left px-2.5 py-1.5 rounded bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800 text-slate-300 hover:text-white transition-colors flex items-center justify-between text-[11px]"
              >
                <span className="font-semibold text-orange-400">🛡️ District Officer (Admin)</span>
                <span className="text-[10px] text-slate-500">ddmo.uttarkashi</span>
              </button>
              <button
                type="button"
                onClick={() => handleFillDemo('ndrf.uttarkashi@gov.in', 'NDRF#Rescue2026')}
                className="w-full text-left px-2.5 py-1.5 rounded bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800 text-slate-300 hover:text-white transition-colors flex items-center justify-between text-[11px]"
              >
                <span className="font-semibold text-emerald-400">🦺 NDRF Commander (Officer)</span>
                <span className="text-[10px] text-slate-500">ndrf.uttarkashi</span>
              </button>
              <button
                type="button"
                onClick={() => handleFillDemo('bdo.bhatwari@uk.gov.in', 'Bhatwari@2026')}
                className="w-full text-left px-2.5 py-1.5 rounded bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800 text-slate-300 hover:text-white transition-colors flex items-center justify-between text-[11px]"
              >
                <span className="font-semibold text-sky-400">🏛️ BDO Bhatwari (Officer)</span>
                <span className="text-[10px] text-slate-500">bdo.bhatwari</span>
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-orange-600 hover:bg-orange-500 disabled:bg-slate-800 text-white font-bold rounded-lg shadow-lg shadow-orange-950/50 transition-all flex items-center justify-center gap-2 active:scale-98"
          >
            {loading ? (
              <span className="inline-block w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>
            ) : (
              <>
                <UserCheck className="w-4 h-4" />
                <span>AUTHENTICATE & ENTER COMMAND CENTER</span>
              </>
            )}
          </button>

          {/* Footer note */}
          <p className="text-[9px] text-slate-500 text-center leading-normal pt-1">
            Protected government early warning portal. Authentication requests are rate-limited and logged.
          </p>
        </form>
      </div>
    </div>
  );
};
