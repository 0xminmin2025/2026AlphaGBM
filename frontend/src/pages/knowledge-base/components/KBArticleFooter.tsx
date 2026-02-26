import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import type { KBChapter } from '../types';
import { getAdjacentChapters } from '../data';

interface Props {
  chapterId: string;
}

export default function KBArticleFooter({ chapterId }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';
  const { prev, next } = getAdjacentChapters(chapterId);

  return (
    <div className="mt-12 pt-6 border-t border-white/10">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {prev ? (
          <NavCard chapter={prev} direction="prev" isZh={isZh} />
        ) : (
          <div />
        )}
        {next && <NavCard chapter={next} direction="next" isZh={isZh} />}
      </div>

      {/* CTA */}
      <div className="mt-8 bg-gradient-to-r from-[#0D9B97]/10 to-[#0D9B97]/5 border border-[#0D9B97]/20 rounded-xl p-6 text-center">
        <h3 className="text-lg font-semibold text-[#FAFAFA] mb-2">
          {isZh ? '准备好开始期权分析了吗？' : 'Ready to Analyze Options?'}
        </h3>
        <p className="text-sm text-[#A1A1AA] mb-4">
          {isZh
            ? '使用 AlphaGBM 的 AI 评分系统，发现最优期权机会'
            : "Use AlphaGBM's AI scoring to find optimal opportunities"}
        </p>
        <Link
          to="/options"
          className="inline-flex items-center px-6 py-2.5 bg-[#0D9B97] hover:bg-[#10B5B0] text-white rounded-lg text-sm font-medium transition-colors"
        >
          {isZh ? '开始期权分析' : 'Analyze Options Now'}
        </Link>
      </div>
    </div>
  );
}

function NavCard({
  chapter,
  direction,
  isZh,
}: {
  chapter: KBChapter;
  direction: 'prev' | 'next';
  isZh: boolean;
}) {
  const title = isZh ? chapter.titleZh : chapter.titleEn;
  const shortTitle = title.replace(/^第[一二三四五六七八九十]+章\s*/, '').replace(/^附：/, '').replace(/^Ch\d+:\s*/, '');

  return (
    <Link
      to={`/knowledge/${chapter.slug}`}
      className={`flex items-center gap-3 p-4 rounded-xl border border-white/10 hover:border-[#0D9B97]/30 bg-[#18181B]/50 hover:bg-[#18181B] transition-all group ${
        direction === 'next' ? 'sm:text-right sm:flex-row-reverse' : ''
      }`}
    >
      {direction === 'prev' ? (
        <ArrowLeft size={16} className="text-[#71717A] group-hover:text-[#0D9B97] transition-colors flex-shrink-0" />
      ) : (
        <ArrowRight size={16} className="text-[#71717A] group-hover:text-[#0D9B97] transition-colors flex-shrink-0" />
      )}
      <div className="min-w-0">
        <p className="text-xs text-[#71717A] mb-0.5">
          {direction === 'prev' ? (isZh ? '上一篇' : 'Previous') : (isZh ? '下一篇' : 'Next')}
        </p>
        <p className="text-sm text-[#A1A1AA] group-hover:text-[#FAFAFA] transition-colors truncate">
          {shortTitle}
        </p>
      </div>
    </Link>
  );
}
