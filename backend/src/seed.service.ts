import { Injectable, OnModuleInit } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import * as bcrypt from 'bcrypt';
import { Admin } from './auth/admin.schema';
import { Category } from './categories/category.schema';

@Injectable()
export class SeedService implements OnModuleInit {
  constructor(
    @InjectModel(Admin.name) private readonly adminModel: Model<Admin>,
    @InjectModel(Category.name) private readonly categoryModel: Model<Category>,
  ) {}

  async onModuleInit() {
    await this.seedAdmin();
    await this.seedCategories();
  }

  private async seedAdmin() {
    const username = process.env.ADMIN_USERNAME;
    const password = process.env.ADMIN_PASSWORD;
    if (!username || !password) {
      return;
    }

    const normalizedUsername = username.toLowerCase().trim();
    const exists = await this.adminModel.findOne({ username: normalizedUsername }).lean();
    if (exists) {
      return;
    }

    const passwordHash = await bcrypt.hash(password, 10);
    await this.adminModel.create({ username: normalizedUsername, passwordHash });
  }

  private async seedCategories() {
    const count = await this.categoryModel.countDocuments();
    if (count > 0) {
      return;
    }

    await this.categoryModel.insertMany([
      {
        name: '미분류',
        description: '카테고리가 지정되지 않은 항목',
        color: '#A7A7A7',
        order: 0,
        isDefault: true,
      },
      {
        name: '다시 읽을 가치가 있는 내용',
        description: '핵심 통찰이나 인사이트가 있는 대화',
        color: '#2C6E49',
        order: 1,
        isDefault: true,
      },
      {
        name: '아이디어 고도화 필요',
        description: '구체화와 추가 검토가 필요한 아이디어',
        color: '#D68C45',
        order: 2,
        isDefault: true,
      },
      {
        name: '정신/육체 건강 팁',
        description: '건강과 생활 개선에 도움 되는 내용',
        color: '#3A7CA5',
        order: 3,
        isDefault: true,
      },
      {
        name: '관심 지식 영역',
        description: '개인 관심사 및 학습 주제',
        color: '#7B5EA7',
        order: 4,
        isDefault: true,
      },
    ]);
  }
}
