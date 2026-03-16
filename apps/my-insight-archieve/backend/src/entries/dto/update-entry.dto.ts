export class UpdateEntryDto {
  title?: string;
  content?: string;
  memo?: string;
  conversationUrl?: string;
  source?: 'chatgpt' | 'claude' | 'gemini' | 'other';
  categoryId?: string;
  tags?: string[];
}
