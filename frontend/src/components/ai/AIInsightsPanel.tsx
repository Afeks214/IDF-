import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon,
  Analytics as AnalyticsIcon,
  Hub as HubIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

interface AIInsight {
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
}

interface SynergyData {
  building_id: string;
  synergy_type: string;
  direction: number;
  confidence: number;
  signals: any[];
  completion_time: string;
  readiness_context: any;
}

interface AIInsightsPanelProps {
  buildingIds: string[];
  onRefresh?: () => void;
}

export const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({ buildingIds, onRefresh }) => {
  const { t } = useTranslation();
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [synergies, setSynergies] = useState<SynergyData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiSystemStatus, setAiSystemStatus] = useState<any>(null);

  const fetchAIInsights = async () => {
    if (buildingIds.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/ai/insights', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          building_ids: buildingIds,
          include_predictions: true,
          include_synergies: true,
          include_recommendations: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch AI insights');
      }

      const data = await response.json();
      setInsights(data.insights?.insights || []);
      setSynergies(data.synergies?.synergies || []);
      setAiSystemStatus(data.ai_system_status || {});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAIInsights();
  }, [buildingIds]);

  const getReadinessColor = (score: number) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  const getTrendIcon = (direction: number) => {
    if (direction > 0) return <TrendingUpIcon color="success" />;
    if (direction < 0) return <WarningIcon color="error" />;
    return <CheckCircleIcon color="primary" />;
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatScore = (score: number) => `${Math.round(score * 100)}%`;

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading AI insights...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
        <Button onClick={fetchAIInsights} sx={{ ml: 2 }}>
          Retry
        </Button>
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <PsychologyIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h5" component="h2">
            AI Insights & Predictions
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {aiSystemStatus && (
            <Chip
              icon={<HubIcon />}
              label={aiSystemStatus.grandmodel_available ? 'GrandModel Active' : 'GrandModel Offline'}
              color={aiSystemStatus.grandmodel_available ? 'success' : 'error'}
              sx={{ mr: 1 }}
            />
          )}
          <Tooltip title="Refresh AI Analysis">
            <IconButton onClick={fetchAIInsights} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Synergy Detection Results */}
      {synergies.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <AnalyticsIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Synergy Detection Results
            </Typography>
            <Grid container spacing={2}>
              {synergies.map((synergy, index) => (
                <Grid item xs={12} md={6} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="subtitle1" fontWeight="bold">
                          Building {synergy.building_id}
                        </Typography>
                        <Chip
                          label={synergy.synergy_type}
                          color={synergy.direction > 0 ? 'success' : 'error'}
                          size="small"
                        />
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                          Direction: {synergy.direction > 0 ? 'Improving' : 'Declining'}
                        </Typography>
                        <Box sx={{ ml: 'auto' }}>
                          <Typography variant="body2" color="text.secondary">
                            Confidence: {formatScore(synergy.confidence)}
                          </Typography>
                        </Box>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        Signals: {synergy.signals.length} detected
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Building Insights */}
      {insights.map((insight, index) => (
        <Accordion key={insight.building_id} sx={{ mb: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
              <Box sx={{ mr: 2 }}>
                {getTrendIcon(insight.predictions.trend_direction)}
              </Box>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6">
                  {insight.building_name || `Building ${insight.building_id}`}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Current Readiness: {formatScore(insight.current_readiness.readiness_score)} |
                  30-day Prediction: {formatScore(insight.predictions.predicted_30_day)}
                </Typography>
              </Box>
              <Box sx={{ mr: 2 }}>
                <LinearProgress
                  variant="determinate"
                  value={insight.current_readiness.readiness_score * 100}
                  color={getReadinessColor(insight.current_readiness.readiness_score)}
                  sx={{ width: 100, height: 8, borderRadius: 4 }}
                />
              </Box>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={3}>
              {/* Current Metrics */}
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle1" gutterBottom>
                  Current Metrics
                </Typography>
                <Box sx={{ mb: 2 }}>
                  {Object.entries(insight.current_readiness.metrics).map(([key, value]) => (
                    <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="body2">
                        {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {formatScore(value as number)}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Grid>

              {/* Predictions */}
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle1" gutterBottom>
                  Predictions
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">7-day Prediction:</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {formatScore(insight.predictions.predicted_7_day)}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">30-day Prediction:</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {formatScore(insight.predictions.predicted_30_day)}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Confidence:</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {formatScore(insight.predictions.confidence)}
                    </Typography>
                  </Box>
                </Box>
              </Grid>

              {/* Recommendations */}
              {insight.recommendations.length > 0 && (
                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle1" gutterBottom>
                    AI Recommendations
                  </Typography>
                  <Grid container spacing={2}>
                    {insight.recommendations.map((rec, recIndex) => (
                      <Grid item xs={12} md={6} key={recIndex}>
                        <Card variant="outlined">
                          <CardContent>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                              <Typography variant="subtitle2" fontWeight="bold">
                                {rec.title}
                              </Typography>
                              <Chip
                                label={rec.priority}
                                color={getPriorityColor(rec.priority)}
                                size="small"
                              />
                            </Box>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                              {rec.description}
                            </Typography>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                              <Typography variant="caption">
                                Impact: {formatScore(rec.expected_impact)}
                              </Typography>
                              <Typography variant="caption">
                                Confidence: {formatScore(rec.confidence)}
                              </Typography>
                            </Box>
                            {rec.actions.length > 0 && (
                              <Box sx={{ mt: 1 }}>
                                <Typography variant="caption" color="text.secondary">
                                  Actions:
                                </Typography>
                                <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>
                                  {rec.actions.map((action, actionIndex) => (
                                    <li key={actionIndex}>
                                      <Typography variant="caption">{action}</Typography>
                                    </li>
                                  ))}
                                </ul>
                              </Box>
                            )}
                            {rec.deadline && (
                              <Typography variant="caption" color="error">
                                Deadline: {new Date(rec.deadline).toLocaleDateString()}
                              </Typography>
                            )}
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </Grid>
              )}
            </Grid>
          </AccordionDetails>
        </Accordion>
      ))}

      {insights.length === 0 && !loading && (
        <Alert severity="info">
          No AI insights available for the selected buildings. Please ensure buildings have inspection data.
        </Alert>
      )}
    </Box>
  );
};

export default AIInsightsPanel;