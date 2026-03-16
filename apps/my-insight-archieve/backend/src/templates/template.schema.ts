import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type TemplateDocument = HydratedDocument<Template>;

@Schema({ timestamps: true })
export class Template {
  @Prop({ required: true })
  name!: string;

  @Prop({ required: true })
  content!: string;

  @Prop({ default: '' })
  description!: string;

  @Prop({ default: '' })
  useCase!: string;

  @Prop({ type: [String], default: [] })
  tags!: string[];
}

export const TemplateSchema = SchemaFactory.createForClass(Template);
