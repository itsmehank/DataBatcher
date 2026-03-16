import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose';
import { HydratedDocument } from 'mongoose';

export type AdminDocument = HydratedDocument<Admin>;

@Schema({ timestamps: true })
export class Admin {
  @Prop({ required: true, unique: true, index: true, trim: true, lowercase: true })
  username!: string;

  @Prop({ required: true })
  passwordHash!: string;
}

export const AdminSchema = SchemaFactory.createForClass(Admin);
