import React, { createContext, useContext, useState } from 'react';
import { UserRole } from '../types';

interface AuthContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  userName: string;
  badgeNumber: string;
  isOfficer: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRole] = useState<UserRole>('DISTRICT_OFFICER');

  const getUserDetails = (r: UserRole) => {
    switch (r) {
      case 'DISTRICT_OFFICER':
        return { name: 'Dr. Meenakshi Sundaram (IAS)', badge: 'DEOC-UTK-01' };
      case 'NDRF_COMMANDER':
        return { name: 'Cmdt. R.K. Bhardwaj', badge: 'NDRF-15-BN' };
      case 'FIELD_VOLUNTEER':
        return { name: 'Deepak Semwal (Aapda Mitra)', badge: 'VOL-BHT-04' };
      case 'CITIZEN':
      default:
        return { name: 'Resident / Pilgrim User', badge: 'CITIZEN-APP' };
    }
  };

  const details = getUserDetails(role);
  const isOfficer = role === 'DISTRICT_OFFICER' || role === 'NDRF_COMMANDER';

  return (
    <AuthContext.Provider
      value={{
        role,
        setRole,
        userName: details.name,
        badgeNumber: details.badge,
        isOfficer,
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
