import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { User, UserRole } from '../models/User';
import { redisManager } from '../config/redis';
import { env } from '../config/env';
import { AppDataSource } from '../config/database';

export interface JwtPayload {
  userId: string;
  email: string;
  role: UserRole;
  iat: number;
  exp: number;
}

export interface LoginResult {
  user: Partial<User>;
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

export class AuthService {
  private userRepository = AppDataSource.getRepository(User);

  async login(email: string, password: string, ipAddress: string): Promise<LoginResult> {
    const user = await this.userRepository.findOne({ where: { email } });
    
    if (!user) {
      throw new Error('אימייל או סיסמה שגויים');
    }

    if (!user.canLogin) {
      throw new Error('החשבון לא פעיל או נחסם');
    }

    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
      user.incrementFailedLoginAttempts();
      await this.userRepository.save(user);
      throw new Error('אימייל או סיסמה שגויים');
    }

    user.updateLastLogin(ipAddress);
    await this.userRepository.save(user);

    const tokens = await this.generateTokens(user);
    
    return {
      user: user.toSafeObject(),
      ...tokens
    };
  }

  async refreshToken(refreshToken: string): Promise<{ accessToken: string; expiresIn: number }> {
    try {
      const decoded = jwt.verify(refreshToken, env.JWT_REFRESH_SECRET) as JwtPayload;
      
      const isBlacklisted = await redisManager.isTokenBlacklisted(refreshToken);
      if (isBlacklisted) {
        throw new Error('Token is blacklisted');
      }

      const user = await this.userRepository.findOne({ where: { id: decoded.userId } });
      if (!user || !user.canLogin) {
        throw new Error('User not found or inactive');
      }

      const accessToken = this.generateAccessToken(user);
      const expiresIn = this.getTokenExpirationTime(env.JWT_EXPIRES_IN);

      return { accessToken, expiresIn };
    } catch (error) {
      throw new Error('Invalid refresh token');
    }
  }

  async logout(accessToken: string, refreshToken?: string): Promise<void> {
    const accessTokenExp = this.getTokenExpirationTime(env.JWT_EXPIRES_IN);
    await redisManager.blacklistToken(accessToken, accessTokenExp);

    if (refreshToken) {
      const refreshTokenExp = this.getTokenExpirationTime(env.JWT_REFRESH_EXPIRES_IN);
      await redisManager.blacklistToken(refreshToken, refreshTokenExp);
    }
  }

  private async generateTokens(user: User): Promise<{ accessToken: string; refreshToken: string; expiresIn: number }> {
    const accessToken = this.generateAccessToken(user);
    const refreshToken = this.generateRefreshToken(user);
    const expiresIn = this.getTokenExpirationTime(env.JWT_EXPIRES_IN);

    return { accessToken, refreshToken, expiresIn };
  }

  private generateAccessToken(user: User): string {
    const payload: Partial<JwtPayload> = {
      userId: user.id,
      email: user.email,
      role: user.role
    };

    return jwt.sign(payload, env.JWT_SECRET, {
      expiresIn: env.JWT_EXPIRES_IN,
      issuer: 'IDF-Testing-Infrastructure',
      audience: 'idf-api-users'
    });
  }

  private generateRefreshToken(user: User): string {
    return jwt.sign(
      { userId: user.id },
      env.JWT_REFRESH_SECRET,
      { expiresIn: env.JWT_REFRESH_EXPIRES_IN }
    );
  }

  private getTokenExpirationTime(expiresIn: string): number {
    const match = expiresIn.match(/(\d+)([hd])/);
    if (!match) return 3600; // Default 1 hour

    const value = parseInt(match[1]);
    const unit = match[2];

    switch (unit) {
      case 'h': return value * 3600;
      case 'd': return value * 24 * 3600;
      default: return 3600;
    }
  }

  async verifyToken(token: string): Promise<JwtPayload> {
    const isBlacklisted = await redisManager.isTokenBlacklisted(token);
    if (isBlacklisted) {
      throw new Error('Token is blacklisted');
    }

    try {
      return jwt.verify(token, env.JWT_SECRET) as JwtPayload;
    } catch (error) {
      throw new Error('Invalid or expired token');
    }
  }
}