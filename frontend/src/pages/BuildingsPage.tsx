import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  FilterList as FilterListIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { useTranslation } from 'react-i18next';
import { Building, BuildingStatus } from '../types';

export const BuildingsPage: React.FC = () => {
  const { t } = useTranslation();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<BuildingStatus | ''>('');

  // Mock data - in real app this would come from API
  const buildings: Building[] = [
    {
      id: '1',
      buildingCode: '40',
      buildingName: 'מבנה ראשי',
      managerName: 'יוסי שמש',
      redTeam: 'צוות אלפא',
      status: 'active',
      testsCount: 12,
      lastTestDate: '2025-07-15',
      createdAt: '2025-01-01',
      updatedAt: '2025-07-15',
    },
    {
      id: '2',
      buildingCode: '25',
      buildingName: 'מבנה משני',
      managerName: 'דני כהן',
      redTeam: 'צוות בטא',
      status: 'active',
      testsCount: 8,
      lastTestDate: '2025-07-10',
      createdAt: '2025-01-15',
      updatedAt: '2025-07-10',
    },
    {
      id: '3',
      buildingCode: '67',
      buildingName: 'מבנה חירום',
      managerName: 'מיכל לוי',
      redTeam: 'צוות גמא',
      status: 'inactive',
      testsCount: 3,
      lastTestDate: '2025-06-20',
      createdAt: '2025-02-01',
      updatedAt: '2025-06-20',
    },
  ];

  const columns: GridColDef[] = [
    {
      field: 'buildingCode',
      headerName: t('buildings.buildingCode'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'buildingName',
      headerName: t('buildings.buildingName'),
      width: 200,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'managerName',
      headerName: t('buildings.managerName'),
      width: 180,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'redTeam',
      headerName: t('buildings.redTeam'),
      width: 150,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'status',
      headerName: t('buildings.status'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
      renderCell: (params: GridRenderCellParams) => (
        <Box
          sx={{
            px: 2,
            py: 0.5,
            borderRadius: 1,
            backgroundColor: params.value === 'active' ? 'success.light' : 'warning.light',
            color: params.value === 'active' ? 'success.dark' : 'warning.dark',
            fontWeight: 'medium',
          }}
        >
          {t(`buildings.${params.value}`)}
        </Box>
      ),
    },
    {
      field: 'testsCount',
      headerName: t('buildings.testsCount'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
      type: 'number',
    },
    {
      field: 'lastTestDate',
      headerName: t('buildings.lastTestDate'),
      width: 150,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'actions',
      headerName: t('buildings.actions'),
      width: 150,
      headerAlign: 'right',
      align: 'right',
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleViewBuilding(params.row.id)}
          >
            {t('buildings.view')}
          </Button>
          <Button
            size="small"
            variant="text"
            onClick={() => handleViewTests(params.row.id)}
          >
            {t('buildings.viewTests')}
          </Button>
        </Box>
      ),
    },
  ];

  const handleAddBuilding = () => {
    console.log('Add building');
  };

  const handleViewBuilding = (id: string) => {
    console.log('View building:', id);
  };

  const handleViewTests = (id: string) => {
    console.log('View tests for building:', id);
  };

  const filteredBuildings = buildings.filter((building) => {
    const matchesSearch = 
      building.buildingName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      building.buildingCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      building.managerName.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = !statusFilter || building.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {t('buildings.title')}
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAddBuilding}
        >
          {t('buildings.addBuilding')}
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            placeholder={t('common.search')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ minWidth: 300 }}
          />
          
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>{t('buildings.status')}</InputLabel>
            <Select
              value={statusFilter}
              label={t('buildings.status')}
              onChange={(e) => setStatusFilter(e.target.value as BuildingStatus | '')}
            >
              <MenuItem value="">
                <em>הכל</em>
              </MenuItem>
              <MenuItem value="active">{t('buildings.active')}</MenuItem>
              <MenuItem value="inactive">{t('buildings.inactive')}</MenuItem>
            </Select>
          </FormControl>
          
          <Button
            variant="outlined"
            startIcon={<FilterListIcon />}
          >
            {t('common.filter')}
          </Button>
        </Box>
      </Paper>

      <Paper sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={filteredBuildings}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: { page: 0, pageSize: 10 },
            },
          }}
          pageSizeOptions={[5, 10, 25]}
          checkboxSelection
          disableRowSelectionOnClick
          localeText={{
            // RTL DataGrid localization
            noRowsLabel: 'אין נתונים להצגה',
            noResultsOverlayLabel: 'לא נמצאו תוצאות',
            footerRowSelected: (count) => `${count} שורות נבחרו`,
            footerPaginationRowsPerPage: 'שורות בעמוד:',
            footerPaginationOf: 'מתוך',
          }}
        />
      </Paper>
    </Box>
  );
};

export default BuildingsPage;