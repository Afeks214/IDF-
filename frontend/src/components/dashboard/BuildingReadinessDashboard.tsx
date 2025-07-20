import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  useTheme,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Divider,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import {
  Home as HomeIcon,
  Engineering as EngineeringIcon,
  Settings as SettingsIcon,
  Business as BusinessIcon,
  Refresh as RefreshIcon,
  Floor as FloorIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { buildingReadinessApi, BuildingData, ReadinessMetrics } from '../../services/buildingReadinessApi';

// Types imported from API service

interface PieChartData {
  name: string;
  value: number;
  color: string;
}

interface BuildingReadinessDashboardProps {
  onRefresh?: () => void;
  isLoading?: boolean;
}

const BuildingReadinessDashboard: React.FC<BuildingReadinessDashboardProps> = ({
  onRefresh,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const theme = useTheme();
  const [selectedBuilding, setSelectedBuilding] = useState<string>('');
  const [selectedFloor, setSelectedFloor] = useState<string>('');
  const [buildings, setBuildings] = useState<BuildingData[]>([]);
  const [readinessData, setReadinessData] = useState<ReadinessMetrics>({
    building_readiness: 0,
    general_readiness: 0,
    engineering_readiness: 0,
    operational_readiness: 0,
  });
  const [loading, setLoading] = useState(false);

  // Mock data based on actual Excel structure
  const mockBuildings: BuildingData[] = [
    {
      building_id: '40',
      building_name: 'מבנה 40',
      building_manager: 'יוסי שמש',
      floor_count: 4,
      floors: [
        { floor_id: '40-1', floor_label: 'קומה 1', inspection_count: 12, completion_rate: 85 },
        { floor_id: '40-2', floor_label: 'קומה 2', inspection_count: 8, completion_rate: 92 },
        { floor_id: '40-3', floor_label: 'קומה 3', inspection_count: 6, completion_rate: 78 },
        { floor_id: '40-4', floor_label: 'מרתף', inspection_count: 15, completion_rate: 45 },
      ],
      readiness_metrics: {
        building_readiness: 75,
        general_readiness: 82,
        engineering_readiness: 68,
        operational_readiness: 88,
      },
    },
    {
      building_id: '25',
      building_name: 'מבנה 25',
      building_manager: 'דנה אבני',
      floor_count: 3,
      floors: [
        { floor_id: '25-1', floor_label: 'קומה 1', inspection_count: 10, completion_rate: 90 },
        { floor_id: '25-2', floor_label: 'קומה 2', inspection_count: 12, completion_rate: 95 },
        { floor_id: '25-3', floor_label: 'קומה 3', inspection_count: 8, completion_rate: 88 },
      ],
      readiness_metrics: {
        building_readiness: 91,
        general_readiness: 89,
        engineering_readiness: 93,
        operational_readiness: 87,
      },
    },
    {
      building_id: '10A',
      building_name: 'מבנה 10A',
      building_manager: 'ציון לחיאני',
      floor_count: 5,
      floors: [
        { floor_id: '10A-1', floor_label: 'קומה 1', inspection_count: 14, completion_rate: 72 },
        { floor_id: '10A-2', floor_label: 'קומה 2', inspection_count: 11, completion_rate: 85 },
        { floor_id: '10A-3', floor_label: 'קומה 3', inspection_count: 9, completion_rate: 90 },
        { floor_id: '10A-4', floor_label: 'קומה 4', inspection_count: 7, completion_rate: 95 },
        { floor_id: '10A-5', floor_label: 'גג', inspection_count: 5, completion_rate: 80 },
      ],
      readiness_metrics: {
        building_readiness: 84,
        general_readiness: 86,
        engineering_readiness: 79,
        operational_readiness: 92,
      },
    },
  ];

  useEffect(() => {
    loadBuildings();
  }, []);

  useEffect(() => {
    if (selectedBuilding) {
      loadBuildingReadiness(selectedBuilding);
    }
  }, [selectedBuilding]);

  const loadBuildings = async () => {
    try {
      setLoading(true);
      const response = await buildingReadinessApi.getBuildings();
      const buildingData: BuildingData[] = response.buildings.map(building => ({
        building_id: building.building_id,
        building_name: building.building_name,
        building_manager: building.building_manager,
        floor_count: building.floor_count,
        floors: [],
        readiness_metrics: {
          building_readiness: 0,
          general_readiness: 0,
          engineering_readiness: 0,
          operational_readiness: 0,
        },
        total_inspections: building.total_inspections,
        completed_inspections: 0,
        last_updated: new Date().toISOString(),
      }));
      
      setBuildings(buildingData);
      if (buildingData.length > 0) {
        setSelectedBuilding(buildingData[0].building_id);
      }
    } catch (error) {
      console.error('Error loading buildings:', error);
      // Fallback to mock data
      setBuildings(mockBuildings);
      if (mockBuildings.length > 0) {
        setSelectedBuilding(mockBuildings[0].building_id);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadBuildingReadiness = async (buildingId: string) => {
    try {
      const buildingData = await buildingReadinessApi.getBuildingReadiness(buildingId);
      setReadinessData(buildingData.readiness_metrics);
      
      // Update the building in the buildings array
      setBuildings(prev => prev.map(building => 
        building.building_id === buildingId 
          ? { ...building, ...buildingData }
          : building
      ));
    } catch (error) {
      console.error('Error loading building readiness:', error);
      // Fallback to mock data
      const building = mockBuildings.find(b => b.building_id === buildingId);
      if (building) {
        setReadinessData(building.readiness_metrics);
      }
    }
  };

  // Prepare pie chart data as per PRD requirements
  const pieChartData = [
    {
      title: 'כשירות מבנה',
      data: [
        { name: 'מוכן', value: readinessData.building_readiness, color: '#4CAF50' },
        { name: 'לא מוכן', value: 100 - readinessData.building_readiness, color: '#F44336' },
      ],
    },
    {
      title: 'כשירות כללי של המבנה',
      data: [
        { name: 'מוכן', value: readinessData.general_readiness, color: '#2196F3' },
        { name: 'לא מוכן', value: 100 - readinessData.general_readiness, color: '#FF9800' },
      ],
    },
    {
      title: 'כשירות הנדסי',
      data: [
        { name: 'מוכן', value: readinessData.engineering_readiness, color: '#9C27B0' },
        { name: 'לא מוכן', value: 100 - readinessData.engineering_readiness, color: '#E91E63' },
      ],
    },
    {
      title: 'כשירות תפעולי',
      data: [
        { name: 'מוכן', value: readinessData.operational_readiness, color: '#00BCD4' },
        { name: 'לא מוכן', value: 100 - readinessData.operational_readiness, color: '#FFEB3B' },
      ],
    },
  ];

  const selectedBuildingData = buildings.find(b => b.building_id === selectedBuilding);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await loadBuildings();
      if (selectedBuilding) {
        await loadBuildingReadiness(selectedBuilding);
      }
      onRefresh?.();
    } finally {
      setLoading(false);
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Paper sx={{ p: 2, backgroundColor: 'rgba(255, 255, 255, 0.95)' }}>
          <Typography variant="body2" fontWeight="bold">
            {payload[0].name}: {payload[0].value}%
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          דשבורד כשירות מבנים - קריית התקשוב
        </Typography>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading || isLoading}
        >
          {loading || isLoading ? <CircularProgress size={20} /> : 'רענן נתונים'}
        </Button>
      </Box>

      {/* Building and Floor Selection */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          בחירת מבנה וקומה
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>מבנה</InputLabel>
              <Select
                value={selectedBuilding}
                label="מבנה"
                onChange={(e) => setSelectedBuilding(e.target.value as string)}
              >
                {buildings.map((building) => (
                  <MenuItem key={building.building_id} value={building.building_id}>
                    {building.building_name} - {building.building_manager}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>קומה</InputLabel>
              <Select
                value={selectedFloor}
                label="קומה"
                onChange={(e) => setSelectedFloor(e.target.value as string)}
              >
                <MenuItem value="">
                  <em>כל הקומות</em>
                </MenuItem>
                {selectedBuildingData?.floors.map((floor) => (
                  <MenuItem key={floor.floor_id} value={floor.floor_id}>
                    {floor.floor_label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Four Pie Charts as per PRD */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          מדדי כשירות מבנה
        </Typography>
        <Grid container spacing={3}>
          {pieChartData.map((chart, index) => (
            <Grid item xs={12} md={6} key={index}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" align="center" gutterBottom>
                    {chart.title}
                  </Typography>
                  <Box sx={{ height: 200 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={chart.data}
                          cx="50%"
                          cy="50%"
                          innerRadius={40}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {chart.data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                  <Typography variant="h4" align="center" fontWeight="bold" color="primary">
                    {chart.data[0].value}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Building-Floor Hierarchy */}
      {selectedBuildingData && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            מבנה {selectedBuildingData.building_name} - מבנה פרטי
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <HomeIcon color="primary" sx={{ mr: 1 }} />
                    <Typography variant="h6">
                      פרטי מבנה
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    מנהל מבנה: {selectedBuildingData.building_manager}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    מספר קומות: {selectedBuildingData.floor_count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    סך הכל בדיקות: {selectedBuildingData.floors.reduce((sum, floor) => sum + floor.inspection_count, 0)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    כשירות לפי קומות
                  </Typography>
                  <List>
                    {selectedBuildingData.floors.map((floor) => (
                      <ListItem key={floor.floor_id}>
                        <ListItemIcon>
                          <FloorIcon color="primary" />
                        </ListItemIcon>
                        <ListItemText
                          primary={floor.floor_label}
                          secondary={`${floor.inspection_count} בדיקות`}
                        />
                        <Chip
                          label={`${floor.completion_rate}%`}
                          color={floor.completion_rate >= 80 ? 'success' : floor.completion_rate >= 60 ? 'warning' : 'error'}
                          variant="outlined"
                        />
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Floor Readiness Bar Chart */}
      {selectedBuildingData && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            כשירות קומות - תצוגה גרפית
          </Typography>
          <Box sx={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={selectedBuildingData.floors}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="floor_label" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="completion_rate" fill="#2196F3" />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default BuildingReadinessDashboard;