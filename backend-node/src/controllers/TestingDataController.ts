import { Request, Response } from 'express';
import { AppDataSource } from '../config/database';
import { TestingData } from '../models/TestingData';
import { Like, Between } from 'typeorm';

export class TestingDataController {
  private repository = AppDataSource.getRepository(TestingData);

  getAll = async (req: Request, res: Response): Promise<void> => {
    try {
      const { page = 1, limit = 20, search, buildingId, inspectionType, startDate, endDate } = req.query;
      
      const where: any = {};
      
      if (search) {
        where.buildingManager = Like(`%${search}%`);
      }
      
      if (buildingId) {
        where.buildingId = buildingId;
      }
      
      if (inspectionType) {
        where.inspectionType = inspectionType;
      }
      
      if (startDate && endDate) {
        where.executionSchedule = Between(new Date(startDate as string), new Date(endDate as string));
      }

      const [data, total] = await this.repository.findAndCount({
        where,
        relations: ['sourceFile'],
        skip: (Number(page) - 1) * Number(limit),
        take: Number(limit),
        order: { createdAt: 'DESC' }
      });

      res.json({
        success: true,
        data,
        pagination: {
          page: Number(page),
          limit: Number(limit),
          total,
          totalPages: Math.ceil(total / Number(limit))
        }
      });
    } catch (error) {
      res.status(500).json({
        error: 'FETCH_FAILED',
        message: 'שגיאה בטעינת הנתונים',
        details: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  };

  getById = async (req: Request, res: Response): Promise<void> => {
    try {
      const { id } = req.params;
      
      const data = await this.repository.findOne({
        where: { id },
        relations: ['sourceFile']
      });

      if (!data) {
        res.status(404).json({
          error: 'NOT_FOUND',
          message: 'נתונים לא נמצאו'
        });
        return;
      }

      res.json({
        success: true,
        data
      });
    } catch (error) {
      res.status(500).json({
        error: 'FETCH_FAILED',
        message: 'שגיאה בטעינת הנתונים'
      });
    }
  };

  update = async (req: Request, res: Response): Promise<void> => {
    try {
      const { id } = req.params;
      const updateData = req.body;

      const result = await this.repository.update(id, updateData);

      if (result.affected === 0) {
        res.status(404).json({
          error: 'NOT_FOUND',
          message: 'נתונים לא נמצאו'
        });
        return;
      }

      const updatedData = await this.repository.findOne({ where: { id } });

      res.json({
        success: true,
        message: 'נתונים עודכנו בהצלחה',
        data: updatedData
      });
    } catch (error) {
      res.status(500).json({
        error: 'UPDATE_FAILED',
        message: 'שגיאה בעדכון הנתונים'
      });
    }
  };

  delete = async (req: Request, res: Response): Promise<void> => {
    try {
      const { id } = req.params;

      const result = await this.repository.delete(id);

      if (result.affected === 0) {
        res.status(404).json({
          error: 'NOT_FOUND',
          message: 'נתונים לא נמצאו'
        });
        return;
      }

      res.json({
        success: true,
        message: 'נתונים נמחקו בהצלחה'
      });
    } catch (error) {
      res.status(500).json({
        error: 'DELETE_FAILED',
        message: 'שגיאה במחיקת הנתונים'
      });
    }
  };

  getStats = async (req: Request, res: Response): Promise<void> => {
    try {
      const totalRecords = await this.repository.count();
      const completedInspections = await this.repository.count({
        where: { reportDistributed: true }
      });
      const pendingInspections = await this.repository.count({
        where: { reportDistributed: false }
      });

      res.json({
        success: true,
        data: {
          totalRecords,
          completedInspections,
          pendingInspections,
          completionRate: totalRecords > 0 ? (completedInspections / totalRecords) * 100 : 0
        }
      });
    } catch (error) {
      res.status(500).json({
        error: 'STATS_FAILED',
        message: 'שגיאה בטעינת הסטטיסטיקות'
      });
    }
  };
}