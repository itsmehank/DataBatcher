import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument, Types } from 'mongoose';

export type EntryDocument = HydratedDocument<Entry>;

@Schema({ timestamps: true })
export class Entry {
  @Prop({ required: true, index: true })
  createdBy!: string;

  @Prop({ required: true })
  title!: string;

  @Prop({ required: true })
  content!: string;

  @Prop({ default: '' })
  memo!: string;

  @Prop({ required: true })
  conversationUrl!: string;

  @Prop({ required: true, enum: ['chatgpt', 'claude', 'gemini', 'other'] })
  source!: 'chatgpt' | 'claude' | 'gemini' | 'other';

  @Prop({ type: Types.ObjectId, ref: 'Category', required: true })
  categoryId!: Types.ObjectId;

  @Prop({ type: [String], default: [] })
  tags!: string[];

  @Prop({
    type: [
      {
        id: { type: String, required: true },
        author: { type: String, required: true },
        content: { type: String, required: true },
        createdAt: { type: Date, required: true },
        updatedAt: { type: Date, required: true },
      },
    ],
    default: [],
  })
  comments!: {
    id: string;
    author: string;
    content: string;
    createdAt: Date;
    updatedAt: Date;
  }[];
}

export const EntrySchema = SchemaFactory.createForClass(Entry);
