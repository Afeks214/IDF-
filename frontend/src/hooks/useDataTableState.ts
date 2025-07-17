import { useState, useCallback, useMemo, useEffect } from 'react';
import { 
  DataRow, 
  Column, 
  FilterCondition, 
  SortConfig, 
  PaginationConfig,
  SearchConfig,
  CellEdit,
  TableState,
  UndoRedoState
} from '../types';
import { areCellValuesEqual } from '../utils/cellUtils';

interface UseDataTableStateProps {
  data: DataRow[];
  columns: Column[];
  pageSize?: number;
  onCellEdit?: (edit: CellEdit) => void;
  onRowSelect?: (rowIds: string[]) => void;
  onSort?: (sort: SortConfig[]) => void;
  onFilter?: (filters: FilterCondition[]) => void;
}

export const useDataTableState = ({
  data,
  columns,
  pageSize = 50,
  onCellEdit,
  onRowSelect,
  onSort,
  onFilter
}: UseDataTableStateProps) => {
  // Main table state
  const [tableState, setTableState] = useState<TableState>({
    data,
    columns,
    filters: [],
    search: {
      query: '',
      columns: columns.map(c => c.id),
      caseSensitive: false,
      wholeWord: false,
      regex: false
    },
    sort: [],
    pagination: {
      page: 1,
      pageSize,
      total: data.length
    },
    selection: {
      selectedRows: [],
      selectedCells: [],
      selectAll: false
    },
    editing: {
      pendingChanges: []
    },
    loading: false
  });

  // Undo/Redo state
  const [undoRedoState, setUndoRedoState] = useState<UndoRedoState>({
    undoStack: [],
    redoStack: [],
    maxStackSize: 50
  });

  // Update data when props change
  useEffect(() => {
    setTableState(prev => ({
      ...prev,
      data,
      columns,
      pagination: {
        ...prev.pagination,
        total: data.length
      }
    }));
  }, [data, columns]);

  // Cell editing functions
  const updateCell = useCallback((rowId: string, columnId: string, newValue: any) => {
    const row = tableState.data.find(r => r.id === rowId);
    if (!row) return;

    const oldValue = row[columnId];
    
    // Check if value actually changed
    const column = tableState.columns.find(c => c.id === columnId);
    if (column && areCellValuesEqual(oldValue, newValue, column)) {
      return;
    }

    const edit: CellEdit = {
      rowId,
      columnId,
      value: newValue,
      oldValue,
      timestamp: new Date()
    };

    // Update table state
    setTableState(prev => ({
      ...prev,
      data: prev.data.map(row => 
        row.id === rowId ? { ...row, [columnId]: newValue } : row
      ),
      editing: {
        ...prev.editing,
        pendingChanges: [...prev.editing.pendingChanges, edit]
      }
    }));

    // Add to undo stack
    setUndoRedoState(prev => ({
      ...prev,
      undoStack: [...prev.undoStack.slice(-prev.maxStackSize + 1), edit],
      redoStack: [] // Clear redo stack when new edit is made
    }));

    // Call external handler
    onCellEdit?.(edit);
  }, [tableState.data, tableState.columns, onCellEdit]);

  const startCellEdit = useCallback((rowId: string, columnId: string) => {
    setTableState(prev => ({
      ...prev,
      editing: {
        ...prev.editing,
        activeCell: { rowId, columnId }
      }
    }));
  }, []);

  const finishCellEdit = useCallback(() => {
    setTableState(prev => ({
      ...prev,
      editing: {
        ...prev.editing,
        activeCell: undefined
      }
    }));
  }, []);

  const cancelCellEdit = useCallback(() => {
    setTableState(prev => ({
      ...prev,
      editing: {
        ...prev.editing,
        activeCell: undefined
      }
    }));
  }, []);

  // Selection functions
  const toggleRowSelection = useCallback((rowId: string) => {
    setTableState(prev => {
      const isSelected = prev.selection.selectedRows.includes(rowId);
      const newSelectedRows = isSelected
        ? prev.selection.selectedRows.filter(id => id !== rowId)
        : [...prev.selection.selectedRows, rowId];

      const newSelectAll = newSelectedRows.length === prev.data.length;

      const newSelection = {
        ...prev.selection,
        selectedRows: newSelectedRows,
        selectAll: newSelectAll
      };

      // Call external handler
      onRowSelect?.(newSelectedRows);

      return {
        ...prev,
        selection: newSelection
      };
    });
  }, [onRowSelect]);

  const toggleSelectAll = useCallback(() => {
    setTableState(prev => {
      const newSelectAll = !prev.selection.selectAll;
      const newSelectedRows = newSelectAll ? prev.data.map(row => row.id) : [];

      const newSelection = {
        ...prev.selection,
        selectedRows: newSelectedRows,
        selectAll: newSelectAll
      };

      // Call external handler
      onRowSelect?.(newSelectedRows);

      return {
        ...prev,
        selection: newSelection
      };
    });
  }, [onRowSelect]);

  const clearSelection = useCallback(() => {
    setTableState(prev => ({
      ...prev,
      selection: {
        selectedRows: [],
        selectedCells: [],
        selectAll: false
      }
    }));
    onRowSelect?.([]);
  }, [onRowSelect]);

  // Filter functions
  const updateFilters = useCallback((filters: FilterCondition[]) => {
    setTableState(prev => ({
      ...prev,
      filters,
      pagination: {
        ...prev.pagination,
        page: 1 // Reset to first page when filtering
      }
    }));
    onFilter?.(filters);
  }, [onFilter]);

  const addFilter = useCallback((filter: FilterCondition) => {
    setTableState(prev => {
      const newFilters = [...prev.filters, filter];
      onFilter?.(newFilters);
      return {
        ...prev,
        filters: newFilters,
        pagination: {
          ...prev.pagination,
          page: 1
        }
      };
    });
  }, [onFilter]);

  const removeFilter = useCallback((filterId: string) => {
    setTableState(prev => {
      const newFilters = prev.filters.filter(f => f.id !== filterId);
      onFilter?.(newFilters);
      return {
        ...prev,
        filters: newFilters,
        pagination: {
          ...prev.pagination,
          page: 1
        }
      };
    });
  }, [onFilter]);

  // Search functions
  const updateSearch = useCallback((search: SearchConfig) => {
    setTableState(prev => ({
      ...prev,
      search,
      pagination: {
        ...prev.pagination,
        page: 1 // Reset to first page when searching
      }
    }));
  }, []);

  // Sort functions
  const updateSort = useCallback((columnId: string, direction: 'asc' | 'desc' | null) => {
    setTableState(prev => {
      let newSort: SortConfig[];
      
      if (direction === null) {
        // Remove sort for this column
        newSort = prev.sort.filter(s => s.column !== columnId);
      } else {
        // Update or add sort for this column
        const existingIndex = prev.sort.findIndex(s => s.column === columnId);
        if (existingIndex >= 0) {
          newSort = prev.sort.map((s, i) => 
            i === existingIndex ? { column: columnId, direction } : s
          );
        } else {
          newSort = [...prev.sort, { column: columnId, direction }];
        }
      }

      onSort?.(newSort);

      return {
        ...prev,
        sort: newSort
      };
    });
  }, [onSort]);

  const clearSort = useCallback(() => {
    setTableState(prev => ({
      ...prev,
      sort: []
    }));
    onSort?.([]);
  }, [onSort]);

  // Pagination functions
  const updatePagination = useCallback((pagination: PaginationConfig) => {
    setTableState(prev => ({
      ...prev,
      pagination
    }));
  }, []);

  // Undo/Redo functions
  const undo = useCallback(() => {
    if (undoRedoState.undoStack.length === 0) return;

    const lastEdit = undoRedoState.undoStack[undoRedoState.undoStack.length - 1];
    
    // Revert the change
    setTableState(prev => ({
      ...prev,
      data: prev.data.map(row => 
        row.id === lastEdit.rowId 
          ? { ...row, [lastEdit.columnId]: lastEdit.oldValue }
          : row
      )
    }));

    // Update undo/redo stacks
    setUndoRedoState(prev => ({
      ...prev,
      undoStack: prev.undoStack.slice(0, -1),
      redoStack: [...prev.redoStack, lastEdit]
    }));

    // Create reverse edit for external handler
    const reverseEdit: CellEdit = {
      rowId: lastEdit.rowId,
      columnId: lastEdit.columnId,
      value: lastEdit.oldValue,
      oldValue: lastEdit.value,
      timestamp: new Date()
    };
    onCellEdit?.(reverseEdit);
  }, [undoRedoState.undoStack, onCellEdit]);

  const redo = useCallback(() => {
    if (undoRedoState.redoStack.length === 0) return;

    const editToRedo = undoRedoState.redoStack[undoRedoState.redoStack.length - 1];
    
    // Reapply the change
    setTableState(prev => ({
      ...prev,
      data: prev.data.map(row => 
        row.id === editToRedo.rowId 
          ? { ...row, [editToRedo.columnId]: editToRedo.value }
          : row
      )
    }));

    // Update undo/redo stacks
    setUndoRedoState(prev => ({
      ...prev,
      undoStack: [...prev.undoStack, editToRedo],
      redoStack: prev.redoStack.slice(0, -1)
    }));

    onCellEdit?.(editToRedo);
  }, [undoRedoState.redoStack, onCellEdit]);

  // Computed properties
  const canUndo = useMemo(() => undoRedoState.undoStack.length > 0, [undoRedoState.undoStack]);
  const canRedo = useMemo(() => undoRedoState.redoStack.length > 0, [undoRedoState.redoStack]);

  return {
    tableState,
    updateCell,
    startCellEdit,
    finishCellEdit,
    cancelCellEdit,
    toggleRowSelection,
    toggleSelectAll,
    clearSelection,
    updateFilters,
    addFilter,
    removeFilter,
    updateSearch,
    updateSort,
    clearSort,
    updatePagination,
    undo,
    redo,
    canUndo,
    canRedo
  };
};