import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Image as ImageIcon,
  Security as SecurityIcon,
  People as PeopleIcon,
  Monitor as MonitorIcon,
  Storage as StorageIcon,
  Assessment as ReportsIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { BackgroundImageManager } from '../components/admin/BackgroundImageManager';
import { SystemConfiguration } from '../components/admin/SystemConfiguration';
import { UserManagement } from '../components/admin/UserManagement';
import { SecurityOverview } from '../components/admin/SecurityOverview';
import { useAppSelector } from '../store';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `admin-tab-${index}`,
    'aria-controls': `admin-tabpanel-${index}`,
  };
}

export const AdminPanel: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAppSelector((state) => state.auth.user);
  const [currentTab, setCurrentTab] = useState(0);
  const [systemStats, setSystemStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    totalBuildings: 0,
    totalTests: 0,
    systemUptime: '0d 0h 0m',
    lastBackup: null as string | null,
    securityAlerts: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user has admin access
    if (!user || user.role !== 'admin') {
      navigate('/unauthorized');
      return;
    }

    // Load system statistics
    loadSystemStats();
  }, [user, navigate]);

  const loadSystemStats = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API calls
      // For MVP, using mock data
      setSystemStats({
        totalUsers: 25,
        activeUsers: 18,
        totalBuildings: 145,
        totalTests: 2340,
        systemUptime: '15d 8h 23m',
        lastBackup: new Date().toISOString(),
        securityAlerts: 2,
      });
    } catch (error) {
      console.error('Failed to load system stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const adminSections = [
    {
      title: t('admin.backgroundManagement'),
      description: t('admin.backgroundManagementDesc'),
      icon: <ImageIcon color="primary" />,
      action: () => setCurrentTab(1),
    },
    {
      title: t('admin.systemConfiguration'),
      description: t('admin.systemConfigurationDesc'),
      icon: <SettingsIcon color="primary" />,
      action: () => setCurrentTab(2),
    },
    {
      title: t('admin.userManagement'),
      description: t('admin.userManagementDesc'),
      icon: <PeopleIcon color="primary" />,
      action: () => setCurrentTab(3),
    },
    {
      title: t('admin.securityOverview'),
      description: t('admin.securityOverviewDesc'),
      icon: <SecurityIcon color="primary" />,
      action: () => setCurrentTab(4),
    },
  ];

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('admin.title')}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {t('admin.description')}
        </Typography>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs
          value={currentTab}
          onChange={handleTabChange}
          aria-label="admin panel tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label={t('admin.overview')} {...a11yProps(0)} />
          <Tab label={t('admin.backgroundManagement')} {...a11yProps(1)} />
          <Tab label={t('admin.systemConfiguration')} {...a11yProps(2)} />
          <Tab label={t('admin.userManagement')} {...a11yProps(3)} />
          <Tab label={t('admin.securityOverview')} {...a11yProps(4)} />
        </Tabs>
      </Box>

      <TabPanel value={currentTab} index={0}>
        {/* System Overview */}
        <Grid container spacing={3}>
          {/* System Statistics */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('admin.systemStatistics')}
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {systemStats.totalUsers}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('admin.totalUsers')}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="success.main">
                      {systemStats.activeUsers}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('admin.activeUsers')}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="info.main">
                      {systemStats.totalBuildings}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('admin.totalBuildings')}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="warning.main">
                      {systemStats.totalTests}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t('admin.totalTests')}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </Paper>

            {/* Quick Actions */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('admin.quickActions')}
              </Typography>
              <Grid container spacing={2}>
                {adminSections.map((section, index) => (
                  <Grid item xs={12} sm={6} key={index}>
                    <Card variant="outlined" sx={{ height: '100%' }}>
                      <CardContent>
                        <Box display="flex" alignItems="center" mb={2}>
                          {section.icon}
                          <Typography variant="h6" sx={{ ml: 1 }}>
                            {section.title}
                          </Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                          {section.description}
                        </Typography>
                      </CardContent>
                      <CardActions>
                        <Button size="small" onClick={section.action}>
                          {t('common.open')}
                        </Button>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>

          {/* System Status */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('admin.systemStatus')}
              </Typography>
              <List>
                <ListItem>
                  <ListItemIcon>
                    <CheckIcon color="success" />
                  </ListItemIcon>
                  <ListItemText
                    primary={t('admin.systemUptime')}
                    secondary={systemStats.systemUptime}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <StorageIcon color="success" />
                  </ListItemIcon>
                  <ListItemText
                    primary={t('admin.lastBackup')}
                    secondary={
                      systemStats.lastBackup
                        ? new Date(systemStats.lastBackup).toLocaleString('he-IL')
                        : t('admin.noBackup')
                    }
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <MonitorIcon color="info" />
                  </ListItemIcon>
                  <ListItemText
                    primary={t('admin.activeConnections')}
                    secondary={systemStats.activeUsers}
                  />
                </ListItem>
              </List>
            </Paper>

            {/* Security Alerts */}
            {systemStats.securityAlerts > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  {t('admin.securityAlertsMessage', { count: systemStats.securityAlerts })}
                </Typography>
                <Button
                  size="small"
                  sx={{ mt: 1 }}
                  onClick={() => setCurrentTab(4)}
                >
                  {t('admin.viewSecurityAlerts')}
                </Button>
              </Alert>
            )}

            {/* System Health */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('admin.systemHealth')}
              </Typography>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="body2" sx={{ minWidth: 100 }}>
                  {t('admin.database')}:
                </Typography>
                <Chip label={t('admin.healthy')} color="success" size="small" />
              </Box>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="body2" sx={{ minWidth: 100 }}>
                  {t('admin.storage')}:
                </Typography>
                <Chip label={t('admin.healthy')} color="success" size="small" />
              </Box>
              <Box display="flex" alignItems="center" mb={1}>
                <Typography variant="body2" sx={{ minWidth: 100 }}>
                  {t('admin.authentication')}:
                </Typography>
                <Chip label={t('admin.healthy')} color="success" size="small" />
              </Box>
              <Box display="flex" alignItems="center">
                <Typography variant="body2" sx={{ minWidth: 100 }}>
                  {t('admin.api')}:
                </Typography>
                <Chip label={t('admin.healthy')} color="success" size="small" />
              </Box>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={currentTab} index={1}>
        <BackgroundImageManager />
      </TabPanel>

      <TabPanel value={currentTab} index={2}>
        <SystemConfiguration />
      </TabPanel>

      <TabPanel value={currentTab} index={3}>
        <UserManagement />
      </TabPanel>

      <TabPanel value={currentTab} index={4}>
        <SecurityOverview />
      </TabPanel>
    </Container>
  );
};

export default AdminPanel;