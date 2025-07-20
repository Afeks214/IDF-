# Hebrew RTL Dashboard Components

This directory contains the Hebrew RTL dashboard components for the IDF Testing Infrastructure system.

## Components Overview

### 1. ReadinessDashboard.tsx
Main dashboard component that displays building readiness statistics with Hebrew RTL support.

**Features:**
- 4 interactive pie charts for different readiness categories
- Real-time data updates every 30 seconds
- Building-floor hierarchical structure
- PostgreSQL connection with 494 records
- Responsive design with Material-UI
- Hebrew translations with right-to-left support

**Readiness Categories:**
1. **כשירות מבנה** (Building Readiness) - Overall building condition
2. **כשירות כללי** (General Readiness) - General operational status
3. **כשירות הנדסי** (Engineering Readiness) - Engineering/structural condition
4. **כשירות תפעולי** (Operational Readiness) - Operational capacity

### 2. ReadinessPieChart.tsx
Reusable pie chart component using Recharts library.

**Features:**
- Interactive pie chart with click handlers
- Custom Hebrew RTL tooltips
- Responsive design
- Color-coded segments
- Percentage labels

### 3. BuildingFloorHierarchy.tsx
Component for displaying building and floor structure.

**Features:**
- Hierarchical building/floor display
- Click handlers for navigation
- Readiness scores per floor
- Manager information
- Last inspection dates

## API Integration

The dashboard connects to PostgreSQL through the `dashboardApi` service:

```typescript
// Get dashboard statistics
const stats = await dashboardApi.getDashboardStats();

// Get readiness data for all 4 categories
const readinessData = await dashboardApi.getReadinessData();

// Get building hierarchy
const buildings = await dashboardApi.getBuildingHierarchy();
```

## Real-time Updates

The dashboard supports real-time updates using the `useRealtimeUpdates` hook:

```typescript
const { isConnected, lastUpdate, forceUpdate } = useRealtimeUpdates({
  enabled: true,
  interval: 30000, // 30 seconds
  onUpdate: (data) => {
    // Handle real-time data update
  },
  onError: (error) => {
    // Handle update errors
  }
});
```

## Hebrew RTL Support

The dashboard is fully internationalized with Hebrew RTL support:

- Uses `react-i18next` for translations
- RTL layout support with Material-UI
- Hebrew date/time formatting
- Right-to-left text alignment
- Hebrew font support

## Data Structure

The dashboard works with the following data structures:

```typescript
interface ReadinessData {
  name: string;
  value: number;
  color: string;
  total?: number;
}

interface BuildingData {
  id: string;
  name: string;
  code: string;
  totalFloors: number;
  overallReadiness: number;
  manager: string;
  lastUpdate: string;
  floors: FloorData[];
}

interface DashboardStats {
  totalBuildings: number;
  totalTests: number;
  pendingTests: number;
  completedTests: number;
  totalRecords: number; // Always 494
  lastUpdateTime: string;
}
```

## Usage

```typescript
import ReadinessDashboard from './components/dashboard/ReadinessDashboard';

function DashboardPage() {
  return (
    <ReadinessDashboard
      onRefresh={handleRefresh}
      isLoading={false}
    />
  );
}
```

## Performance Optimizations

- **Lazy loading**: Components use React.lazy for code splitting
- **Memoization**: Expensive calculations are memoized
- **Virtualization**: Long lists use virtual scrolling
- **Debounced updates**: API calls are debounced to prevent excessive requests
- **Cache strategy**: API responses are cached for 5 minutes

## Accessibility

- Full keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Hebrew screen reader support
- ARIA labels and roles

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Dependencies

- React 18+
- Material-UI 5+
- Recharts 2.10+
- react-i18next 14+
- TypeScript 5+

## Security

- API calls use JWT authentication
- Input validation and sanitization
- XSS protection
- CSRF protection
- Rate limiting on API endpoints