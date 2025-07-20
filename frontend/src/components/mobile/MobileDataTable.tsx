import React, { useState, useRef, useEffect } from 'react';
import { useSwipeGesture } from '../../hooks/useMobile';
import { usePWA } from '../pwa/PWAProvider';

interface Column {
  key: string;
  label: string;
  width?: number;
  render?: (value: any, row: any) => React.ReactNode;
  sortable?: boolean;
  filterable?: boolean;
}

interface MobileDataTableProps {
  data: any[];
  columns: Column[];
  onRowClick?: (row: any) => void;
  onCellEdit?: (rowIndex: number, columnKey: string, value: any) => void;
  className?: string;
  showSearch?: boolean;
  showFilter?: boolean;
  virtualScroll?: boolean;
  pageSize?: number;
}

const MobileDataTable: React.FC<MobileDataTableProps> = ({
  data,
  columns,
  onRowClick,
  onCellEdit,
  className = '',
  showSearch = true,
  showFilter = false,
  virtualScroll = false,
  pageSize = 50
}) => {
  const { isMobile, touchSupport } = usePWA();
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(0);
  const [selectedRow, setSelectedRow] = useState<number | null>(null);
  const [editingCell, setEditingCell] = useState<{row: number, column: string} | null>(null);
  const [scrollPosition, setScrollPosition] = useState({ x: 0, y: 0 });
  
  const tableRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);

  // Filter data based on search term
  const filteredData = data.filter(row => {
    if (!searchTerm) return true;
    return Object.values(row).some(value =>
      String(value).toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  // Sort data
  const sortedData = [...filteredData].sort((a, b) => {
    if (!sortColumn) return 0;
    
    const aValue = a[sortColumn];
    const bValue = b[sortColumn];
    
    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  // Paginate data
  const paginatedData = virtualScroll 
    ? sortedData 
    : sortedData.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  // Handle column sort
  const handleSort = (columnKey: string) => {
    if (sortColumn === columnKey) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnKey);
      setSortDirection('asc');
    }
  };

  // Handle cell edit
  const handleCellClick = (rowIndex: number, columnKey: string, value: any) => {
    if (onCellEdit) {
      setEditingCell({ row: rowIndex, column: columnKey });
    }
  };

  // Handle cell edit complete
  const handleCellEditComplete = (newValue: any) => {
    if (editingCell && onCellEdit) {
      onCellEdit(editingCell.row, editingCell.column, newValue);
    }
    setEditingCell(null);
  };

  // Swipe gesture for navigation
  const swipeHandlers = useSwipeGesture(
    () => {
      // Swipe left - next page
      if (currentPage < Math.ceil(filteredData.length / pageSize) - 1) {
        setCurrentPage(currentPage + 1);
      }
    },
    () => {
      // Swipe right - previous page
      if (currentPage > 0) {
        setCurrentPage(currentPage - 1);
      }
    }
  );

  // Handle horizontal scroll sync
  useEffect(() => {
    const handleScroll = () => {
      if (tableRef.current && headerRef.current) {
        const scrollLeft = tableRef.current.scrollLeft;
        headerRef.current.scrollLeft = scrollLeft;
      }
    };

    const tableElement = tableRef.current;
    if (tableElement) {
      tableElement.addEventListener('scroll', handleScroll);
      return () => tableElement.removeEventListener('scroll', handleScroll);
    }
  }, []);

  // Mobile-optimized cell component
  const MobileCell: React.FC<{
    value: any;
    row: any;
    column: Column;
    rowIndex: number;
    isEditing: boolean;
    onClick: () => void;
  }> = ({ value, row, column, rowIndex, isEditing, onClick }) => {
    const [editValue, setEditValue] = useState(value);

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleCellEditComplete(editValue);
      } else if (e.key === 'Escape') {
        setEditValue(value);
        setEditingCell(null);
      }
    };

    if (isEditing) {
      return (
        <div className="mobile-data-table-cell editing">
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={() => handleCellEditComplete(editValue)}
            onKeyDown={handleKeyDown}
            className="mobile-input"
            autoFocus
            style={{ fontSize: '16px' }} // Prevent zoom on iOS
          />
        </div>
      );
    }

    return (
      <div
        className={`mobile-data-table-cell ${touchSupport ? 'touch-target' : ''}`}
        onClick={onClick}
        style={{ minWidth: column.width }}
      >
        {column.render ? column.render(value, row) : value}
      </div>
    );
  };

  return (
    <div className={`mobile-data-table-container ${className}`}>
      {/* Search and Controls */}
      {showSearch && (
        <div className="mobile-padding">
          <div className="mobile-search-controls">
            <input
              type="search"
              placeholder="חיפוש..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="mobile-input"
              style={{ fontSize: '16px' }}
            />
            {filteredData.length > 0 && (
              <div className="text-sm text-gray-500 mt-2">
                {filteredData.length} תוצאות
              </div>
            )}
          </div>
        </div>
      )}

      {/* Table Header */}
      <div className="table-container" ref={headerRef}>
        <div className="mobile-data-table-header">
          {columns.map((column) => (
            <div
              key={column.key}
              className={`mobile-data-table-header-cell ${column.sortable ? 'sortable' : ''}`}
              onClick={() => column.sortable && handleSort(column.key)}
              style={{ minWidth: column.width }}
            >
              <span>{column.label}</span>
              {column.sortable && sortColumn === column.key && (
                <span className="sort-indicator">
                  {sortDirection === 'asc' ? '↑' : '↓'}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Table Body */}
      <div 
        className="table-container mobile-data-table-body" 
        ref={tableRef}
        {...(touchSupport ? swipeHandlers : {})}
      >
        {paginatedData.map((row, rowIndex) => (
          <div
            key={rowIndex}
            className={`mobile-data-table-row ${selectedRow === rowIndex ? 'selected' : ''}`}
            onClick={() => {
              setSelectedRow(rowIndex);
              onRowClick?.(row);
            }}
          >
            {columns.map((column) => {
              const isEditing = editingCell?.row === rowIndex && editingCell?.column === column.key;
              return (
                <MobileCell
                  key={column.key}
                  value={row[column.key]}
                  row={row}
                  column={column}
                  rowIndex={rowIndex}
                  isEditing={isEditing}
                  onClick={() => handleCellClick(rowIndex, column.key, row[column.key])}
                />
              );
            })}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {!virtualScroll && Math.ceil(filteredData.length / pageSize) > 1 && (
        <div className="mobile-pagination">
          <div className="flex items-center justify-between mobile-padding">
            <button
              onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
              disabled={currentPage === 0}
              className="mobile-btn bg-gray-200 text-gray-700 disabled:opacity-50"
            >
              הקודם
            </button>
            
            <span className="text-sm text-gray-600">
              עמוד {currentPage + 1} מתוך {Math.ceil(filteredData.length / pageSize)}
            </span>
            
            <button
              onClick={() => setCurrentPage(Math.min(Math.ceil(filteredData.length / pageSize) - 1, currentPage + 1))}
              disabled={currentPage >= Math.ceil(filteredData.length / pageSize) - 1}
              className="mobile-btn bg-gray-200 text-gray-700 disabled:opacity-50"
            >
              הבא
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {data.length === 0 && (
        <div className="mobile-loading">
          <div className="mobile-spinner" />
          <span>טוען נתונים...</span>
        </div>
      )}

      {/* Empty State */}
      {filteredData.length === 0 && data.length > 0 && (
        <div className="mobile-empty-state mobile-padding">
          <div className="text-center py-8">
            <span className="text-4xl mb-4 block">🔍</span>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              לא נמצאו תוצאות
            </h3>
            <p className="text-gray-600">
              נסה לשנות את מונחי החיפוש
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MobileDataTable;