import { useMemo } from 'react';
import { 
  DataRow, 
  Column, 
  FilterCondition, 
  SortConfig, 
  SearchConfig,
  PaginationConfig
} from '../types';

interface UseVirtualizationProps {
  data: DataRow[];
  columns: Column[];
  filters: FilterCondition[];
  search: SearchConfig;
  sort: SortConfig[];
  pagination: PaginationConfig;
  virtual: boolean;
}

export const useVirtualization = ({
  data,
  columns,
  filters,
  search,
  sort,
  pagination,
  virtual
}: UseVirtualizationProps) => {
  
  // Filter data based on filters and search
  const filteredData = useMemo(() => {
    let result = [...data];

    // Apply filters
    if (filters.length > 0) {
      result = result.filter(row => {
        return filters.every(filter => {
          const value = row[filter.column];
          return applyFilter(value, filter);
        });
      });
    }

    // Apply search
    if (search.query.trim()) {
      const query = search.caseSensitive ? search.query : search.query.toLowerCase();
      const searchRegex = search.regex ? new RegExp(query, search.caseSensitive ? 'g' : 'gi') : null;

      result = result.filter(row => {
        return search.columns.some(columnId => {
          const value = row[columnId];
          if (value === null || value === undefined) return false;
          
          const stringValue = search.caseSensitive ? 
            value.toString() : 
            value.toString().toLowerCase();

          if (search.regex && searchRegex) {
            return searchRegex.test(stringValue);
          } else if (search.wholeWord) {
            const words = stringValue.split(/\s+/);
            return words.some(word => word === query);
          } else {
            return stringValue.includes(query);
          }
        });
      });
    }

    return result;
  }, [data, filters, search]);

  // Sort data
  const sortedData = useMemo(() => {
    if (sort.length === 0) return filteredData;

    return [...filteredData].sort((a, b) => {
      for (const sortConfig of sort) {
        const column = columns.find(c => c.id === sortConfig.column);
        if (!column) continue;

        const aValue = a[sortConfig.column];
        const bValue = b[sortConfig.column];

        const comparison = compareValues(aValue, bValue, column.type);
        
        if (comparison !== 0) {
          return sortConfig.direction === 'asc' ? comparison : -comparison;
        }
      }
      return 0;
    });
  }, [filteredData, sort, columns]);

  // Paginate data (for non-virtual mode)
  const paginatedData = useMemo(() => {
    if (virtual) return sortedData;

    const startIndex = (pagination.page - 1) * pagination.pageSize;
    const endIndex = startIndex + pagination.pageSize;
    return sortedData.slice(startIndex, endIndex);
  }, [sortedData, pagination, virtual]);

  // Calculate column widths based on content
  const columnWidths = useMemo(() => {
    return columns.map(column => {
      if (column.width) return column.width;

      // Calculate width based on column type and content
      let baseWidth = 120;
      
      switch (column.type) {
        case 'boolean':
          baseWidth = 80;
          break;
        case 'number':
          baseWidth = 100;
          break;
        case 'date':
          baseWidth = 120;
          break;
        case 'email':
          baseWidth = 200;
          break;
        case 'url':
          baseWidth = 250;
          break;
        default:
          // Calculate based on header length and sample data
          const headerWidth = column.label.length * 8 + 40;
          const sampleData = paginatedData.slice(0, 10);
          const maxContentWidth = Math.max(
            ...sampleData.map(row => {
              const value = row[column.id];
              return value ? value.toString().length * 8 : 0;
            })
          );
          baseWidth = Math.max(headerWidth, Math.min(maxContentWidth + 20, 300));
      }

      return baseWidth;
    });
  }, [columns, paginatedData]);

  // Row height (can be dynamic based on content)
  const rowHeight = useMemo(() => {
    // Check if any rows have multi-line content
    const hasMultilineContent = paginatedData.some(row => 
      columns.some(column => {
        const value = row[column.id];
        return value && value.toString().length > 100;
      })
    );

    return hasMultilineContent ? 40 : 32;
  }, [paginatedData, columns]);

  // Total height for virtual scrolling
  const totalHeight = useMemo(() => {
    return (paginatedData.length + 1) * rowHeight; // +1 for header
  }, [paginatedData.length, rowHeight]);

  // Get item data for react-window
  const getItemData = () => {
    return {
      data: paginatedData,
      columns,
      rowHeight,
      columnWidths
    };
  };

  return {
    visibleData: paginatedData,
    filteredData,
    sortedData,
    totalHeight,
    rowHeight,
    columnWidths,
    getItemData
  };
};

// Helper function to apply a single filter
const applyFilter = (value: any, filter: FilterCondition): boolean => {
  switch (filter.operator) {
    case 'equals':
      return value === filter.value;
    
    case 'contains':
      if (value === null || value === undefined) return false;
      return value.toString().toLowerCase().includes(filter.value.toLowerCase());
    
    case 'startsWith':
      if (value === null || value === undefined) return false;
      return value.toString().toLowerCase().startsWith(filter.value.toLowerCase());
    
    case 'endsWith':
      if (value === null || value === undefined) return false;
      return value.toString().toLowerCase().endsWith(filter.value.toLowerCase());
    
    case 'greaterThan':
      if (value === null || value === undefined) return false;
      return Number(value) > Number(filter.value);
    
    case 'lessThan':
      if (value === null || value === undefined) return false;
      return Number(value) < Number(filter.value);
    
    case 'between':
      if (value === null || value === undefined) return false;
      const num = Number(value);
      return num >= Number(filter.value) && num <= Number(filter.value2);
    
    case 'in':
      if (!Array.isArray(filter.value)) return false;
      return filter.value.includes(value);
    
    case 'isEmpty':
      return value === null || value === undefined || value === '';
    
    case 'isNotEmpty':
      return value !== null && value !== undefined && value !== '';
    
    default:
      return true;
  }
};

// Helper function to compare values for sorting
const compareValues = (a: any, b: any, type: string): number => {
  // Handle null/undefined values
  if (a === null || a === undefined) {
    if (b === null || b === undefined) return 0;
    return -1;
  }
  if (b === null || b === undefined) {
    return 1;
  }

  switch (type) {
    case 'number':
      return Number(a) - Number(b);
    
    case 'date':
      const dateA = new Date(a);
      const dateB = new Date(b);
      return dateA.getTime() - dateB.getTime();
    
    case 'boolean':
      return Number(a) - Number(b);
    
    default:
      // String comparison with Hebrew support
      return a.toString().localeCompare(b.toString(), 'he');
  }
};