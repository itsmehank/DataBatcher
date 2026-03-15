import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Template } from './template.schema';
import { CreateTemplateDto } from './dto/create-template.dto';
import { UpdateTemplateDto } from './dto/update-template.dto';

@Injectable()
export class TemplatesService {
  constructor(
    @InjectModel(Template.name) private readonly templateModel: Model<Template>,
  ) {}

  findAll(query: { q?: string; tag?: string }) {
    const filter: Record<string, unknown> = {};
    if (query.q) {
      filter.$or = [
        { name: { $regex: query.q, $options: 'i' } },
        { content: { $regex: query.q, $options: 'i' } },
        { description: { $regex: query.q, $options: 'i' } },
      ];
    }
    if (query.tag) {
      filter.tags = query.tag;
    }
    return this.templateModel.find(filter).sort({ updatedAt: -1 }).lean();
  }

  async findOne(id: string) {
    const template = await this.templateModel.findById(id).lean();
    if (!template) {
      throw new NotFoundException('템플릿을 찾을 수 없습니다.');
    }
    return template;
  }

  create(dto: CreateTemplateDto) {
    return this.templateModel.create({
      ...dto,
      description: dto.description || '',
      useCase: dto.useCase || '',
      tags: dto.tags || [],
    });
  }

  async update(id: string, dto: UpdateTemplateDto) {
    const updated = await this.templateModel
      .findByIdAndUpdate(id, dto, { new: true })
      .lean();
    if (!updated) {
      throw new NotFoundException('템플릿을 찾을 수 없습니다.');
    }
    return updated;
  }

  async delete(id: string) {
    const deleted = await this.templateModel.findByIdAndDelete(id).lean();
    if (!deleted) {
      throw new NotFoundException('템플릿을 찾을 수 없습니다.');
    }
    return { ok: true };
  }
}
