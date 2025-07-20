import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  useTheme,
  Tab,
  Tabs,
  Badge,
  Chip,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Home as HomeIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Psychology as PsychologyIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  Hub as HubIcon,
  Analytics as AnalyticsIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { AIInsightsPanel } from '../ai/AIInsightsPanel';
import { ReadinessPieChart } from './ReadinessPieChart';

interface StatsCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  change?: number;
  aiPrediction?: number;
}

const StatsCard: React.FC<StatsCardProps> = ({ title, value, icon, color, change, aiPrediction }) => {
  const theme = useTheme();
  
  return (
    <Card sx={{ height: '100%', position: 'relative' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box
            sx={{
              backgroundColor: color,
              borderRadius: '50%',
              width: 48,
              height: 48,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              mr: 2,
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </Box>
        <Typography variant="h3" component="div" fontWeight="bold">
          {value}
        </Typography>
        {change !== undefined && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
            {change > 0 ? (
              <TrendingUpIcon color="success" fontSize="small" />
            ) : (
              <WarningIcon color="error" fontSize="small" />
            )}
            <Typography variant="body2" color={change > 0 ? 'success.main' : 'error.main'} sx={{ ml: 0.5 }}>
              {change > 0 ? '+' : ''}{change}% from last week
            </Typography>
          </Box>
        )}
        {aiPrediction !== undefined && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              AI 30-day prediction: {aiPrediction}
            </Typography>
          </Box>
        )}
      </CardContent>
      {aiPrediction !== undefined && (
        <Box sx={{ position: 'absolute', top: 8, right: 8 }}>
          <PsychologyIcon fontSize="small" color="primary" />
        </Box>
      )}
    </Card>
  );
};

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
};

export const AIEnhancedDashboard: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [selectedBuildings, setSelectedBuildings] = useState<string[]>([]);
  const [aiSystemStatus, setAiSystemStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Mock data - in real app this would come from API
  const [stats, setStats] = useState({
    totalBuildings: 45,
    totalTests: 234,
    pendingTests: 12,
    completedTests: 198,
    aiPredictions: {
      totalBuildings: 48,
      totalTests: 267,
      pendingTests: 8,
      completedTests: 225,
    },
    changes: {
      totalBuildings: 2,
      totalTests: 8,
      pendingTests: -3,
      completedTests: 12,
    }
  });

  const [availableBuildings] = useState([
    { id: 'B001', name: 'מבנה 1' },
    { id: 'B002', name: 'מבנה 2' },
    { id: 'B003', name: 'מבנה 3' },
    { id: 'B004', name: 'מבנה 4' },
    { id: 'B005', name: 'מבנה 5' },
  ]);

  const recentActivity = [
    {
      id: 1,
      type: 'test_completed',
      building: 'מבנה 40',
      testType: 'הנדסית',
      date: '2025-07-17',
      aiRecommendation: 'Schedule follow-up inspection',
    },
    {
      id: 2,
      type: 'test_created',
      building: 'מבנה 25',
      testType: 'ביטחונית',
      date: '2025-07-17',
      aiRecommendation: 'Prioritize contractor coordination',
    },
    {
      id: 3,
      type: 'building_added',
      building: 'מבנה 67',
      testType: '',
      date: '2025-07-16',
      aiRecommendation: 'Initialize baseline inspection',
    },
  ];

  const fetchAISystemStatus = async () => {
    try {
      const response = await fetch('/api/v1/ai/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setAiSystemStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch AI system status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAISystemStatus();
    // Set default selected buildings
    setSelectedBuildings(['B001', 'B002', 'B003']);
  }, []);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleBuildingSelectionChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setSelectedBuildings(typeof value === 'string' ? value.split(',') : value);
  };

  const getSystemStatusColor = () => {
    if (!aiSystemStatus) return 'default';
    return aiSystemStatus.grandmodel_integration?.available ? 'success' : 'error';
  };

  const getSystemStatusText = () => {
    if (!aiSystemStatus) return 'Unknown';
    return aiSystemStatus.grandmodel_integration?.available ? 'Active' : 'Offline';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading AI-Enhanced Dashboard...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {t('dashboard.title')} - AI Enhanced
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Chip
            icon={<HubIcon />}
            label={`GrandModel ${getSystemStatusText()}`}
            color={getSystemStatusColor()}
            sx={{ mr: 1 }}
          />
          <Chip
            icon={<AnalyticsIcon />}
            label="AI Insights"
            color="primary"
          />
        </Box>
      </Box>

      {/* AI System Status Alert */}
      {aiSystemStatus && !aiSystemStatus.grandmodel_integration?.available && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          GrandModel AI system is offline. Some predictive features may be limited.
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.totalBuildings')}
            value={stats.totalBuildings}
            icon={<HomeIcon />}
            color={theme.palette.primary.main}
            change={stats.changes.totalBuildings}
            aiPrediction={stats.aiPredictions.totalBuildings}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.totalTests')}
            value={stats.totalTests}
            icon={<AssessmentIcon />}
            color={theme.palette.secondary.main}
            change={stats.changes.totalTests}
            aiPrediction={stats.aiPredictions.totalTests}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.pendingTests')}
            value={stats.pendingTests}
            icon={<ScheduleIcon />}
            color={theme.palette.warning.main}
            change={stats.changes.pendingTests}
            aiPrediction={stats.aiPredictions.pendingTests}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.completedTests')}
            value={stats.completedTests}
            icon={<CheckCircleIcon />}
            color={theme.palette.success.main}
            change={stats.changes.completedTests}
            aiPrediction={stats.aiPredictions.completedTests}
          />
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Dashboard Overview" />
          <Tab 
            label={
              <Badge badgeContent={selectedBuildings.length} color="primary">
                AI Insights
              </Badge>
            }
          />
          <Tab label="MARL Coordination" />
          <Tab label="Predictive Analytics" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('dashboard.testsByType')}
              </Typography>
              <ReadinessPieChart />
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('dashboard.recentActivity')}
              </Typography>
              <Box sx={{ mt: 2 }}>
                {recentActivity.map((activity) => (
                  <Box
                    key={activity.id}
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      borderBottom: 1,
                      borderColor: 'divider',
                      pb: 2,
                      mb: 2,
                      '&:last-child': { borderBottom: 0, mb: 0 },
                    }}
                  >
                    <Typography variant="body2" fontWeight="medium">
                      {activity.building}
                    </Typography>
                    {activity.testType && (
                      <Typography variant="body2" color="text.secondary">
                        {activity.testType}
                      </Typography>
                    )}
                    <Typography variant="caption" color="text.secondary">
                      {activity.date}
                    </Typography>
                    {activity.aiRecommendation && (
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                        <PsychologyIcon fontSize="small" color="primary" sx={{ mr: 0.5 }} />
                        <Typography variant="caption" color="primary">
                          {activity.aiRecommendation}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                ))}
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Box sx={{ mb: 3 }}>
          <FormControl sx={{ minWidth: 300 }}>
            <InputLabel>Select Buildings for AI Analysis</InputLabel>
            <Select
              multiple
              value={selectedBuildings}
              onChange={handleBuildingSelectionChange}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip
                      key={value}
                      label={availableBuildings.find(b => b.id === value)?.name || value}
                      size="small"
                    />
                  ))}
                </Box>
              )}
            >
              {availableBuildings.map((building) => (
                <MenuItem key={building.id} value={building.id}>
                  {building.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
        <AIInsightsPanel buildingIds={selectedBuildings} />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            MARL Coordination System
          </Typography>
          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" color="text.secondary">
              Multi-Agent Reinforcement Learning coordination for building readiness optimization.
            </Typography>
          </Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Coordination Status
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                    <Typography variant="body2">
                      {aiSystemStatus?.marl_coordination?.enabled ? 'Active' : 'Inactive'}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Status: {aiSystemStatus?.marl_coordination?.status || 'Unknown'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Synergy Patterns
                  </Typography>
                  <Box sx={{ mb: 1 }}>
                    <Chip label="Sequential Synergy" color="primary" size="small" sx={{ mr: 1, mb: 1 }} />
                    <Chip label="MLMI Patterns" color="secondary" size="small" sx={{ mr: 1, mb: 1 }} />
                    <Chip label="NWRQK Patterns" color="secondary" size="small" sx={{ mr: 1, mb: 1 }} />
                    <Chip label="FVG Patterns" color="secondary" size="small" sx={{ mr: 1, mb: 1 }} />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    AI-powered pattern recognition for building readiness optimization.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Predictive Analytics Engine
          </Typography>
          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" color="text.secondary">
              Advanced predictive modeling for building readiness forecasting and optimization.
            </Typography>
          </Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    7-Day Forecast
                  </Typography>
                  <Typography variant="h4" color="primary">
                    +12%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Expected readiness improvement
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    30-Day Forecast
                  </Typography>
                  <Typography variant="h4" color="success.main">
                    +28%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Projected readiness improvement
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Risk Assessment
                  </Typography>
                  <Typography variant="h4" color="warning.main">
                    Low
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Current system risk level
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      </TabPanel>
    </Box>
  );
};

export default AIEnhancedDashboard;