import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import { InjectConnection } from '@nestjs/mongoose';
import { Connection } from 'mongoose';
import { gzipSync } from 'zlib';
import { promises as fs } from 'fs';
import * as path from 'path';

type BackupStatus = {
  ok: boolean;
  message: string;
  timestamp: string;
};

@Injectable()
export class BackupService {
  private isRunning = false;
  private lastStatus: BackupStatus = {
    ok: true,
    message: '아직 백업 실행 이력이 없습니다.',
    timestamp: new Date().toISOString(),
  };

  constructor(@InjectConnection() private readonly connection: Connection) {}

  private backupDir() {
    return process.env.BACKUP_DIR || '/app/backups';
  }

  private backupFileName() {
    return process.env.BACKUP_FILE_NAME || 'latest.archive.gz';
  }

  async exportAll() {
    if (this.isRunning) {
      throw new ServiceUnavailableException('이미 백업이 실행 중입니다.');
    }

    this.isRunning = true;

    try {
      await fs.mkdir(this.backupDir(), { recursive: true });

      const db = this.connection.db;
      if (!db) {
        throw new Error('MongoDB 연결이 초기화되지 않았습니다.');
      }
      const collections = await db.listCollections().toArray();

      const payload: Record<string, unknown> = {
        exportedAt: new Date().toISOString(),
        databaseName: db.databaseName,
        collections: {},
      };

      for (const item of collections) {
        const docs = await db.collection(item.name).find({}).toArray();
        (payload.collections as Record<string, unknown[]>)[item.name] = docs;
      }

      const tempFile = path.join(
        this.backupDir(),
        `tmp-${Date.now()}-${this.backupFileName()}`,
      );
      const finalFile = path.join(this.backupDir(), this.backupFileName());

      const compressed = gzipSync(Buffer.from(JSON.stringify(payload), 'utf-8'));
      await fs.writeFile(tempFile, compressed);

      const allFiles = await fs.readdir(this.backupDir());
      const archiveFiles = allFiles.filter(
        (name) => name.endsWith('.archive.gz') && name !== path.basename(tempFile),
      );
      await Promise.all(
        archiveFiles.map((name) => fs.unlink(path.join(this.backupDir(), name))),
      );

      await fs.rename(tempFile, finalFile);
      const stats = await fs.stat(finalFile);

      this.lastStatus = {
        ok: true,
        message: `백업 완료 (${stats.size} bytes)`,
        timestamp: new Date().toISOString(),
      };

      return {
        ok: true,
        fileName: this.backupFileName(),
        size: stats.size,
        createdAt: new Date().toISOString(),
      };
    } catch (error) {
      this.lastStatus = {
        ok: false,
        message: `백업 실패: ${(error as Error).message}`,
        timestamp: new Date().toISOString(),
      };
      throw error;
    } finally {
      this.isRunning = false;
    }
  }

  async status() {
    const filePath = path.join(this.backupDir(), this.backupFileName());
    let fileInfo: {
      exists: boolean;
      fileName?: string;
      size?: number;
      updatedAt?: string;
    } = { exists: false };

    try {
      const stats = await fs.stat(filePath);
      fileInfo = {
        exists: true,
        fileName: this.backupFileName(),
        size: stats.size,
        updatedAt: stats.mtime.toISOString(),
      };
    } catch {
      fileInfo = { exists: false };
    }

    return {
      running: this.isRunning,
      lastStatus: this.lastStatus,
      file: fileInfo,
    };
  }
}
