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
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  FilterList as FilterListIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { useTranslation } from 'react-i18next';
import { TestRecord, TestStatus, TestType } from '../types';

export const TestsPage: React.FC = () => {
  const { t } = useTranslation();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<TestStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState<TestType | ''>('');

  // Mock data - in real app this would come from API
  const tests: TestRecord[] = [
    {
      id: '1',
      buildingId: '1',
      testType: 'engineering',
      testLeader: 'יגאל גזמן',
      testRound: 1,
      testDate: '2025-07-20',
      status: 'pending',
      reportDistributed: false,
      retestRequired: false,
      notes: 'בדיקה ראשונית',
      createdAt: '2025-07-17',
      updatedAt: '2025-07-17',
    },
    {
      id: '2',
      buildingId: '1',
      testType: 'security',
      testLeader: 'אמיר לוי',
      testRound: 2,
      testDate: '2025-07-15',
      status: 'completed',
      results: 'הבדיקה עברה בהצלחה',
      reportDistributed: true,
      retestRequired: false,
      createdAt: '2025-07-10',
      updatedAt: '2025-07-15',
    },
    {
      id: '3',
      buildingId: '2',
      testType: 'safety',
      testLeader: 'שרה כהן',
      testRound: 1,
      testDate: '2025-07-12',
      status: 'failed',
      results: 'נמצאו ליקויים בבטיחות',
      reportDistributed: false,
      retestRequired: true,
      notes: 'נדרשת תיקון דחוף',
      createdAt: '2025-07-08',
      updatedAt: '2025-07-12',
    },
    {
      id: '4',
      buildingId: '3',
      testType: 'operational',
      testLeader: 'דוד שמש',
      testRound: 1,
      testDate: '2025-07-18',
      status: 'inProgress',
      reportDistributed: false,
      retestRequired: false,
      notes: 'בדיקה בתהליך',
      createdAt: '2025-07-16',
      updatedAt: '2025-07-18',
    },
  ];

  const getStatusColor = (status: TestStatus) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'inProgress':
        return 'info';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'id',
      headerName: 'מזהה',
      width: 80,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'testType',
      headerName: t('tests.testType'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
      renderCell: (params: GridRenderCellParams) => (
        t(`tests.testTypes.${params.value}`)
      ),
    },
    {
      field: 'testLeader',
      headerName: t('tests.testLeader'),
      width: 150,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'testRound',
      headerName: t('tests.testRound'),
      width: 100,
      headerAlign: 'right',
      align: 'right',
      type: 'number',
    },
    {
      field: 'testDate',
      headerName: t('tests.testDate'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
    },
    {
      field: 'status',
      headerName: t('tests.status'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={t(`tests.${params.value}`)}
          color={getStatusColor(params.value as TestStatus) as any}
          size="small"
        />
      ),
    },
    {
      field: 'reportDistributed',
      headerName: t('tests.reportDistributed'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
      type: 'boolean',
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value ? t('common.yes') : t('common.no')}
          color={params.value ? 'success' : 'default'}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'retestRequired',
      headerName: t('tests.retestRequired'),
      width: 120,
      headerAlign: 'right',
      align: 'right',
      type: 'boolean',
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value ? t('common.yes') : t('common.no')}
          color={params.value ? 'warning' : 'success'}
          size="small"
          variant="outlined"
        />
      ),
    },
    {
      field: 'actions',
      headerName: 'פעולות',
      width: 150,
      headerAlign: 'right',
      align: 'right',
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() => handleViewTest(params.row.id)}
          >
            {t('common.edit')}
          </Button>
          <Button
            size="small"
            variant="text"
            onClick={() => handleViewTest(params.row.id)}
          >
            צפה
          </Button>
        </Box>
      ),
    },
  ];

  const handleAddTest = () => {
    console.log('Add test');
  };

  const handleViewTest = (id: string) => {
    console.log('View test:', id);
  };

  const filteredTests = tests.filter((test) => {
    const matchesSearch = 
      test.testLeader.toLowerCase().includes(searchTerm.toLowerCase()) ||
      test.id.includes(searchTerm) ||
      (test.notes && test.notes.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesStatus = !statusFilter || test.status === statusFilter;
    const matchesType = !typeFilter || test.testType === typeFilter;
    
    return matchesSearch && matchesStatus && matchesType;
  });

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          {t('tests.title')}
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAddTest}
        >
          {t('tests.addTest')}
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
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
            sx={{ minWidth: 250 }}
          />
          
          <FormControl sx={{ minWidth: 120 }}>
            <InputLabel>{t('tests.status')}</InputLabel>
            <Select
              value={statusFilter}
              label={t('tests.status')}
              onChange={(e) => setStatusFilter(e.target.value as TestStatus | '')}
            >
              <MenuItem value="">
                <em>הכל</em>
              </MenuItem>
              <MenuItem value="pending">{t('tests.pending')}</MenuItem>
              <MenuItem value="inProgress">{t('tests.inProgress')}</MenuItem>
              <MenuItem value="completed">{t('tests.completed')}</MenuItem>
              <MenuItem value="failed">{t('tests.failed')}</MenuItem>
            </Select>
          </FormControl>

          <FormControl sx={{ minWidth: 120 }}>
            <InputLabel>{t('tests.testType')}</InputLabel>
            <Select
              value={typeFilter}
              label={t('tests.testType')}
              onChange={(e) => setTypeFilter(e.target.value as TestType | '')}
            >
              <MenuItem value="">
                <em>הכל</em>
              </MenuItem>
              <MenuItem value="engineering">{t('tests.testTypes.engineering')}</MenuItem>
              <MenuItem value="security">{t('tests.testTypes.security')}</MenuItem>
              <MenuItem value="safety">{t('tests.testTypes.safety')}</MenuItem>
              <MenuItem value="operational">{t('tests.testTypes.operational')}</MenuItem>
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
          rows={filteredTests}
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

export default TestsPage;