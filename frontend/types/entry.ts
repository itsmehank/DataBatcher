export type EntryComment = {
  id: string;
  author: string;
  content: string;
  createdAt: string;
  updatedAt: string;
};

export type Entry = {
  _id: string;
  title: string;
  content: string;
  memo: string;
  source: string;
  conversationUrl: string;
  tags: string[];
  createdAt?: string;
  categoryId?: string;
  createdBy?: string;
  comments?: EntryComment[];
};
