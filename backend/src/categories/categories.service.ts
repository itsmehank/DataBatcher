import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectConnection, InjectModel } from '@nestjs/mongoose';
import { Connection, Model } from 'mongoose';
import { Category } from './category.schema';
import { CreateCategoryDto } from './dto/create-category.dto';
import { UpdateCategoryDto } from './dto/update-category.dto';

@Injectable()
export class CategoriesService {
  constructor(
    @InjectModel(Category.name) private readonly categoryModel: Model<Category>,
    @InjectConnection() private readonly connection: Connection,
  ) {}

  findAll() {
    return this.categoryModel.find().sort({ order: 1, createdAt: 1 }).lean();
  }

  create(dto: CreateCategoryDto) {
    return this.categoryModel.create({
      name: dto.name,
      description: dto.description || '',
      color: dto.color || '#4A7C59',
      order: dto.order || 0,
      isDefault: false,
    });
  }

  async update(id: string, dto: UpdateCategoryDto) {
    const category = await this.categoryModel
      .findByIdAndUpdate(id, dto, { new: true })
      .lean();
    if (!category) {
      throw new NotFoundException('카테고리를 찾을 수 없습니다.');
    }
    return category;
  }

  async delete(id: string) {
    const target = await this.categoryModel.findById(id).lean();
    if (!target) {
      throw new NotFoundException('카테고리를 찾을 수 없습니다.');
    }

    let uncategorized = await this.categoryModel
      .findOne({ name: '미분류' })
      .lean();

    if (!uncategorized) {
      uncategorized = await this.categoryModel.create({
        name: '미분류',
        description: '카테고리가 지정되지 않은 항목',
        color: '#A7A7A7',
        order: 999,
        isDefault: true,
      });
    }

    await this.connection
      .collection('entries')
      .updateMany(
        { categoryId: target._id },
        { $set: { categoryId: uncategorized._id } },
      );

    await this.categoryModel.findByIdAndDelete(id);

    return { ok: true };
  }
}
