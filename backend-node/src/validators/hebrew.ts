import { body, param, query } from 'express-validator';
import { HebrewTextProcessor } from '../utils/hebrew';

/**
 * Custom validators for Hebrew text fields
 */

export const hebrewNameValidator = (fieldName: string, required = true) => {
  const validator = body(fieldName);
  
  if (required) {
    validator.notEmpty().withMessage(`${fieldName} נדרש`);
  } else {
    validator.optional();
  }
  
  return validator
    .isLength({ min: 2, max: 100 })
    .withMessage(`${fieldName} חייב להיות בין 2-100 תווים`)
    .custom((value) => {
      if (!value) return true; // Skip if optional and empty
      
      const validation = HebrewTextProcessor.validateHebrewName(value);
      if (!validation.valid) {
        throw new Error(validation.errors.join(', '));
      }
      return true;
    });
};

export const militaryIdValidator = body('militaryId')
  .optional()
  .custom((value) => {
    if (!value) return true;
    
    const validation = HebrewTextProcessor.validateMilitaryId(value);
    if (!validation.valid) {
      throw new Error(validation.errors.join(', '));
    }
    return true;
  });

export const hebrewTextValidator = (fieldName: string, maxLength = 500) =>
  body(fieldName)
    .optional()
    .isLength({ max: maxLength })
    .withMessage(`${fieldName} לא יכול להיות יותר מ-${maxLength} תווים`)
    .custom((value) => {
      if (!value) return true;
      
      // Check for malicious content
      const maliciousPatterns = [
        /<script/i,
        /javascript:/i,
        /on\w+\s*=/i,
        /<iframe/i,
        /<object/i,
        /<embed/i
      ];
      
      for (const pattern of maliciousPatterns) {
        if (pattern.test(value)) {
          throw new Error('הטקסט מכיל תוכן חשוד');
        }
      }
      
      return true;
    });

export const buildingIdValidator = body('buildingId')
  .notEmpty()
  .withMessage('מזהה מבנה נדרש')
  .isLength({ max: 10 })
  .withMessage('מזהה מבנה לא יכול להיות יותר מ-10 תווים')
  .matches(/^[A-Za-z0-9\u05D0-\u05EA]+$/)
  .withMessage('מזהה מבנה יכול לכלול רק אותיות ומספרים');

export const hebrewSearchValidator = query('search')
  .optional()
  .isLength({ min: 2, max: 100 })
  .withMessage('חיפוש חייב להיות בין 2-100 תווים')
  .custom((value) => {
    if (!value) return true;
    
    // Clean the search term
    const cleaned = HebrewTextProcessor.cleanForSearch(value);
    if (cleaned.length === 0) {
      throw new Error('מונח חיפוש לא חוקי');
    }
    
    return true;
  });

export const paginationValidators = [
  query('page')
    .optional()
    .isInt({ min: 1 })
    .withMessage('מספר עמוד חייב להיות מספר חיובי'),
  query('limit')
    .optional()
    .isInt({ min: 1, max: 100 })
    .withMessage('מגבלת תוצאות חייבת להיות בין 1-100')
];

export const dateRangeValidators = [
  query('startDate')
    .optional()
    .isISO8601()
    .withMessage('תאריך התחלה לא חוקי'),
  query('endDate')
    .optional()
    .isISO8601()
    .withMessage('תאריך סיום לא חוקי')
    .custom((value, { req }) => {
      if (value && req.query?.startDate) {
        const start = new Date(req.query.startDate as string);
        const end = new Date(value);
        if (end < start) {
          throw new Error('תאריך הסיום חייב להיות אחרי תאריך ההתחלה');
        }
      }
      return true;
    })
];

export const uuidValidator = (paramName: string) =>
  param(paramName)
    .isUUID(4)
    .withMessage(`${paramName} חייב להיות UUID חוקי`);

export const createTestingDataValidators = [
  buildingIdValidator,
  hebrewNameValidator('buildingManager'),
  hebrewTextValidator('redTeam', 200),
  hebrewTextValidator('inspectionType', 100),
  hebrewNameValidator('inspectionLeader'),
  body('inspectionRound')
    .isInt({ min: 1 })
    .withMessage('מספר סבב בדיקה חייב להיות מספר חיובי'),
  hebrewTextValidator('regulator1', 50),
  hebrewTextValidator('regulator2', 50),
  body('executionSchedule')
    .optional()
    .isISO8601()
    .withMessage('תאריך ביצוע לא חוקי'),
  body('targetCompletion')
    .optional()
    .isISO8601()
    .withMessage('תאריך יעד לא חוקי'),
  body('coordinatedWithContractor')
    .optional()
    .isBoolean()
    .withMessage('השדה חייב להיות true או false'),
  body('reportDistributed')
    .optional()
    .isBoolean()
    .withMessage('השדה חייב להיות true או false')
];

export const updateTestingDataValidators = [
  uuidValidator('id'),
  ...createTestingDataValidators.map(validator => validator.optional())
];