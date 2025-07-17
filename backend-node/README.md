# IDF Testing Infrastructure API

A military-grade Node.js/TypeScript backend API with Hebrew support for managing IDF testing infrastructure data.

## Features

- **Military-Grade Security**: JWT authentication, rate limiting, input validation, audit logging
- **Hebrew Language Support**: Full RTL text support, Hebrew text processing, validation
- **Excel Processing**: Secure file upload, parsing, and data processing with Hebrew content
- **PostgreSQL Database**: TypeORM with optimized queries and migrations
- **Redis Caching**: Session management, rate limiting, and performance optimization
- **Comprehensive Logging**: Structured logging with security audit trails
- **API Documentation**: Swagger/OpenAPI documentation with Hebrew field descriptions

## Technology Stack

- **Runtime**: Node.js 18+ with TypeScript
- **Framework**: Express.js with security middleware
- **Database**: PostgreSQL with TypeORM
- **Caching**: Redis with ioredis
- **Authentication**: JWT with refresh tokens
- **File Processing**: multer + xlsx for Excel files
- **Logging**: Winston with daily rotation
- **Documentation**: Swagger/OpenAPI 3.0

## Project Structure

```
src/
├── config/          # Configuration files (database, redis, env)
├── controllers/     # Route controllers with Hebrew error messages
├── middleware/      # Security, auth, and validation middleware
├── models/          # TypeORM entities with Hebrew field support
├── routes/          # API route definitions
├── services/        # Business logic and external integrations
├── utils/           # Utility functions (Hebrew text processing, logger)
├── validators/      # Input validation with Hebrew messages
└── server.ts        # Main application entry point
```

## Quick Start

### Prerequisites

- Node.js 18+ and npm 9+
- PostgreSQL 13+
- Redis 6+

### Installation

1. Clone and navigate to the project:
```bash
cd backend-node
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Build the TypeScript code:
```bash
npm run build
```

5. Run database migrations:
```bash
npm run migration:run
```

6. Start the development server:
```bash
npm run dev
```

The API will be available at `http://localhost:3000`

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login with Hebrew error messages
- `POST /api/auth/refresh` - Refresh JWT tokens
- `POST /api/auth/logout` - Secure logout with token blacklisting
- `GET /api/auth/me` - Get current user info

### Testing Data
- `GET /api/testing-data` - List testing data with Hebrew search
- `GET /api/testing-data/:id` - Get specific testing data
- `PUT /api/testing-data/:id` - Update testing data (requires permissions)
- `DELETE /api/testing-data/:id` - Delete testing data (admin only)
- `GET /api/testing-data/stats` - Get analytics and statistics

### File Upload
- `POST /api/files/upload` - Upload Excel files with security validation
- `GET /api/files/:id/status` - Check file processing status
- `GET /api/files` - List uploaded files
- `DELETE /api/files/:id` - Delete file and associated data

## Security Features

### Authentication & Authorization
- JWT with RS256 signing
- Refresh token rotation
- Role-based access control (RBAC)
- Account lockout after failed attempts
- Password complexity requirements

### Input Validation
- Hebrew text validation and normalization
- SQL injection prevention
- XSS protection with input sanitization
- File type and content validation
- Size limits and malware scanning

### Rate Limiting
- Global API rate limiting
- Login attempt rate limiting
- File upload rate limiting
- IP-based blocking for suspicious activity

### Audit Logging
- All security events logged
- Hebrew text operations tracked
- File operations with checksums
- User activity monitoring
- Structured log format for analysis

## Hebrew Language Support

### Text Processing
- Unicode normalization (NFD/NFC)
- Hebrew diacritic removal
- RTL text handling
- Hebrew numeral conversion
- Search term generation

### Validation
- Hebrew name validation
- Military ID format checking
- Mixed language content handling
- Character encoding verification

### Database Storage
- UTF-8 encoding for all Hebrew fields
- Proper collation for Hebrew sorting
- Full-text search optimization
- RTL text indexing

## Environment Variables

See `.env.example` for all available configuration options:

- **Application**: PORT, NODE_ENV, API_PREFIX
- **Database**: DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME
- **JWT**: JWT_SECRET, JWT_EXPIRES_IN, JWT_REFRESH_SECRET
- **Redis**: REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
- **Security**: BCRYPT_ROUNDS, RATE_LIMIT_*, CORS_ORIGINS
- **Files**: MAX_FILE_SIZE, UPLOAD_PATH, ALLOWED_FILE_TYPES
- **Hebrew**: HEBREW_VALIDATION, RTL_SUPPORT, UNICODE_NORMALIZATION
- **Logging**: LOG_LEVEL, LOG_FORMAT, LOG_DIRECTORY

## Development Scripts

```bash
npm run dev          # Start development server with nodemon
npm run build        # Build TypeScript to JavaScript
npm run start        # Start production server
npm run test         # Run test suite
npm run lint         # Run ESLint
npm run lint:fix     # Fix ESLint issues
npm run clean        # Clean build directory
```

## Database Scripts

```bash
npm run migration:generate  # Generate new migration
npm run migration:run      # Run pending migrations
npm run migration:revert   # Revert last migration
```

## Production Deployment

1. Set `NODE_ENV=production` in environment
2. Configure PostgreSQL with SSL
3. Set up Redis cluster for high availability
4. Configure reverse proxy (nginx) with HTTPS
5. Set up log aggregation and monitoring
6. Enable database backups and disaster recovery

## API Documentation

When `SWAGGER_ENABLED=true`, documentation is available at:
- Interactive docs: `http://localhost:3000/api/docs`
- JSON spec: `http://localhost:3000/api/docs.json`

## Monitoring & Health Checks

- Health endpoint: `GET /health`
- Returns database and Redis connection status
- Includes performance metrics and uptime
- Suitable for load balancer health checks

## Support

For technical support or security issues:
- Internal: Contact IDF Testing Infrastructure Team
- Security: Follow responsible disclosure process

## License

Proprietary - IDF Internal Use Only