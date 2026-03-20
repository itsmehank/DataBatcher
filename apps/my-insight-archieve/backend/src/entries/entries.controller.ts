import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  Query,
  Req,
  UseGuards,
} from '@nestjs/common';
import { EntriesService } from './entries.service';
import { JwtAuthGuard } from '../common/jwt-auth.guard';
import { CreateEntryDto } from './dto/create-entry.dto';
import { UpdateEntryDto } from './dto/update-entry.dto';
import { CreateCommentDto } from './dto/create-comment.dto';
import { UpdateCommentDto } from './dto/update-comment.dto';

@Controller('entries')
export class EntriesController {
  constructor(private readonly entriesService: EntriesService) {}

  @Get()
  findAll(
    @Query('categoryId') categoryId?: string,
    @Query('q') q?: string,
    @Query('source') source?: string,
  ) {
    return this.entriesService.findAll({ categoryId, q, source });
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.entriesService.findOne(id);
  }

  @UseGuards(JwtAuthGuard)
  @Post()
  create(@Body() body: CreateEntryDto, @Req() req: { user: { username: string } }) {
    return this.entriesService.create(body, req.user.username);
  }

  @UseGuards(JwtAuthGuard)
  @Patch(':id')
  update(@Param('id') id: string, @Body() body: UpdateEntryDto) {
    return this.entriesService.update(id, body);
  }

  @UseGuards(JwtAuthGuard)
  @Delete(':id')
  delete(@Param('id') id: string, @Req() req: { user: { username: string } }) {
    return this.entriesService.delete(id, req.user.username);
  }

  @UseGuards(JwtAuthGuard)
  @Post(':id/comments')
  addComment(
    @Param('id') id: string,
    @Body() body: CreateCommentDto,
    @Req() req: { user: { username: string } },
  ) {
    return this.entriesService.addComment(id, body, req.user.username);
  }

  @UseGuards(JwtAuthGuard)
  @Patch(':id/comments/:commentId')
  updateComment(
    @Param('id') id: string,
    @Param('commentId') commentId: string,
    @Body() body: UpdateCommentDto,
    @Req() req: { user: { username: string } },
  ) {
    return this.entriesService.updateComment(id, commentId, body, req.user.username);
  }

  @UseGuards(JwtAuthGuard)
  @Delete(':id/comments/:commentId')
  deleteComment(
    @Param('id') id: string,
    @Param('commentId') commentId: string,
    @Req() req: { user: { username: string } },
  ) {
    return this.entriesService.deleteComment(id, commentId, req.user.username);
  }
}
