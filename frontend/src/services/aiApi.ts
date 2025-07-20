/**
 * AI Integration API service for GrandModel integration
 */

interface AIInsightRequest {
  building_ids: string[];
  include_predictions?: boolean;
  include_synergies?: boolean;
  include_recommendations?: boolean;
}

interface AIInsightResponse {
  insights: {
    total_buildings: number;
    insights: Array<{
      building_id: string;
      building_name: string;
      current_readiness: {
        readiness_score: number;
        metrics: {
          completion_rate: number;
          defect_rate: number;
          schedule_adherence: number;
          regulatory_compliance: number;
          contractor_coordination: number;
        };
        signals: any[];
      };
      predictions: {
        current_score: number;
        predicted_7_day: number;
        predicted_30_day: number;
        trend_direction: number;
        confidence: number;
        factors: any;
      };
      recommendations: Array<{
        recommendation_type: string;
        priority: string;
        title: string;
        description: string;
        expected_impact: number;
        confidence: number;
        actions: string[];
        deadline: string | null;
      }>;
    }>;
  };
  synergies: {
    total_buildings_analyzed: number;
    synergies_detected: number;
    synergies: Array<{
      building_id: string;
      synergy_type: string;
      direction: number;
      confidence: number;
      signals: any[];
      completion_time: string;
      readiness_context: any;
    }>;
  };
  timestamp: string;
  ai_system_status: {
    grandmodel_available: boolean;
    synergy_detection_enabled: boolean;
    predictive_analytics_enabled: boolean;
  };
}

interface AISystemStatus {
  grandmodel_integration: {
    available: boolean;
    synergy_detector_initialized: boolean;
    version: string;
  };
  predictive_analytics: {
    enabled: boolean;
    version: string;
  };
  marl_coordination: {
    enabled: boolean;
    status: string;
  };
  timestamp: string;
}

interface SynergyDetectionRequest {
  building_ids: string[];
  time_window_hours?: number;
}

interface SynergyDetectionResponse {
  total_buildings_analyzed: number;
  synergies_detected: number;
  synergies: Array<{
    building_id: string;
    synergy_type: string;
    direction: number;
    confidence: number;
    signals: any[];
    completion_time: string;
    readiness_context: any;
  }>;
  timestamp: string;
}

interface PredictiveAnalyticsRequest {
  building_ids: string[];
  prediction_horizon_days?: number;
}

interface PredictiveAnalyticsResponse {
  total_buildings: number;
  insights: Array<{
    building_id: string;
    building_name: string;
    current_readiness: any;
    predictions: any;
    recommendations: any[];
    timestamp: string;
  }>;
  timestamp: string;
}

interface BuildingRecommendation {
  building_id: string;
  recommendations: Array<{
    building_id: string;
    recommendation_type: string;
    priority: string;
    title: string;
    description: string;
    expected_impact: number;
    confidence: number;
    actions: string[];
    deadline: string | null;
    metadata: any;
  }>;
  timestamp: string;
}

interface BuildingReadinessAnalysis {
  total_buildings: number;
  analyses: Array<{
    building_id: string;
    building_name?: string;
    total_inspections: number;
    readiness_score: number;
    metrics: {
      completion_rate: number;
      defect_rate: number;
      schedule_adherence: number;
      regulatory_compliance: number;
      contractor_coordination: number;
    };
    signals: any[];
    timestamp: string;
  }>;
  timestamp: string;
}

interface MarlCoordinationStatus {
  marl_coordination: {
    enabled: boolean;
    status: string;
  };
  synergy_detection: {
    enabled: boolean;
    patterns_supported: string[];
  };
  signal_types: string[];
  timestamp: string;
}

interface DecisionOptimization {
  total_buildings: number;
  optimizations: Array<{
    building_id: string;
    current_readiness: number;
    predicted_readiness: number;
    optimization_potential: number;
    priority_actions: string[];
    marl_coordination_score: number;
  }>;
  marl_coordination_active: boolean;
  timestamp: string;
}

const API_BASE_URL = '/api/v1/ai';

const getAuthHeader = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
};

export const aiApi = {
  // Get AI system status
  getSystemStatus: async (): Promise<AISystemStatus> => {
    const response = await fetch(`${API_BASE_URL}/status`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<AISystemStatus>(response);
  },

  // Get comprehensive AI insights for buildings
  getBuildingInsights: async (request: AIInsightRequest): Promise<AIInsightResponse> => {
    const response = await fetch(`${API_BASE_URL}/insights`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(request),
    });
    return handleResponse<AIInsightResponse>(response);
  },

  // Detect synergy patterns
  detectSynergies: async (request: SynergyDetectionRequest): Promise<SynergyDetectionResponse> => {
    const response = await fetch(`${API_BASE_URL}/synergy-detection`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(request),
    });
    return handleResponse<SynergyDetectionResponse>(response);
  },

  // Generate predictive analytics
  generatePredictiveAnalytics: async (request: PredictiveAnalyticsRequest): Promise<PredictiveAnalyticsResponse> => {
    const response = await fetch(`${API_BASE_URL}/predictive-analytics`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(request),
    });
    return handleResponse<PredictiveAnalyticsResponse>(response);
  },

  // Get building-specific recommendations
  getBuildingRecommendations: async (buildingId: string): Promise<BuildingRecommendation> => {
    const response = await fetch(`${API_BASE_URL}/recommendations/${buildingId}`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<BuildingRecommendation>(response);
  },

  // Get building readiness analysis
  getBuildingReadinessAnalysis: async (buildingIds: string[]): Promise<BuildingReadinessAnalysis> => {
    const params = new URLSearchParams();
    buildingIds.forEach(id => params.append('building_ids', id));
    
    const response = await fetch(`${API_BASE_URL}/buildings/readiness-analysis?${params}`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<BuildingReadinessAnalysis>(response);
  },

  // Get MARL coordination status
  getMarlCoordinationStatus: async (): Promise<MarlCoordinationStatus> => {
    const response = await fetch(`${API_BASE_URL}/marl/coordination-status`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return handleResponse<MarlCoordinationStatus>(response);
  },

  // Optimize building decisions using MARL
  optimizeBuildingDecisions: async (request: AIInsightRequest): Promise<DecisionOptimization> => {
    const response = await fetch(`${API_BASE_URL}/marl/optimize-decisions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(request),
    });
    return handleResponse<DecisionOptimization>(response);
  },
};

export type {
  AIInsightRequest,
  AIInsightResponse,
  AISystemStatus,
  SynergyDetectionRequest,
  SynergyDetectionResponse,
  PredictiveAnalyticsRequest,
  PredictiveAnalyticsResponse,
  BuildingRecommendation,
  BuildingReadinessAnalysis,
  MarlCoordinationStatus,
  DecisionOptimization,
};