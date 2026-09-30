import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserRole, OfficerProfile } from '../types';
import { authService } from '../services/authService';

interface AuthContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  userName: string;
  badgeNumber: string;
  isOfficer: boolean;
  isAuthenticated: boolean;
  officer: OfficerProfile | null;
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  isLoginModalOpen: boolean;
  openLoginModal: (reason?: string) => void;
  closeLoginModal: () => void;
  loginPromptReason: string | null;
  getValidAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [officer, setOfficer] = useState<OfficerProfile | null>(null);
  const [role, setRoleState] = useState<UserRole>('CITIZEN');
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [loginPromptReason, setLoginPromptReason] = useState<string | null>(null);

  // Silently check for existing valid session on mount
  useEffect(() => {
    let isMounted = true;
    const checkSession = async () => {
      const token = await authService.getValidToken();
      if (token && isMounted) {
        const me = await authService.getMe();
        if (me && isMounted) {
          setOfficer(me);
          if (me.role === 'admin') {
            setRoleState('DISTRICT_OFFICER');
          } else {
            setRoleState('NDRF_COMMANDER');
          }
        }
      }
    };
    checkSession();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const data = await authService.login(username, password);
      setOfficer(data.officer);
      if (data.officer.role === 'admin') {
        setRoleState('DISTRICT_OFFICER');
      } else {
        setRoleState('NDRF_COMMANDER');
      }
      setIsLoginModalOpen(false);
      setLoginPromptReason(null);
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || 'Login failed.' };
    }
  };

  const logout = async () => {
    await authService.logout();
    setOfficer(null);
    setRoleState('CITIZEN');
  };

  const openLoginModal = (reason?: string) => {
    setLoginPromptReason(reason || null);
    setIsLoginModalOpen(true);
  };

  const closeLoginModal = () => {
    setIsLoginModalOpen(false);
    setLoginPromptReason(null);
  };

  const isAuthenticated = !!officer;
  const isOfficer = isAuthenticated && (officer?.role === 'officer' || officer?.role === 'admin');

  const setRole = (r: UserRole) => {
    setRoleState(r);
    if ((r === 'DISTRICT_OFFICER' || r === 'NDRF_COMMANDER') && !isAuthenticated) {
      openLoginModal('Officer login required to enter operational command mode.');
    }
  };

  const userName = officer
    ? officer.name
    : role === 'CITIZEN'
    ? 'Resident / Pilgrim User'
    : role === 'FIELD_VOLUNTEER'
    ? 'Deepak Semwal (Aapda Mitra)'
    : 'Guest';

  const badgeNumber = officer
    ? `${officer.district.toUpperCase()}-${officer.role.toUpperCase()}`
    : 'CITIZEN-APP';

  return (
    <AuthContext.Provider
      value={{
        role,
        setRole,
        userName,
        badgeNumber,
        isOfficer,
        isAuthenticated,
        officer,
        login,
        logout,
        isLoginModalOpen,
        openLoginModal,
        closeLoginModal,
        loginPromptReason,
        getValidAccessToken: () => authService.getValidToken(),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
