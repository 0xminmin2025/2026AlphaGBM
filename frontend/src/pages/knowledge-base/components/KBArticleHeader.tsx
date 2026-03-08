import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Clock, Calendar, Share2, Bookmark, Check } from 'lucide-react';
import type { KBChapter } from '../types';

interface Props {
  chapter: KBChapter;
}

export default function KBArticleHeader({ chapter }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';
  const [copied, setCopied] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="mb-8">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-3xl font-bold text-[#FAFAFA] leading-tight flex-1">
          {isZh ? chapter.titleZh : chapter.titleEn}
        </h1>
        <div className="flex items-center gap-1.5 flex-shrink-0 mt-1">
          <button
            onClick={handleShare}
            title={isZh ? '复制链接' : 'Copy link'}
            className="p-2 rounded-lg text-[#71717A] hover:text-[#FAFAFA] hover:bg-[#27272A] transition-all"
          >
            {copied ? <Check size={16} className="text-[#10B981]" /> : <Share2 size={16} />}
          </button>
          <button
            onClick={() => setBookmarked(!bookmarked)}
            title={isZh ? '收藏' : 'Bookmark'}
            className={`p-2 rounded-lg transition-all ${
              bookmarked
                ? 'text-[#F59E0B] bg-[#F59E0B]/10'
                : 'text-[#71717A] hover:text-[#FAFAFA] hover:bg-[#27272A]'
            }`}
          >
            <Bookmark size={16} fill={bookmarked ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>
      <div className="flex items-center gap-4 text-sm text-[#71717A] mt-4">
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
