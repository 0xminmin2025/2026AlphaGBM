import type { UserTier } from '@/components/BlurOverlay';

export interface KBSection {
  id: string;
  titleZh: string;
  titleEn: string;
}

export interface KBChapter {
  id: string;
  slug: string;
  fileId: string;
  titleZh: string;
  titleEn: string;
  accessLevel: UserTier;
  readTimeMin: number;
  updatedAt: string;
  sections: KBSection[];
}

export interface KBCategory {
  id: string;
  titleZh: string;
  titleEn: string;
  icon: string;
  chapters: KBChapter[];
}
