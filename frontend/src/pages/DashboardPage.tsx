import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  useTheme,
  Alert,
  Snackbar,
  Fade,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Home as HomeIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import ReadinessDashboard from '../components/dashboard/ReadinessDashboard';
import BuildingReadinessDashboard from '../components/dashboard/BuildingReadinessDashboard';
import { dashboardApi, DashboardStats } from '../services/dashboardApi';

interface StatsCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}

const StatsCard: React.FC<StatsCardProps> = ({ title, value, icon, color }) => {
  return (
    <Card sx={{ height: '100%' }}>
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
      </CardContent>
    </Card>
  );
};

export const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const [stats, setStats] = useState<DashboardStats>({
    totalBuildings: 45,
    totalTests: 234,
    pendingTests: 12,
    completedTests: 198,
    totalRecords: 494,
    lastUpdateTime: new Date().toISOString(),
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showReadinessDashboard, setShowReadinessDashboard] = useState(true);

  // Load dashboard data on component mount
  useEffect(() => {
    loadDashboardData();
    // Set up real-time updates every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const dashboardStats = await dashboardApi.getDashboardStats();
      setStats(dashboardStats);
      setShowSuccess(true);
    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('שגיאה בטעינת נתוני הלוח בקרה');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshData = async () => {
    await loadDashboardData();
  };

  const recentActivity = [
    {
      id: 1,
      type: 'test_completed',
      building: 'מבנה 40',
      testType: 'הנדסית',
      date: '2025-07-17',
    },
    {
      id: 2,
      type: 'test_created',
      building: 'מבנה 25',
      testType: 'ביטחונית',
      date: '2025-07-17',
    },
    {
      id: 3,
      type: 'building_added',
      building: 'מבנה 67',
      testType: '',
      date: '2025-07-16',
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      {/* Success Snackbar */}
      <Snackbar
        open={showSuccess}
        autoHideDuration={3000}
        onClose={() => setShowSuccess(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert onClose={() => setShowSuccess(false)} severity="success" sx={{ width: '100%' }}>
          נתוני הלוח עודכנו בהצלחה
        </Alert>
      </Snackbar>

      {/* Error Snackbar */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert onClose={() => setError(null)} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>

      {/* Main Dashboard Content - PRD Compliant Building Readiness Dashboard */}
      <Fade in={showReadinessDashboard} timeout={500}>
        <Box>
          <BuildingReadinessDashboard
            onRefresh={handleRefreshData}
            isLoading={loading}
          />
        </Box>
      </Fade>

      {/* Legacy Dashboard - Hidden by default, can be toggled */}
      <Fade in={!showReadinessDashboard} timeout={500}>
        <Box sx={{ display: showReadinessDashboard ? 'none' : 'block' }}>
          <Typography variant="h4" component="h1" gutterBottom>
            {t('dashboard.title')}
          </Typography>
          
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatsCard
                title={t('dashboard.totalBuildings')}
                value={stats.totalBuildings}
                icon={<HomeIcon />}
                color={theme.palette.primary.main}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatsCard
                title={t('dashboard.totalTests')}
                value={stats.totalTests}
                icon={<AssessmentIcon />}
                color={theme.palette.secondary.main}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatsCard
                title={t('dashboard.pendingTests')}
                value={stats.pendingTests}
                icon={<ScheduleIcon />}
                color={theme.palette.warning.main}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatsCard
                title={t('dashboard.completedTests')}
                value={stats.completedTests}
                icon={<CheckCircleIcon />}
                color={theme.palette.success.main}
              />
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  {t('dashboard.testsByType')}
                </Typography>
                <Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography color="text.secondary">
                    Chart component will be implemented here
                  </Typography>
                </Box>
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
                    </Box>
                  ))}
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Box>
      </Fade>
    </Box>
  );
};

export default DashboardPage;