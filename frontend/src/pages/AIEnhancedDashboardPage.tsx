import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  useTheme,
  Switch,
  FormControlLabel,
  Chip,
  Alert,
  Snackbar,
  Fade,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Home as HomeIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Psychology as PsychologyIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { AIEnhancedDashboard } from '../components/dashboard/AIEnhancedDashboard';
import ReadinessDashboard from '../components/dashboard/ReadinessDashboard';
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

export const AIEnhancedDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const [aiModeEnabled, setAiModeEnabled] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await dashboardApi.getStats();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch data');
        setSnackbarOpen(true);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  // Mock data fallback
  const fallbackStats = {
    totalBuildings: 45,
    totalTests: 234,
    pendingTests: 12,
    completedTests: 198,
  };

  const displayStats = stats || fallbackStats;

  // If AI mode is enabled, show the AI-enhanced dashboard
  if (aiModeEnabled) {
    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 3, pb: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Chip
              icon={<PsychologyIcon />}
              label="AI Mode Active"
              color="primary"
              sx={{ mr: 2 }}
            />
            <Typography variant="h4" component="h1">
              {t('dashboard.title')} - AI Enhanced
            </Typography>
          </Box>
          <FormControlLabel
            control={
              <Switch
                checked={aiModeEnabled}
                onChange={(e) => setAiModeEnabled(e.target.checked)}
                color="primary"
              />
            }
            label="Enable AI Insights"
          />
        </Box>
        <AIEnhancedDashboard />
        
        {/* Error Snackbar */}
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={6000}
          onClose={handleCloseSnackbar}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
            {error}
          </Alert>
        </Snackbar>
      </Box>
    );
  }

  // Standard dashboard mode
  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {t('dashboard.title')}
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={aiModeEnabled}
              onChange={(e) => setAiModeEnabled(e.target.checked)}
              color="primary"
            />
          }
          label="Enable AI Insights"
        />
      </Box>
      
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.totalBuildings')}
            value={displayStats.totalBuildings}
            icon={<HomeIcon />}
            color={theme.palette.primary.main}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.totalTests')}
            value={displayStats.totalTests}
            icon={<AssessmentIcon />}
            color={theme.palette.secondary.main}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.pendingTests')}
            value={displayStats.pendingTests}
            icon={<ScheduleIcon />}
            color={theme.palette.warning.main}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title={t('dashboard.completedTests')}
            value={displayStats.completedTests}
            icon={<CheckCircleIcon />}
            color={theme.palette.success.main}
          />
        </Grid>
      </Grid>

      <Fade in={!loading}>
        <Box>
          <ReadinessDashboard />
        </Box>
      </Fade>

      {/* Error Snackbar */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AIEnhancedDashboardPage;