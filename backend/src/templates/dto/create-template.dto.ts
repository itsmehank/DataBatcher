export class CreateTemplateDto {
  name!: string;
  content!: string;
  description?: string;
  useCase?: string;
  tags?: string[];
}
