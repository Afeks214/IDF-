import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { usePWA } from '../pwa/PWAProvider';

interface MobileNavigationProps {
  className?: string;
}

const MobileNavigation: React.FC<MobileNavigationProps> = ({ className = '' }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isMobile } = usePWA();

  if (!isMobile) {
    return null;
  }

  const navigationItems = [
    {
      path: '/dashboard',
      label: 'דשבורד',
      icon: '📊',
      ariaLabel: 'דשבורד ראשי'
    },
    {
      path: '/buildings',
      label: 'בניינים',
      icon: '🏢',
      ariaLabel: 'רשימת בניינים'
    },
    {
      path: '/tests',
      label: 'בדיקות',
      icon: '🔍',
      ariaLabel: 'בדיקות ובקרה'
    },
    {
      path: '/reports',
      label: 'דוחות',
      icon: '📋',
      ariaLabel: 'דוחות ונתונים'
    }
  ];

  const handleNavigate = (path: string) => {
    navigate(path);
  };

  return (
    <nav className={`mobile-nav ${className}`} role="navigation" aria-label="ניווט מהיר">
      <div className="flex">
        {navigationItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <button
              key={item.path}
              onClick={() => handleNavigate(item.path)}
              className={`mobile-nav-item ${isActive ? 'active' : ''}`}
              aria-label={item.ariaLabel}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="text-lg mb-1" role="img" aria-hidden="true">
                {item.icon}
              </span>
              <span className="text-xs font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

export default MobileNavigation;