// Types principaux pour LEXO v1

export interface Document {
  id: string;
  filename: string;
  category: DocumentCategory;
  dateDocument: Date;
  dateIndexation: Date;
  confidenceScore: number;
  entities: string[];
  amount?: number;
  customTags: string[];
  ocrText: string;
  embeddings?: number[];
}

export enum DocumentCategory {
  FACTURES = 'factures',
  IMPOTS = 'impots',
  RIB = 'rib',
  PIECES_IDENTITE = 'pieces_identite',
  CONTRATS = 'contrats',
  COURRIERS = 'courriers',
  RELEVES_BANCAIRES = 'releves_bancaires',
  NON_CLASSES = 'non_classes',
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  createdAt: Date;
  lastLogin?: Date;
}

export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  READONLY = 'readonly',
}

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  success: boolean;
}

export interface UploadProgress {
  progress: number;
  filename: string;
  status: 'uploading' | 'processing' | 'complete' | 'error';
}