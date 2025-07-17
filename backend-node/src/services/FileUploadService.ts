import multer from 'multer';
import path from 'path';
import crypto from 'crypto';
import { Request } from 'express';
import { env } from '../config/env';
import * as XLSX from 'xlsx';

export class FileUploadService {
  private static readonly ALLOWED_MIME_TYPES = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
    'application/vnd.ms-excel', // .xls
    'text/csv', // .csv
    'application/csv'
  ];

  private static readonly ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.csv'];

  static createMulterConfig() {
    const storage = multer.diskStorage({
      destination: (req, file, cb) => {
        cb(null, env.UPLOAD_PATH);
      },
      filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + crypto.randomBytes(6).toString('hex');
        const ext = path.extname(file.originalname);
        cb(null, `${file.fieldname}-${uniqueSuffix}${ext}`);
      }
    });

    const fileFilter = (req: Request, file: Express.Multer.File, cb: multer.FileFilterCallback) => {
      // Check file extension
      const ext = path.extname(file.originalname).toLowerCase();
      if (!this.ALLOWED_EXTENSIONS.includes(ext)) {
        return cb(new Error(`סוג קובץ לא נתמך: ${ext}. קבצים מותרים: ${this.ALLOWED_EXTENSIONS.join(', ')}`));
      }

      // Check MIME type
      if (!this.ALLOWED_MIME_TYPES.includes(file.mimetype)) {
        return cb(new Error(`סוג MIME לא נתמך: ${file.mimetype}`));
      }

      // Additional security: Check for malicious filenames
      if (this.isFilenameSecure(file.originalname)) {
        cb(null, true);
      } else {
        cb(new Error('שם קובץ מכיל תווים לא חוקיים'));
      }
    };

    return multer({
      storage,
      fileFilter,
      limits: {
        fileSize: env.MAX_FILE_SIZE,
        files: env.MAX_FILES_PER_REQUEST
      }
    });
  }

  private static isFilenameSecure(filename: string): boolean {
    // Check for path traversal attempts
    if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
      return false;
    }

    // Check for null bytes
    if (filename.includes('\0')) {
      return false;
    }

    // Check for executable extensions
    const dangerousExtensions = ['.exe', '.bat', '.cmd', '.scr', '.com', '.pif', '.vbs', '.js'];
    const ext = path.extname(filename).toLowerCase();
    if (dangerousExtensions.includes(ext)) {
      return false;
    }

    return true;
  }

  static async validateFileContent(filePath: string): Promise<{ valid: boolean; error?: string; metadata?: any }> {
    try {
      const workbook = XLSX.readFile(filePath);
      const sheetNames = workbook.SheetNames;

      if (sheetNames.length === 0) {
        return { valid: false, error: 'הקובץ לא מכיל גיליונות עבודה' };
      }

      // Get the first sheet
      const worksheet = workbook.Sheets[sheetNames[0]];
      const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

      if (data.length === 0) {
        return { valid: false, error: 'הקובץ ריק' };
      }

      // Check for minimum required columns (Hebrew headers)
      const headers = data[0] as string[];
      const requiredHeaders = ['מבנה', 'מנהל מבנה', 'סוג הבדיקה'];
      const missingHeaders = requiredHeaders.filter(header => 
        !headers.some(h => h && h.toString().includes(header))
      );

      if (missingHeaders.length > 0) {
        return { 
          valid: false, 
          error: `חסרים עמודות נדרשות: ${missingHeaders.join(', ')}` 
        };
      }

      // Validate data integrity
      const dataRows = data.slice(1);
      if (dataRows.length > 10000) {
        return { valid: false, error: 'הקובץ מכיל יותר מדי שורות (מקסימום 10,000)' };
      }

      return {
        valid: true,
        metadata: {
          totalRows: dataRows.length,
          totalColumns: headers.length,
          sheetNames,
          headers
        }
      };
    } catch (error) {
      return { 
        valid: false, 
        error: `שגיאה בקריאת הקובץ: ${error instanceof Error ? error.message : 'שגיאה לא ידועה'}` 
      };
    }
  }

  static async processExcelFile(filePath: string): Promise<any[]> {
    const workbook = XLSX.readFile(filePath);
    const worksheet = workbook.Sheets[workbook.SheetNames[0]];
    
    // Convert to JSON with Hebrew support
    const jsonData = XLSX.utils.sheet_to_json(worksheet, {
      header: 1,
      defval: '',
      blankrows: false
    });

    if (jsonData.length === 0) {
      throw new Error('No data found in Excel file');
    }

    const headers = jsonData[0] as string[];
    const dataRows = jsonData.slice(1) as any[][];

    // Map Hebrew headers to English field names
    const headerMapping: Record<string, string> = {
      'מבנה': 'buildingId',
      'מנהל מבנה': 'buildingManager',
      'צוות אדום': 'redTeam',
      'סוג הבדיקה': 'inspectionType',
      'מוביל הבדיקה': 'inspectionLeader',
      'סבב בדיקות': 'inspectionRound',
      'רגולטור 1': 'regulator1',
      'רגולטור 2': 'regulator2',
      'לו"ז ביצוע מתואם/ ריאלי': 'executionSchedule',
      'יעד לסיום': 'targetCompletion',
      'האם מתואם מול זכיין?': 'coordinatedWithContractor',
      'צרופת דו"ח ליקויים': 'defectReportAttached',
      'האם הדו"ח הופץ': 'reportDistributed',
      'תאריך הפצת הדו"ח': 'distributionDate'
    };

    // Process data rows
    const processedData = dataRows.map(row => {
      const rowData: any = {};
      
      headers.forEach((header, index) => {
        const englishKey = headerMapping[header] || header;
        let value = row[index];

        // Process different data types
        if (value !== undefined && value !== null && value !== '') {
          // Handle dates
          if (englishKey.includes('Date') || englishKey.includes('Schedule') || englishKey.includes('Completion')) {
            value = this.parseExcelDate(value);
          }
          // Handle booleans
          else if (englishKey.includes('coordinated') || englishKey.includes('Distributed')) {
            value = this.parseBoolean(value);
          }
          // Handle numbers
          else if (englishKey === 'inspectionRound') {
            value = parseInt(value) || 0;
          }
          // Handle strings (trim whitespace)
          else if (typeof value === 'string') {
            value = value.trim();
          }
        }

        rowData[englishKey] = value;
      });

      return rowData;
    });

    return processedData;
  }

  private static parseExcelDate(value: any): Date | null {
    if (!value) return null;

    // Handle Excel serial number dates
    if (typeof value === 'number') {
      const excelEpoch = new Date(1900, 0, 1);
      const date = new Date(excelEpoch.getTime() + (value - 1) * 24 * 60 * 60 * 1000);
      return date;
    }

    // Handle string dates
    if (typeof value === 'string') {
      const parsedDate = new Date(value);
      return isNaN(parsedDate.getTime()) ? null : parsedDate;
    }

    // Handle Date objects
    if (value instanceof Date) {
      return value;
    }

    return null;
  }

  private static parseBoolean(value: any): boolean {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'string') {
      const lower = value.toLowerCase().trim();
      return lower === 'true' || lower === 'כן' || lower === '1' || lower === 'yes';
    }
    if (typeof value === 'number') {
      return value > 0;
    }
    return false;
  }

  static generateFileHash(filePath: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const hash = crypto.createHash('sha256');
      const fs = require('fs');
      const stream = fs.createReadStream(filePath);

      stream.on('data', (data: Buffer) => hash.update(data));
      stream.on('end', () => resolve(hash.digest('hex')));
      stream.on('error', reject);
    });
  }
}