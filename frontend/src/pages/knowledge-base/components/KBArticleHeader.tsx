import { useTranslation } from 'react-i18next';
import { Clock, Calendar } from 'lucide-react';
import type { KBChapter } from '../types';

interface Props {
  chapter: KBChapter;
}

export default function KBArticleHeader({ chapter }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-[#FAFAFA] mb-4 leading-tight">
        {isZh ? chapter.titleZh : chapter.titleEn}
      </h1>
      <div className="flex items-center gap-4 text-sm text-[#71717A]">
        <span className="flex items-center gap-1.5">
          <Calendar size={14} />
          {chapter.updatedAt}
        </span>
        <span className="flex items-center gap-1.5">
          <Clock size={14} />
          {isZh ? `${chapter.readTimeMin} 分钟阅读` : `${chapter.readTimeMin} min read`}
        </span>
      </div>
    </div>
  );
}
