import { BadRequestException, ForbiddenException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model, Types } from 'mongoose';
import { Entry } from './entry.schema';
import { CreateEntryDto } from './dto/create-entry.dto';
import { UpdateEntryDto } from './dto/update-entry.dto';
import { CreateCommentDto } from './dto/create-comment.dto';
import { UpdateCommentDto } from './dto/update-comment.dto';

@Injectable()
export class EntriesService {
  constructor(@InjectModel(Entry.name) private readonly entryModel: Model<Entry>) {}

  findAll(query: { categoryId?: string; q?: string; source?: string }) {
    const filter: Record<string, unknown> = {};

    if (query.categoryId) {
      filter.categoryId = new Types.ObjectId(query.categoryId);
    }
    if (query.source) {
      filter.source = query.source;
    }
    if (query.q) {
      filter.$or = [
        { title: { $regex: query.q, $options: 'i' } },
        { content: { $regex: query.q, $options: 'i' } },
        { memo: { $regex: query.q, $options: 'i' } },
      ];
    }

    return this.entryModel.find(filter).sort({ createdAt: -1 }).lean();
  }

  async findOne(id: string) {
    const entry = await this.entryModel.findById(id).lean();
    if (!entry) {
      throw new NotFoundException('항목을 찾을 수 없습니다.');
    }
    return entry;
  }

  create(dto: CreateEntryDto, createdBy: string) {
    return this.entryModel.create({
      ...dto,
      createdBy,
      categoryId: new Types.ObjectId(dto.categoryId),
      tags: dto.tags || [],
      memo: dto.memo || '',
    });
  }

  async update(id: string, dto: UpdateEntryDto) {
    const updateData: Record<string, unknown> = { ...dto };
    if (dto.categoryId) {
      updateData.categoryId = new Types.ObjectId(dto.categoryId);
    }
    const updated = await this.entryModel
      .findByIdAndUpdate(id, updateData, { new: true })
      .lean();
    if (!updated) {
      throw new NotFoundException('항목을 찾을 수 없습니다.');
    }
    return updated;
  }

  async delete(id: string, username: string) {
    const target = await this.entryModel.findById(id).lean();
    if (!target) {
      throw new NotFoundException('항목을 찾을 수 없습니다.');
    }
    if (target.createdBy !== username) {
      throw new ForbiddenException('본인이 작성한 기록만 삭제할 수 있습니다.');
    }

    const deleted = await this.entryModel.findByIdAndDelete(id).lean();
    if (!deleted) {
      throw new NotFoundException('항목을 찾을 수 없습니다.');
    }
    return { ok: true };
  }

  async addComment(id: string, dto: CreateCommentDto, author: string) {
    const content = dto.content.trim();
    if (!content) {
      throw new BadRequestException('댓글 내용을 입력해 주세요.');
    }

    const entry = await this.entryModel.findById(id);
    if (!entry) {
      throw new NotFoundException('항목을 찾을 수 없습니다.');
    }

    const now = new Date();
    entry.comments.push({
      id: new Types.ObjectId().toString(),
      author,
      content,
      createdAt: now,
      updatedAt: now,
    });
    await entry.save();

    return entry.toObject();
  }

  async updateComment(id: string, commentId: string, dto: UpdateCommentDto, author: string) {
    const content = dto.content.trim();
    if (!content) {
      throw new BadRequestException('댓글 내용을 입력해 주세요.');
    }

    const entry = await this.entryModel.findById(id);
    if (!entry) {
      throw new NotFoundException('항목을 찾을 수 없습니다.');
    }

    const target = entry.comments.find((comment) => comment.id === commentId);
    if (!target) {
      throw new NotFoundException('댓글을 찾을 수 없습니다.');
    }
    if (target.author !== author) {
      throw new ForbiddenException('본인이 작성한 댓글만 수정할 수 있습니다.');
    }

    target.content = content;
    target.updatedAt = new Date();
    await entry.save();

    return entry.toObject();
  }

  async deleteComment(id: string, commentId: string, author: string) {
    const entry = await this.entryModel.findById(id);
    if (!entry) {
      throw new NotFoundException('항목을 찾을 수 없습니다.');
    }

    const target = entry.comments.find((comment) => comment.id === commentId);
    if (!target) {
      throw new NotFoundException('댓글을 찾을 수 없습니다.');
    }
    if (target.author !== author) {
      throw new ForbiddenException('본인이 작성한 댓글만 삭제할 수 있습니다.');
    }

    entry.comments = entry.comments.filter((comment) => comment.id !== commentId);
    await entry.save();

    return entry.toObject();
  }
}
