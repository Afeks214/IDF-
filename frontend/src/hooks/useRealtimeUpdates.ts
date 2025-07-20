import { useEffect, useRef, useState } from 'react';
import { dashboardApi } from '../services/dashboardApi';

interface RealtimeUpdateOptions {
  enabled?: boolean;
  interval?: number; // milliseconds
  onUpdate?: (data: any) => void;
  onError?: (error: Error) => void;
}

export const useRealtimeUpdates = (options: RealtimeUpdateOptions = {}) => {
  const {
    enabled = true,
    interval = 30000, // 30 seconds
    onUpdate,
    onError,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const startUpdates = () => {
    if (!enabled) return;

    setIsConnected(true);
    setError(null);

    // Initial fetch
    fetchUpdate();

    // Set up interval for periodic updates
    intervalRef.current = setInterval(fetchUpdate, interval);
  };

  const stopUpdates = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsConnected(false);
  };

  const fetchUpdate = async () => {
    try {
      const updateData = await dashboardApi.getRealtimeUpdates();
      
      if (updateData) {
        setLastUpdate(new Date());
        setError(null);
        
        if (onUpdate) {
          onUpdate(updateData);
        }
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Real-time update failed');
      setError(error);
      
      if (onError) {
        onError(error);
      }
      
      console.error('Real-time update error:', error);
    }
  };

  const forceUpdate = () => {
    fetchUpdate();
  };

  // Start updates when component mounts or enabled changes
  useEffect(() => {
    if (enabled) {
      startUpdates();
    } else {
      stopUpdates();
    }

    // Cleanup on unmount
    return () => {
      stopUpdates();
    };
  }, [enabled, interval]);

  // Handle visibility change (pause updates when tab is not active)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopUpdates();
      } else if (enabled) {
        startUpdates();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled]);

  return {
    isConnected,
    lastUpdate,
    error,
    forceUpdate,
    startUpdates,
    stopUpdates,
  };
};

export default useRealtimeUpdates;