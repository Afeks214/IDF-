import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ReadinessData {
  name: string;
  value: number;
  color: string;
  total?: number;
}

export interface BuildingData {
  id: string;
  name: string;
  code: string;
  totalFloors: number;
  overallReadiness: number;
  manager: string;
  lastUpdate: string;
  floors: FloorData[];
}

export interface FloorData {
  id: string;
  name: string;
  level: number;
  totalRooms: number;
  readinessScore: number;
  lastInspection: string;
}

export interface DashboardStats {
  totalBuildings: number;
  totalTests: number;
  pendingTests: number;
  completedTests: number;
  totalRecords: number;
  lastUpdateTime: string;
}

export interface ReadinessCategories {
  buildingReadiness: ReadinessData[];
  generalReadiness: ReadinessData[];
  engineeringReadiness: ReadinessData[];
  operationalReadiness: ReadinessData[];
}

class DashboardApiService {
  private axios = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  constructor() {
    // Add request interceptor for auth token
    this.axios.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('authToken');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Get dashboard statistics
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const response = await this.axios.get('/api/v1/dashboard/stats');
      return response.data;
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      // Return mock data as fallback
      return {
        totalBuildings: 45,
        totalTests: 234,
        pendingTests: 12,
        completedTests: 198,
        totalRecords: 494,
        lastUpdateTime: new Date().toISOString(),
      };
    }
  }

  // Get readiness data for all 4 categories
  async getReadinessData(): Promise<ReadinessCategories> {
    try {
      const response = await this.axios.get('/api/v1/dashboard/readiness');
      return response.data;
    } catch (error) {
      console.error('Error fetching readiness data:', error);
      // Return mock data as fallback
      return this.getMockReadinessData();
    }
  }

  // Get building hierarchy data
  async getBuildingHierarchy(): Promise<BuildingData[]> {
    try {
      const response = await this.axios.get('/api/v1/dashboard/buildings');
      return response.data;
    } catch (error) {
      console.error('Error fetching building hierarchy:', error);
      // Return mock data as fallback
      return this.getMockBuildingData();
    }
  }

  // Get real-time updates
  async getRealtimeUpdates(): Promise<any> {
    try {
      const response = await this.axios.get('/api/v1/dashboard/updates');
      return response.data;
    } catch (error) {
      console.error('Error fetching realtime updates:', error);
      return null;
    }
  }

  // Mock data methods for development/fallback
  private getMockReadinessData(): ReadinessCategories {
    return {
      buildingReadiness: [
        { name: 'מעולה (90%+)', value: 12, color: '#4caf50' },
        { name: 'טוב (70-89%)', value: 18, color: '#ff9800' },
        { name: 'דורש שיפור (<70%)', value: 15, color: '#f44336' },
      ],
      generalReadiness: [
        { name: 'כשיר לחלוטין', value: 25, color: '#4caf50' },
        { name: 'כשיר עם הערות', value: 15, color: '#ff9800' },
        { name: 'לא כשיר', value: 5, color: '#f44336' },
      ],
      engineeringReadiness: [
        { name: 'מבנה תקין', value: 30, color: '#2196f3' },
        { name: 'דרוש תיקון קל', value: 10, color: '#ff9800' },
        { name: 'דרוש תיקון דחוף', value: 5, color: '#f44336' },
      ],
      operationalReadiness: [
        { name: 'מוכן לפעילות', value: 28, color: '#9c27b0' },
        { name: 'דרוש השלמות', value: 12, color: '#ff9800' },
        { name: 'לא מוכן', value: 5, color: '#f44336' },
      ],
    };
  }

  private getMockBuildingData(): BuildingData[] {
    return [
      {
        id: '1',
        name: 'מבנה מטה',
        code: 'MTA-001',
        totalFloors: 5,
        overallReadiness: 92,
        manager: 'רס"ן כהן',
        lastUpdate: '2025-07-18',
        floors: [
          {
            id: '1-1',
            name: 'קומת קרקע',
            level: 0,
            totalRooms: 25,
            readinessScore: 95,
            lastInspection: '2025-07-15',
          },
          {
            id: '1-2',
            name: 'קומה ראשונה',
            level: 1,
            totalRooms: 20,
            readinessScore: 88,
            lastInspection: '2025-07-14',
          },
          {
            id: '1-3',
            name: 'קומה שנייה',
            level: 2,
            totalRooms: 18,
            readinessScore: 90,
            lastInspection: '2025-07-13',
          },
        ],
      },
      {
        id: '2',
        name: 'מבנה חיל הקשר',
        code: 'COM-002',
        totalFloors: 3,
        overallReadiness: 76,
        manager: 'רס"ן לוי',
        lastUpdate: '2025-07-17',
        floors: [
          {
            id: '2-1',
            name: 'קומת קרקע',
            level: 0,
            totalRooms: 15,
            readinessScore: 82,
            lastInspection: '2025-07-16',
          },
          {
            id: '2-2',
            name: 'קומה ראשונה',
            level: 1,
            totalRooms: 12,
            readinessScore: 70,
            lastInspection: '2025-07-15',
          },
        ],
      },
      {
        id: '3',
        name: 'מבנה לוגיסטיקה',
        code: 'LOG-003',
        totalFloors: 4,
        overallReadiness: 85,
        manager: 'רס"ן ברק',
        lastUpdate: '2025-07-18',
        floors: [
          {
            id: '3-1',
            name: 'קומת קרקע - מחסנים',
            level: 0,
            totalRooms: 8,
            readinessScore: 88,
            lastInspection: '2025-07-17',
          },
          {
            id: '3-2',
            name: 'קומה ראשונה - משרדים',
            level: 1,
            totalRooms: 12,
            readinessScore: 82,
            lastInspection: '2025-07-16',
          },
        ],
      },
    ];
  }
}

export const dashboardApi = new DashboardApiService();
export default dashboardApi;