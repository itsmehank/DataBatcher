import { Controller, Get, Post, UseGuards } from '@nestjs/common';
import { BackupService } from './backup.service';
import { JwtAuthGuard } from '../common/jwt-auth.guard';

@Controller('admin/backup')
@UseGuards(JwtAuthGuard)
export class BackupController {
  constructor(private readonly backupService: BackupService) {}

  @Post('export')
  exportAll() {
    return this.backupService.exportAll();
  }

  @Get('status')
  status() {
    return this.backupService.status();
  }
}
