import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { MongooseModule } from '@nestjs/mongoose';
import { ThrottlerModule } from '@nestjs/throttler';
import { AuthModule } from './auth/auth.module';
import { CategoriesModule } from './categories/categories.module';
import { EntriesModule } from './entries/entries.module';
import { TemplatesModule } from './templates/templates.module';
import { BackupModule } from './backup/backup.module';
import { HealthController } from './health.controller';
import { SeedService } from './seed.service';
import { Admin, AdminSchema } from './auth/admin.schema';
import { Category, CategorySchema } from './categories/category.schema';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    MongooseModule.forRoot(process.env.MONGODB_URI || ''),
    MongooseModule.forFeature([
      { name: Admin.name, schema: AdminSchema },
      { name: Category.name, schema: CategorySchema },
    ]),
    ThrottlerModule.forRoot([{ ttl: 60_000, limit: 60 }]),
    AuthModule,
    CategoriesModule,
    EntriesModule,
    TemplatesModule,
    BackupModule,
  ],
  controllers: [HealthController],
  providers: [SeedService],
})
export class AppModule {}
