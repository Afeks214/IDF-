import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  useTheme,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  CircularProgress,
  Fade,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import ReadinessPieChart from './ReadinessPieChart';
import BuildingFloorHierarchy from './BuildingFloorHierarchy';
import { dashboardApi, type ReadinessCategories, type BuildingData } from '../../services/dashboardApi';

interface ReadinessData {
  name: string;
  value: number;
  color: string;
  total?: number;
}

interface ReadinessDashboardProps {
  onRefresh?: () => void;
  isLoading?: boolean;
}

const ReadinessDashboard: React.FC<ReadinessDashboardProps> = ({
  onRefresh,
  isLoading = false,
}) => {
  const theme = useTheme();
  const { t } = useTranslation();
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [readinessData, setReadinessData] = useState<ReadinessCategories | null>(null);
  const [buildingData, setBuildingData] = useState<BuildingData[]>([]);
  const [localLoading, setLocalLoading] = useState(false);
  const [, setError] = useState<string | null>(null);

  // Load data on component mount
  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLocalLoading(true);
      setError(null);
      
      // Load readiness data and building hierarchy in parallel
      const [readiness, buildings] = await Promise.all([
        dashboardApi.getReadinessData(),
        dashboardApi.getBuildingHierarchy(),
      ]);
      
      setReadinessData(readiness);
      setBuildingData(buildings);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('שגיאה בטעינת נתוני הדשבורד');
    } finally {
      setLocalLoading(false);
    }
  };

  // Get default mock data if API data is not available
  const getMockData = () => {
    return {
      buildingReadinessData: [
        { name: 'מעולה (90%+)', value: 12, color: theme.palette.success.main },
        { name: 'טוב (70-89%)', value: 18, color: theme.palette.warning.main },
        { name: 'דורש שיפור (<70%)', value: 15, color: theme.palette.error.main },
      ],
      generalReadinessData: [
        { name: 'כשיר לחלוטין', value: 25, color: '#4caf50' },
        { name: 'כשיר עם הערות', value: 15, color: '#ff9800' },
        { name: 'לא כשיר', value: 5, color: '#f44336' },
      ],
      engineeringReadinessData: [
        { name: 'מבנה תקין', value: 30, color: '#2196f3' },
        { name: 'דרוש תיקון קל', value: 10, color: '#ff9800' },
        { name: 'דרוש תיקון דחוף', value: 5, color: '#f44336' },
      ],
      operationalReadinessData: [
        { name: 'מוכן לפעילות', value: 28, color: '#9c27b0' },
        { name: 'דרוש השלמות', value: 12, color: '#ff9800' },
        { name: 'לא מוכן', value: 5, color: '#f44336' },
      ],
    };
  };

  // Use API data if available, otherwise use mock data
  const mockData = getMockData();
  const buildingReadinessData = readinessData?.buildingReadiness || mockData.buildingReadinessData;
  const generalReadinessData = readinessData?.generalReadiness || mockData.generalReadinessData;
  const engineeringReadinessData = readinessData?.engineeringReadiness || mockData.engineeringReadinessData;
  const operationalReadinessData = readinessData?.operationalReadiness || mockData.operationalReadinessData;
  const buildings = buildingData.length > 0 ? buildingData : [];

  const handleRefresh = async () => {
    if (onRefresh) {
      onRefresh();
    }
    await loadDashboardData();
  };

  const handleSectionClick = (data: ReadinessData) => {
    console.log('Clicked section:', data);
    // Here you would typically navigate to a detailed view or filter data
  };

  const handleBuildingClick = (building: any) => {
    console.log('Clicked building:', building);
    // Navigate to building details
  };

  const handleFloorClick = (building: any, floor: any) => {
    console.log('Clicked floor:', building, floor);
    // Navigate to floor details
  };

  const getSummaryStats = () => {
    const totalBuildings = buildingReadinessData.reduce((sum, item) => sum + item.value, 0);
    const excellentBuildings = buildingReadinessData.find(item => item.name.includes('מעולה'))?.value || 0;
    const improvementNeeded = buildingReadinessData.find(item => item.name.includes('דורש שיפור'))?.value || 0;
    
    return {
      totalBuildings,
      excellentPercentage: ((excellentBuildings / totalBuildings) * 100).toFixed(1),
      improvementNeeded,
      trend: excellentBuildings > improvementNeeded ? 'up' : 'down',
    };
  };

  const stats = getSummaryStats();

  return (
    <Box sx={{ width: '100%', p: 2 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <AssessmentIcon sx={{ fontSize: 40, color: theme.palette.primary.main }} />
          <Box>
            <Typography variant="h4" component="h1" fontWeight="bold">
              {t('dashboard.title')}
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              {t('dashboard.lastUpdate')}: {lastUpdate.toLocaleString('he-IL')}
            </Typography>
          </Box>
        </Box>
        <Tooltip title={t('dashboard.refreshData')}>
          <IconButton 
            onClick={handleRefresh} 
            disabled={isLoading || localLoading}
            sx={{ position: 'relative' }}
          >
            {localLoading ? (
              <CircularProgress size={24} />
            ) : (
              <RefreshIcon />
            )}
          </IconButton>
        </Tooltip>
      </Box>

      {/* Summary Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h4" fontWeight="bold" color="primary">
                  {stats.totalBuildings}
                </Typography>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {t('dashboard.totalBuildings')}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    בבדיקה
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h4" fontWeight="bold" color="success.main">
                  {stats.excellentPercentage}%
                </Typography>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {t('dashboard.excellentReadiness')}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {stats.trend === 'up' ? (
                      <TrendingUpIcon fontSize="small" color="success" />
                    ) : (
                      <TrendingDownIcon fontSize="small" color="error" />
                    )}
                    <Typography variant="caption" color="text.secondary">
                      {t('dashboard.trend')}
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h4" fontWeight="bold" color="warning.main">
                  {stats.improvementNeeded}
                </Typography>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {t('dashboard.needsImprovement')}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    מבנים
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h4" fontWeight="bold" color="info.main">
                  494
                </Typography>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    {t('dashboard.totalSystemRecords')}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    במערכת
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Dashboard Grid */}
      <Grid container spacing={3}>
        {/* Pie Charts */}
        <Grid item xs={12} md={6}>
          <Fade in={true} timeout={600}>
            <Paper sx={{ p: 2, height: '400px' }}>
              <ReadinessPieChart
                title={t('dashboard.buildingReadiness')}
                data={buildingReadinessData}
                onSectionClick={handleSectionClick}
              />
            </Paper>
          </Fade>
        </Grid>

        <Grid item xs={12} md={6}>
          <Fade in={true} timeout={800}>
            <Paper sx={{ p: 2, height: '400px' }}>
              <ReadinessPieChart
                title={t('dashboard.generalReadiness')}
                data={generalReadinessData}
                onSectionClick={handleSectionClick}
              />
            </Paper>
          </Fade>
        </Grid>

        <Grid item xs={12} md={6}>
          <Fade in={true} timeout={1000}>
            <Paper sx={{ p: 2, height: '400px' }}>
              <ReadinessPieChart
                title={t('dashboard.engineeringReadiness')}
                data={engineeringReadinessData}
                onSectionClick={handleSectionClick}
              />
            </Paper>
          </Fade>
        </Grid>

        <Grid item xs={12} md={6}>
          <Fade in={true} timeout={1200}>
            <Paper sx={{ p: 2, height: '400px' }}>
              <ReadinessPieChart
                title={t('dashboard.operationalReadiness')}
                data={operationalReadinessData}
                onSectionClick={handleSectionClick}
              />
            </Paper>
          </Fade>
        </Grid>

        {/* Building Hierarchy */}
        <Grid item xs={12}>
          <Fade in={true} timeout={1400}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
                {t('dashboard.buildingHierarchy')}
              </Typography>
              <BuildingFloorHierarchy
                buildings={buildings}
                onBuildingClick={handleBuildingClick}
                onFloorClick={handleFloorClick}
              />
            </Paper>
          </Fade>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ReadinessDashboard;