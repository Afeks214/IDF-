# IDF Data Management UI

Advanced data management interface with Excel-like functionality and comprehensive Hebrew RTL support.

## Features

### 🔥 Core Capabilities
- **Advanced Data Table**: Excel-like interface with virtualization for large datasets
- **Hebrew RTL Support**: Full right-to-left layout and Hebrew text optimization
- **Inline Editing**: Real-time cell editing with validation
- **Advanced Search & Filtering**: Multi-condition filters with regex support
- **Excel Import/Export**: Full Excel compatibility with preview and mapping
- **Bulk Operations**: Select and perform actions on multiple rows
- **Real-time Updates**: Live data synchronization
- **Keyboard Navigation**: Excel-like keyboard shortcuts and navigation

### 📊 Data Management
- **Multiple Export Formats**: Excel, CSV, PDF, JSON
- **Smart Column Mapping**: Auto-detect column mappings during import
- **Data Validation**: Type checking and custom validation rules
- **Undo/Redo**: Complete operation history with unlimited undo
- **Column Aggregation**: Sum, average, count, min/max calculations
- **Saved Filters**: Save and reuse complex filter combinations

### 🎨 User Experience
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark/Light Themes**: User preference support
- **Performance Optimized**: Virtual scrolling for 100k+ rows
- **Accessibility**: WCAG 2.1 AA compliant
- **Customizable UI**: Adjustable column widths, row heights, and layouts

## Technology Stack

- **React 18**: Modern React with hooks and concurrent features
- **TypeScript**: Full type safety and IntelliSense
- **TanStack Table**: Powerful table library with virtualization
- **TanStack Query**: Server state management
- **Tailwind CSS**: Utility-first CSS framework
- **React Window**: Virtual scrolling for performance
- **React Hook Form**: Form state management
- **Date-fns**: Date manipulation and formatting
- **Lucide React**: Modern icon library

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Environment Variables

Create a `.env` file in the root directory:

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── DataTable/      # Advanced data table components
│   ├── Search/         # Search and filtering components
│   ├── Excel/          # Import/export functionality
│   └── Charts/         # Data visualization components
├── hooks/              # Custom React hooks
├── services/           # API and external service integrations
├── types/              # TypeScript type definitions
├── utils/              # Utility functions and helpers
├── styles/             # Global styles and themes
└── pages/              # Page components and routing
```

## Key Components

### DataTable
The main data table component with advanced features:

```tsx
<DataTable
  data={data}
  columns={columns}
  editable={true}
  selectable={true}
  virtual={true}
  onCellEdit={handleCellEdit}
  onRowSelect={handleRowSelect}
  rtl={true}
/>
```

### AdvancedSearch
Comprehensive search and filtering interface:

```tsx
<AdvancedSearch
  columns={columns}
  searchConfig={searchConfig}
  filters={filters}
  onSearchChange={handleSearchChange}
  onFiltersChange={handleFiltersChange}
  rtl={true}
/>
```

### ExcelImportExport
Excel file handling with preview and mapping:

```tsx
<ExcelImportExport
  columns={columns}
  data={data}
  onImportComplete={handleImport}
  onExportComplete={handleExport}
  rtl={true}
/>
```

## Hebrew RTL Support

This application provides comprehensive Hebrew and RTL support:

- **Layout Direction**: All components respect RTL layout
- **Text Alignment**: Proper text alignment for Hebrew content  
- **Font Optimization**: Optimized Hebrew fonts (Heebo, Arial)
- **Keyboard Navigation**: RTL-aware keyboard navigation
- **Date/Number Formatting**: Hebrew locale formatting
- **Form Validation**: Hebrew error messages

## Performance Optimizations

- **Virtual Scrolling**: Handle 100k+ rows smoothly
- **Memoization**: Prevent unnecessary re-renders
- **Code Splitting**: Lazy load components
- **Bundle Optimization**: Tree shaking and compression
- **Image Optimization**: WebP support with fallbacks
- **Caching**: Smart API response caching

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Arrow Keys` | Navigate cells |
| `Enter` | Edit cell |
| `F2` | Edit cell |
| `Escape` | Cancel edit |
| `Tab` | Next cell |
| `Shift+Tab` | Previous cell |
| `Ctrl+C` | Copy cell |
| `Ctrl+V` | Paste cell |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+A` | Select all |
| `Ctrl+F` | Find |

## API Integration

The frontend integrates with the backend API for:

- **Data Operations**: CRUD operations on table data
- **File Upload**: Excel/CSV file processing
- **Real-time Updates**: WebSocket connections for live updates
- **User Preferences**: Save/load user settings
- **Export Generation**: Server-side export processing

## Testing

```bash
# Run unit tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run E2E tests
npm run test:e2e

# Run accessibility tests
npm run test:a11y
```

## Deployment

### Production Build
```bash
npm run build
```

### Docker Deployment
```bash
docker build -t idf-data-ui .
docker run -p 3000:80 idf-data-ui
```

### Environment-specific Builds
```bash
# Staging
npm run build:staging

# Production
npm run build:production
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Security Considerations

- **Input Validation**: All user inputs are validated
- **XSS Protection**: Sanitized HTML output
- **CSRF Protection**: CSRF tokens for state-changing operations
- **Authentication**: JWT-based authentication
- **Authorization**: Role-based access control

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation wiki