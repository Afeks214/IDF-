import React, { createContext, useContext, useEffect } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { CacheProvider } from '@emotion/react';
import createCache from '@emotion/cache';
import { prefixer } from 'stylis';
import rtlPlugin from 'stylis-plugin-rtl';
import rtlTheme from '../../theme';

// Create RTL cache
const cacheRtl = createCache({
  key: 'muirtl',
  stylisPlugins: [prefixer, rtlPlugin],
});

// Create LTR cache for fallback
const cacheLtr = createCache({
  key: 'muiltr',
});

interface RTLContextType {
  direction: 'rtl' | 'ltr';
  toggleDirection: () => void;
}

const RTLContext = createContext<RTLContextType | undefined>(undefined);

export const useRTL = () => {
  const context = useContext(RTLContext);
  if (context === undefined) {
    throw new Error('useRTL must be used within an RTLProvider');
  }
  return context;
};

interface RTLProviderProps {
  children: React.ReactNode;
  defaultDirection?: 'rtl' | 'ltr';
}

export const RTLProvider: React.FC<RTLProviderProps> = ({
  children,
  defaultDirection = 'rtl',
}) => {
  const [direction, setDirection] = React.useState<'rtl' | 'ltr'>(defaultDirection);

  const toggleDirection = () => {
    setDirection(prev => prev === 'rtl' ? 'ltr' : 'rtl');
  };

  // Update document direction
  useEffect(() => {
    document.dir = direction;
    document.documentElement.lang = direction === 'rtl' ? 'he' : 'en';
  }, [direction]);

  const cache = direction === 'rtl' ? cacheRtl : cacheLtr;
  const theme = { ...rtlTheme, direction };

  return (
    <RTLContext.Provider value={{ direction, toggleDirection }}>
      <CacheProvider value={cache}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          {children}
        </ThemeProvider>
      </CacheProvider>
    </RTLContext.Provider>
  );
};

export default RTLProvider;