import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ChevronRight } from 'lucide-react';
import type { KBCategory, KBChapter } from '../types';

interface Props {
  category: KBCategory;
  chapter: KBChapter;
}

export default function KBBreadcrumb({ category, chapter }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  return (
    <nav className="flex items-center gap-1.5 text-sm text-[#71717A] mb-4 flex-wrap">
      <Link to="/knowledge" className="hover:text-[#0D9B97] transition-colors">
        {isZh ? '知识库' : 'Knowledge Base'}
      </Link>
      <ChevronRight size={14} />
      <span className="text-[#A1A1AA]">{isZh ? category.titleZh : category.titleEn}</span>
      <ChevronRight size={14} />
      <span className="text-[#FAFAFA]">
        {isZh
          ? chapter.titleZh.replace(/^第[一二三四五六七八九十]+章\s*/, '').replace(/^附：/, '')
          : chapter.titleEn.replace(/^Ch\d+:\s*/, '')}
      </span>
    </nav>
  );
}
