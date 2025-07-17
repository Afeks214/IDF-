import { Request, Response } from 'express';
import { FileUploadService } from '../services/FileUploadService';
import { AppDataSource } from '../config/database';
import { ExcelFile, FileStatus } from '../models/ExcelFile';
import { TestingData } from '../models/TestingData';
import fs from 'fs/promises';
import path from 'path';

export class FileUploadController {
  private excelFileRepository = AppDataSource.getRepository(ExcelFile);
  private testingDataRepository = AppDataSource.getRepository(TestingData);

  uploadFile = async (req: Request, res: Response): Promise<void> => {
    try {
      if (!req.file) {
        res.status(400).json({
          error: 'NO_FILE',
          message: 'לא נבחר קובץ להעלאה'
        });
        return;
      }

      const file = req.file;
      
      // Generate file hash for duplicate detection
      const fileHash = await FileUploadService.generateFileHash(file.path);
      
      // Check for duplicate files
      const existingFile = await this.excelFileRepository.findOne({
        where: { fileHash }
      });

      if (existingFile) {
        // Remove the uploaded file
        await fs.unlink(file.path);
        
        res.status(409).json({
          error: 'DUPLICATE_FILE',
          message: 'הקובץ כבר קיים במערכת',
          existingFileId: existingFile.id
        });
        return;
      }

      // Validate file content
      const validation = await FileUploadService.validateFileContent(file.path);
      if (!validation.valid) {
        // Remove the invalid file
        await fs.unlink(file.path);
        
        res.status(400).json({
          error: 'INVALID_FILE_CONTENT',
          message: validation.error
        });
        return;
      }

      // Create file record
      const excelFile = this.excelFileRepository.create({
        fileName: file.originalname,
        filePath: file.path,
        mimeType: file.mimetype,
        fileSize: file.size,
        fileHash,
        status: FileStatus.PROCESSING,
        totalRows: validation.metadata?.totalRows || 0,
        uploadedBy: { id: req.user!.userId } as any
      });

      const savedFile = await this.excelFileRepository.save(excelFile);

      // Process file in background
      this.processFileAsync(savedFile.id, file.path);

      res.status(201).json({
        success: true,
        message: 'הקובץ הועלה בהצלחה ונמצא בעיבוד',
        data: {
          fileId: savedFile.id,
          fileName: savedFile.fileName,
          status: savedFile.status,
          totalRows: savedFile.totalRows
        }
      });
    } catch (error) {
      // Clean up file if it exists
      if (req.file?.path) {
        try {
          await fs.unlink(req.file.path);
        } catch (unlinkError) {
          console.error('Error removing file:', unlinkError);
        }
      }

      res.status(500).json({
        error: 'UPLOAD_FAILED',
        message: 'שגיאה בהעלאת הקובץ',
        details: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  };

  private async processFileAsync(fileId: string, filePath: string): Promise<void> {
    try {
      // Process Excel data
      const processedData = await FileUploadService.processExcelFile(filePath);
      
      // Save processed data to database
      const testingDataEntries = processedData.map(data => 
        this.testingDataRepository.create({
          ...data,
          sourceFile: { id: fileId } as any
        })
      );

      await this.testingDataRepository.save(testingDataEntries);

      // Update file status
      await this.excelFileRepository.update(fileId, {
        status: FileStatus.COMPLETED,
        processedRows: testingDataEntries.length
      });

      console.log(`Successfully processed file ${fileId}: ${testingDataEntries.length} records`);
    } catch (error) {
      console.error(`Error processing file ${fileId}:`, error);
      
      // Update file status with error
      await this.excelFileRepository.update(fileId, {
        status: FileStatus.FAILED,
        errorMessage: error instanceof Error ? error.message : 'Unknown processing error'
      });
    }
  }

  getFileStatus = async (req: Request, res: Response): Promise<void> => {
    try {
      const { fileId } = req.params;

      const file = await this.excelFileRepository.findOne({
        where: { id: fileId },
        relations: ['uploadedBy']
      });

      if (!file) {
        res.status(404).json({
          error: 'FILE_NOT_FOUND',
          message: 'קובץ לא נמצא'
        });
        return;
      }

      res.json({
        success: true,
        data: {
          id: file.id,
          fileName: file.fileName,
          status: file.status,
          totalRows: file.totalRows,
          processedRows: file.processedRows,
          errorMessage: file.errorMessage,
          uploadedAt: file.createdAt,
          uploadedBy: file.uploadedBy.fullName
        }
      });
    } catch (error) {
      res.status(500).json({
        error: 'STATUS_CHECK_FAILED',
        message: 'שגיאה בבדיקת סטטוס הקובץ'
      });
    }
  };

  getUploadedFiles = async (req: Request, res: Response): Promise<void> => {
    try {
      const { page = 1, limit = 20 } = req.query;

      const [files, total] = await this.excelFileRepository.findAndCount({
        relations: ['uploadedBy'],
        skip: (Number(page) - 1) * Number(limit),
        take: Number(limit),
        order: { createdAt: 'DESC' }
      });

      res.json({
        success: true,
        data: files.map(file => ({
          id: file.id,
          fileName: file.fileName,
          status: file.status,
          totalRows: file.totalRows,
          processedRows: file.processedRows,
          uploadedAt: file.createdAt,
          uploadedBy: file.uploadedBy.fullName
        })),
        pagination: {
          page: Number(page),
          limit: Number(limit),
          total,
          totalPages: Math.ceil(total / Number(limit))
        }
      });
    } catch (error) {
      res.status(500).json({
        error: 'FETCH_FILES_FAILED',
        message: 'שגיאה בטעינת רשימת הקבצים'
      });
    }
  };

  deleteFile = async (req: Request, res: Response): Promise<void> => {
    try {
      const { fileId } = req.params;

      const file = await this.excelFileRepository.findOne({
        where: { id: fileId }
      });

      if (!file) {
        res.status(404).json({
          error: 'FILE_NOT_FOUND',
          message: 'קובץ לא נמצא'
        });
        return;
      }

      // Delete associated testing data
      await this.testingDataRepository.delete({ sourceFile: { id: fileId } });

      // Delete file from filesystem
      try {
        await fs.unlink(file.filePath);
      } catch (fsError) {
        console.warn('Could not delete file from filesystem:', fsError);
      }

      // Delete file record
      await this.excelFileRepository.delete(fileId);

      res.json({
        success: true,
        message: 'הקובץ נמחק בהצלחה'
      });
    } catch (error) {
      res.status(500).json({
        error: 'DELETE_FAILED',
        message: 'שגיאה במחיקת הקובץ'
      });
    }
  };
}