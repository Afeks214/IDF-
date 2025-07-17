import { useState, useCallback, RefObject } from 'react';
import { FixedSizeGrid as Grid } from 'react-window';
import { DataRow, Column } from '../types';

interface UseKeyboardNavigationProps {
  data: DataRow[];
  columns: Column[];
  onCellEdit?: (rowId: string, columnId: string) => void;
  gridRef?: RefObject<Grid>;
}

interface ActiveCell {
  rowIndex: number;
  columnIndex: number;
}

export const useKeyboardNavigation = ({
  data,
  columns,
  onCellEdit,
  gridRef
}: UseKeyboardNavigationProps) => {
  const [activeCell, setActiveCell] = useState<ActiveCell | null>(null);

  const navigateCell = useCallback((rowIndex: number, columnIndex: number) => {
    const newActiveCell = { rowIndex, columnIndex };
    setActiveCell(newActiveCell);

    // Scroll to cell if using virtual grid
    if (gridRef?.current) {
      gridRef.current.scrollToItem({
        rowIndex: rowIndex + 1, // +1 for header
        columnIndex,
        align: 'auto'
      });
    }
  }, [gridRef]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!activeCell) return;

    const { rowIndex, columnIndex } = activeCell;
    
    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault();
        if (rowIndex > 0) {
          navigateCell(rowIndex - 1, columnIndex);
        }
        break;

      case 'ArrowDown':
        e.preventDefault();
        if (rowIndex < data.length - 1) {
          navigateCell(rowIndex + 1, columnIndex);
        }
        break;

      case 'ArrowLeft':
        e.preventDefault();
        if (columnIndex > 0) {
          navigateCell(rowIndex, columnIndex - 1);
        }
        break;

      case 'ArrowRight':
        e.preventDefault();
        if (columnIndex < columns.length - 1) {
          navigateCell(rowIndex, columnIndex + 1);
        }
        break;

      case 'Enter':
        e.preventDefault();
        const row = data[rowIndex];
        const column = columns[columnIndex];
        if (row && column && column.editable) {
          onCellEdit?.(row.id, column.id);
        }
        break;

      case 'F2':
        e.preventDefault();
        const f2Row = data[rowIndex];
        const f2Column = columns[columnIndex];
        if (f2Row && f2Column && f2Column.editable) {
          onCellEdit?.(f2Row.id, f2Column.id);
        }
        break;

      case 'Home':
        e.preventDefault();
        if (e.ctrlKey) {
          // Ctrl+Home: Go to first cell
          navigateCell(0, 0);
        } else {
          // Home: Go to first column in current row
          navigateCell(rowIndex, 0);
        }
        break;

      case 'End':
        e.preventDefault();
        if (e.ctrlKey) {
          // Ctrl+End: Go to last cell
          navigateCell(data.length - 1, columns.length - 1);
        } else {
          // End: Go to last column in current row
          navigateCell(rowIndex, columns.length - 1);
        }
        break;

      case 'PageUp':
        e.preventDefault();
        const pageUpNewRow = Math.max(0, rowIndex - 10);
        navigateCell(pageUpNewRow, columnIndex);
        break;

      case 'PageDown':
        e.preventDefault();
        const pageDownNewRow = Math.min(data.length - 1, rowIndex + 10);
        navigateCell(pageDownNewRow, columnIndex);
        break;

      case 'Tab':
        e.preventDefault();
        if (e.shiftKey) {
          // Shift+Tab: Move to previous cell
          if (columnIndex > 0) {
            navigateCell(rowIndex, columnIndex - 1);
          } else if (rowIndex > 0) {
            navigateCell(rowIndex - 1, columns.length - 1);
          }
        } else {
          // Tab: Move to next cell
          if (columnIndex < columns.length - 1) {
            navigateCell(rowIndex, columnIndex + 1);
          } else if (rowIndex < data.length - 1) {
            navigateCell(rowIndex + 1, 0);
          }
        }
        break;

      case 'Escape':
        e.preventDefault();
        setActiveCell(null);
        break;

      case 'Delete':
      case 'Backspace':
        e.preventDefault();
        const deleteRow = data[rowIndex];
        const deleteColumn = columns[columnIndex];
        if (deleteRow && deleteColumn && deleteColumn.editable) {
          // Clear cell value
          onCellEdit?.(deleteRow.id, deleteColumn.id);
        }
        break;

      default:
        // Handle character input for quick editing
        if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
          const charRow = data[rowIndex];
          const charColumn = columns[columnIndex];
          if (charRow && charColumn && charColumn.editable) {
            onCellEdit?.(charRow.id, charColumn.id);
          }
        }
        break;
    }
  }, [activeCell, data, columns, navigateCell, onCellEdit]);

  // Excel-like selection handling
  const handleMouseSelection = useCallback((
    startRow: number, 
    startCol: number, 
    endRow: number, 
    endCol: number
  ) => {
    // For future implementation of range selection
    console.log('Range selection:', { startRow, startCol, endRow, endCol });
  }, []);

  // Copy/Paste handling
  const handleCopy = useCallback(() => {
    if (!activeCell) return;

    const { rowIndex, columnIndex } = activeCell;
    const row = data[rowIndex];
    const column = columns[columnIndex];
    
    if (row && column) {
      const value = row[column.id];
      if (value !== null && value !== undefined) {
        navigator.clipboard.writeText(value.toString());
      }
    }
  }, [activeCell, data, columns]);

  const handlePaste = useCallback(async () => {
    if (!activeCell) return;

    try {
      const text = await navigator.clipboard.readText();
      const { rowIndex, columnIndex } = activeCell;
      const row = data[rowIndex];
      const column = columns[columnIndex];
      
      if (row && column && column.editable) {
        onCellEdit?.(row.id, column.id);
        // The actual paste handling would be done in the cell edit component
      }
    } catch (err) {
      console.error('Failed to read clipboard:', err);
    }
  }, [activeCell, data, columns, onCellEdit]);

  // Extended keyboard shortcuts
  const handleAdvancedKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'c':
          e.preventDefault();
          handleCopy();
          break;
        
        case 'v':
          e.preventDefault();
          handlePaste();
          break;
        
        case 'a':
          e.preventDefault();
          // Select all - would need to be implemented in parent component
          break;
        
        case 'z':
          e.preventDefault();
          // Undo - would be handled by parent component
          break;
        
        case 'y':
          e.preventDefault();
          // Redo - would be handled by parent component
          break;
        
        case 'f':
          e.preventDefault();
          // Find - would open search dialog
          break;
      }
    }
    
    // Call the basic navigation handler
    handleKeyDown(e);
  }, [handleKeyDown, handleCopy, handlePaste]);

  return {
    activeCell,
    navigateCell,
    handleKeyDown: handleAdvancedKeyDown,
    handleMouseSelection,
    setActiveCell
  };
};