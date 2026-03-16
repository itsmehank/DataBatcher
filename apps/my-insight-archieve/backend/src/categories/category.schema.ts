import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type CategoryDocument = HydratedDocument<Category>;

@Schema({ timestamps: true })
export class Category {
  @Prop({ required: true, unique: true })
  name!: string;

  @Prop({ default: '' })
  description!: string;

  @Prop({ default: '#4A7C59' })
  color!: string;

  @Prop({ default: 0 })
  order!: number;

  @Prop({ default: false })
  isDefault!: boolean;
}

export const CategorySchema = SchemaFactory.createForClass(Category);
