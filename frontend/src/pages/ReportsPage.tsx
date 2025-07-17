import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Card,
  CardContent,
  Divider,
  Chip,
} from '@mui/material';
import {
  FileDownload as FileDownloadIcon,
  Assessment as AssessmentIcon,
  PictureAsPdf as PdfIcon,
  TableChart as ExcelIcon,
  Description as CsvIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs, { Dayjs } from 'dayjs';
import { useTranslation } from 'react-i18next';
import { ExportFormat, TestType, TestStatus } from '../types';

export const ReportsPage: React.FC = () => {
  const { t } = useTranslation();
  const [fromDate, setFromDate] = useState<Dayjs | null>(dayjs().subtract(1, 'month'));
  const [toDate, setToDate] = useState<Dayjs | null>(dayjs());
  const [selectedBuildings, setSelectedBuildings] = useState<string[]>([]);
  const [selectedTestTypes, setSelectedTestTypes] = useState<TestType[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<TestStatus[]>([]);
  const [reportFormat, setReportFormat] = useState<ExportFormat>('pdf');

  // Mock data
  const buildings = [
    { id: '1', name: 'מבנה 40', code: '40' },
    { id: '2', name: 'מבנה 25', code: '25' },
    { id: '3', name: 'מבנה 67', code: '67' },
  ];

  const reportTemplates = [
    {
      id: 'monthly',
      title: 'דוח חודשי',
      description: 'סיכום פעילות בדיקות חודשית',
      icon: <AssessmentIcon />,
    },
    {
      id: 'building-status',
      title: 'סטטוס מבנים',
      description: 'מצב נוכחי של כל המבנים',
      icon: <AssessmentIcon />,
    },
    {
      id: 'failed-tests',
      title: 'בדיקות שנכשלו',
      description: 'רשימת בדיקות שדרושות תיקון',
      icon: <AssessmentIcon />,
    },
    {
      id: 'pending-tests',
      title: 'בדיקות ממתינות',
      description: 'בדיקות שעדיין לא בוצעו',
      icon: <AssessmentIcon />,
    },
  ];

  const handleGenerateReport = () => {
    console.log('Generate report with filters:', {
      fromDate: fromDate?.format('YYYY-MM-DD'),
      toDate: toDate?.format('YYYY-MM-DD'),
      buildings: selectedBuildings,
      testTypes: selectedTestTypes,
      statuses: selectedStatuses,
      format: reportFormat,
    });
  };

  const handleQuickReport = (templateId: string) => {
    console.log('Generate quick report:', templateId);
  };

  const getFormatIcon = (format: ExportFormat) => {
    switch (format) {
      case 'pdf':
        return <PdfIcon />;
      case 'excel':
        return <ExcelIcon />;
      case 'csv':
        return <CsvIcon />;
      default:
        return <FileDownloadIcon />;
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('reports.title')}
        </Typography>

        <Grid container spacing={3}>
          {/* Quick Reports */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                דוחות מהירים
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {reportTemplates.map((template) => (
                  <Card
                    key={template.id}
                    sx={{
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        boxShadow: 2,
                        transform: 'translateY(-2px)',
                      },
                    }}
                    onClick={() => handleQuickReport(template.id)}
                  >
                    <CardContent sx={{ p: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Box sx={{ color: 'primary.main' }}>
                          {template.icon}
                        </Box>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="subtitle2" fontWeight="bold">
                            {template.title}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {template.description}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            </Paper>
          </Grid>

          {/* Custom Report Generator */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                {t('reports.generateReport')}
              </Typography>
              
              <Grid container spacing={3}>
                {/* Date Range */}
                <Grid item xs={12} sm={6}>
                  <DatePicker
                    label={t('reports.fromDate')}
                    value={fromDate}
                    onChange={setFromDate}
                    slotProps={{
                      textField: { fullWidth: true },
                    }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <DatePicker
                    label={t('reports.toDate')}
                    value={toDate}
                    onChange={setToDate}
                    slotProps={{
                      textField: { fullWidth: true },
                    }}
                  />
                </Grid>

                {/* Buildings Selection */}
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>{t('reports.selectBuildings')}</InputLabel>
                    <Select
                      multiple
                      value={selectedBuildings}
                      onChange={(e) => setSelectedBuildings(e.target.value as string[])}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {selected.map((value) => {
                            const building = buildings.find(b => b.id === value);
                            return (
                              <Chip
                                key={value}
                                label={building?.name || value}
                                size="small"
                              />
                            );
                          })}
                        </Box>
                      )}
                    >
                      {buildings.map((building) => (
                        <MenuItem key={building.id} value={building.id}>
                          {building.name} ({building.code})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                {/* Test Types Selection */}
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>{t('reports.selectTestTypes')}</InputLabel>
                    <Select
                      multiple
                      value={selectedTestTypes}
                      onChange={(e) => setSelectedTestTypes(e.target.value as TestType[])}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {selected.map((value) => (
                            <Chip
                              key={value}
                              label={t(`tests.testTypes.${value}`)}
                              size="small"
                            />
                          ))}
                        </Box>
                      )}
                    >
                      <MenuItem value="engineering">{t('tests.testTypes.engineering')}</MenuItem>
                      <MenuItem value="security">{t('tests.testTypes.security')}</MenuItem>
                      <MenuItem value="safety">{t('tests.testTypes.safety')}</MenuItem>
                      <MenuItem value="operational">{t('tests.testTypes.operational')}</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                {/* Test Status Selection */}
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>סטטוס בדיקות</InputLabel>
                    <Select
                      multiple
                      value={selectedStatuses}
                      onChange={(e) => setSelectedStatuses(e.target.value as TestStatus[])}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {selected.map((value) => (
                            <Chip
                              key={value}
                              label={t(`tests.${value}`)}
                              size="small"
                            />
                          ))}
                        </Box>
                      )}
                    >
                      <MenuItem value="pending">{t('tests.pending')}</MenuItem>
                      <MenuItem value="inProgress">{t('tests.inProgress')}</MenuItem>
                      <MenuItem value="completed">{t('tests.completed')}</MenuItem>
                      <MenuItem value="failed">{t('tests.failed')}</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                {/* Report Format */}
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>{t('reports.reportFormat')}</InputLabel>
                    <Select
                      value={reportFormat}
                      onChange={(e) => setReportFormat(e.target.value as ExportFormat)}
                    >
                      <MenuItem value="pdf">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <PdfIcon fontSize="small" />
                          {t('reports.pdf')}
                        </Box>
                      </MenuItem>
                      <MenuItem value="excel">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <ExcelIcon fontSize="small" />
                          {t('reports.excel')}
                        </Box>
                      </MenuItem>
                      <MenuItem value="csv">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <CsvIcon fontSize="small" />
                          {t('reports.csv')}
                        </Box>
                      </MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12}>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={getFormatIcon(reportFormat)}
                      onClick={handleGenerateReport}
                    >
                      {t('reports.generateReport')}
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </LocalizationProvider>
  );
};

export default ReportsPage;