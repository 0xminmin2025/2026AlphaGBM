import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronRight, Search, Lock, BookOpen, Target, Zap, Monitor, PenLine } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { kbCategories } from '../data';
import type { KBCategory, KBChapter } from '../types';
import { useHasAccess } from '@/components/BlurOverlay';

interface Props {
  activeSlug: string;
}

const iconMap: Record<string, { icon: LucideIcon; color: string }> = {
  BookOpen: { icon: BookOpen, color: '#0D9B97' },
  Target: { icon: Target, color: '#F59E0B' },
  Zap: { icon: Zap, color: '#8B5CF6' },
  Monitor: { icon: Monitor, color: '#3B82F6' },
  PenLine: { icon: PenLine, color: '#10B981' },
};

function CategoryIcon({ name }: { name: string }) {
  const entry = iconMap[name];
  if (!entry) return null;
  const Icon = entry.icon;
  return (
    <div
      className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
      style={{ backgroundColor: `${entry.color}15`, border: `1px solid ${entry.color}25` }}
    >
      <Icon size={13} style={{ color: entry.color }} />
    </div>
  );
}

export default function KBLeftSidebar({ activeSlug }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';
  const [search, setSearch] = useState('');

  // Find which category the active chapter belongs to
  const activeCategoryId = useMemo(() => {
    for (const cat of kbCategories) {
      if (cat.chapters.some((ch) => ch.slug === activeSlug)) {
        return cat.id;
      }
    }
    return kbCategories[0]?.id;
  }, [activeSlug]);

  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set([activeCategoryId])
  );

  const toggleCategory = (catId: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(catId)) {
        next.delete(catId);
      } else {
        next.add(catId);
      }
      return next;
    });
  };

  // Filter categories and chapters by search
  const filteredCategories = useMemo(() => {
    if (!search.trim()) return kbCategories;
    const q = search.toLowerCase();
    return kbCategories
      .map((cat) => ({
        ...cat,
        chapters: cat.chapters.filter(
          (ch) =>
            ch.titleZh.toLowerCase().includes(q) ||
            ch.titleEn.toLowerCase().includes(q)
        ),
      }))
      .filter((cat) => cat.chapters.length > 0);
  }, [search]);

  return (
    <aside className="w-full h-full bg-[#18181B]/50 border-r border-white/10 flex flex-col">
      {/* Title */}
      <div className="px-4 pt-5 pb-3">
        <h2 className="text-lg font-semibold text-[#FAFAFA]">
          {isZh ? '知识库' : 'Knowledge Base'}
        </h2>
      </div>

      {/* Search */}
      <div className="px-4 pb-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={isZh ? '搜索知识库...' : 'Search...'}
            className="w-full bg-[#09090B] border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm text-[#FAFAFA] placeholder:text-[#71717A] focus:outline-none focus:border-[#0D9B97] transition-colors"
          />
        </div>
      </div>

      {/* Navigation Tree */}
      <nav className="flex-1 overflow-y-auto px-2 pb-4">
        {filteredCategories.map((cat) => (
          <CategoryGroup
            key={cat.id}
            category={cat}
            isExpanded={expandedCategories.has(cat.id) || search.trim().length > 0}
            onToggle={() => toggleCategory(cat.id)}
            activeSlug={activeSlug}
            isZh={isZh}
          />
        ))}
      </nav>
    </aside>
  );
}

function CategoryGroup({
  category,
  isExpanded,
  onToggle,
  activeSlug,
  isZh,
}: {
  category: KBCategory;
  isExpanded: boolean;
  onToggle: () => void;
  activeSlug: string;
  isZh: boolean;
}) {
  return (
    <div className="mb-1">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-semibold text-[#A1A1AA] hover:bg-[#27272A]/70 hover:text-[#FAFAFA] transition-all duration-200"
      >
        <CategoryIcon name={category.icon} />
        <span className="flex-1 text-left truncate">{isZh ? category.titleZh : category.titleEn}</span>
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {isExpanded && (
        <div className="ml-2 mt-0.5 space-y-0.5">
          {category.chapters.map((ch) => (
            <ChapterNavItem key={ch.id} chapter={ch} isActive={ch.slug === activeSlug} isZh={isZh} />
          ))}
        </div>
      )}
    </div>
  );
}

function ChapterNavItem({
  chapter,
  isActive,
  isZh,
}: {
  chapter: KBChapter;
  isActive: boolean;
  isZh: boolean;
}) {
  const hasAccess = useHasAccess(chapter.accessLevel);
  const title = isZh ? chapter.titleZh : chapter.titleEn;
  // Truncate long titles for display
  const shortTitle = title.replace(/^第[一二三四五六七八九十]+章\s*/, '').replace(/^附：/, '');

  return (
    <Link
      to={`/knowledge/${chapter.slug}`}
      className={`flex items-center gap-2 px-3 py-2 text-sm transition-all duration-200 ${
        isActive
          ? 'bg-[#0D9B97]/10 text-[#0D9B97] border-l-[3px] border-[#0D9B97] font-medium rounded-r-lg'
          : 'text-[#71717A] hover:text-[#A1A1AA] hover:bg-[#27272A]/50 border-l-[3px] border-transparent rounded-lg'
      }`}
    >
      <span className="flex-1 truncate">{shortTitle}</span>
      {!hasAccess && <Lock size={12} className="text-[#71717A] flex-shrink-0" />}
    </Link>
  );
}
