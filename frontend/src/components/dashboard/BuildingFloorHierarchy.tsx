import React, { useState } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Collapse,
  IconButton,
  Chip,
  useTheme,
} from '@mui/material';
import {
  ExpandLess,
  ExpandMore,
  Business as BusinessIcon,
  Layers as LayersIcon,
} from '@mui/icons-material';

interface Floor {
  id: string;
  name: string;
  level: number;
  totalRooms: number;
  readinessScore: number;
  lastInspection: string;
}

interface Building {
  id: string;
  name: string;
  code: string;
  floors: Floor[];
  totalFloors: number;
  overallReadiness: number;
  manager: string;
  lastUpdate: string;
}

interface BuildingFloorHierarchyProps {
  buildings: Building[];
  onBuildingClick?: (building: Building) => void;
  onFloorClick?: (building: Building, floor: Floor) => void;
}

const BuildingFloorHierarchy: React.FC<BuildingFloorHierarchyProps> = ({
  buildings,
  onBuildingClick,
  onFloorClick,
}) => {
  const [expandedBuildings, setExpandedBuildings] = useState<Set<string>>(new Set());
  const theme = useTheme();

  const toggleBuilding = (buildingId: string) => {
    const newExpanded = new Set(expandedBuildings);
    if (newExpanded.has(buildingId)) {
      newExpanded.delete(buildingId);
    } else {
      newExpanded.add(buildingId);
    }
    setExpandedBuildings(newExpanded);
  };

  const getReadinessColor = (score: number) => {
    if (score >= 90) return theme.palette.success.main;
    if (score >= 70) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  const getReadinessText = (score: number) => {
    if (score >= 90) return 'מעולה';
    if (score >= 70) return 'טוב';
    return 'דורש שיפור';
  };

  return (
    <Box sx={{ width: '100%', maxHeight: '500px', overflow: 'auto' }}>
      <Typography
        variant="h6"
        component="h3"
        sx={{
          mb: 2,
          fontWeight: 'bold',
          color: theme.palette.primary.main,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <BusinessIcon />
        מבנים וקומות
      </Typography>
      
      <List sx={{ width: '100%' }}>
        {buildings.map((building) => (
          <Box key={building.id}>
            <ListItem
              disablePadding
              sx={{
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                mb: 1,
              }}
            >
              <ListItemButton
                onClick={() => toggleBuilding(building.id)}
                sx={{
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.04)',
                  },
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    mr: 2,
                  }}
                >
                  <BusinessIcon color="primary" />
                </Box>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {building.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        ({building.code})
                      </Typography>
                      <Chip
                        label={`${building.totalFloors} קומות`}
                        size="small"
                        variant="outlined"
                        color="primary"
                      />
                    </Box>
                  }
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                          כשירות כללית:
                        </Typography>
                        <Chip
                          label={`${building.overallReadiness}% - ${getReadinessText(building.overallReadiness)}`}
                          size="small"
                          sx={{
                            backgroundColor: getReadinessColor(building.overallReadiness),
                            color: 'white',
                            fontWeight: 'bold',
                          }}
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        מנהל: {building.manager}
                      </Typography>
                    </Box>
                  }
                />
                <IconButton
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onBuildingClick) {
                      onBuildingClick(building);
                    }
                  }}
                  size="small"
                >
                  {expandedBuildings.has(building.id) ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </ListItemButton>
            </ListItem>
            
            <Collapse in={expandedBuildings.has(building.id)} timeout="auto" unmountOnExit>
              <List component="div" disablePadding sx={{ mr: 2 }}>
                {building.floors.map((floor) => (
                  <ListItem
                    key={floor.id}
                    sx={{
                      pl: 4,
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      mb: 0.5,
                      backgroundColor: 'rgba(0, 0, 0, 0.02)',
                    }}
                  >
                    <ListItemButton
                      onClick={() => {
                        if (onFloorClick) {
                          onFloorClick(building, floor);
                        }
                      }}
                      sx={{
                        '&:hover': {
                          backgroundColor: 'rgba(0, 0, 0, 0.04)',
                        },
                      }}
                    >
                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1,
                          mr: 2,
                        }}
                      >
                        <LayersIcon color="secondary" fontSize="small" />
                      </Box>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Typography variant="body1" fontWeight="medium">
                              {floor.name}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              (קומה {floor.level})
                            </Typography>
                            <Chip
                              label={`${floor.totalRooms} חדרים`}
                              size="small"
                              variant="outlined"
                              color="secondary"
                            />
                          </Box>
                        }
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 0.5 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="body2" color="text.secondary">
                                כשירות:
                              </Typography>
                              <Chip
                                label={`${floor.readinessScore}%`}
                                size="small"
                                sx={{
                                  backgroundColor: getReadinessColor(floor.readinessScore),
                                  color: 'white',
                                  fontWeight: 'bold',
                                }}
                              />
                            </Box>
                            <Typography variant="body2" color="text.secondary">
                              בדיקה אחרונה: {floor.lastInspection}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Collapse>
          </Box>
        ))}
      </List>
    </Box>
  );
};

export default BuildingFloorHierarchy;