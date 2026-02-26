import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import { Menu } from 'lucide-react';
import { findChapterBySlug, findCategoryByChapterId, loadChapterContent, allChapters } from './data';
import { useActiveSection } from './hooks/useActiveSection';
import { extractHeadings } from './components/KBMarkdownRenderer';
import KBLeftSidebar from './components/KBLeftSidebar';
import KBBreadcrumb from './components/KBBreadcrumb';
import KBArticleHeader from './components/KBArticleHeader';
import KBMarkdownRenderer from './components/KBMarkdownRenderer';
import KBArticleFooter from './components/KBArticleFooter';
import KBRightSidebar from './components/KBRightSidebar';
import KBMobileNav from './components/KBMobileNav';
import { BlurOverlay, useHasAccess } from '@/components/BlurOverlay';
import { BuffettCaseStudy, SellPutExample } from './components/KBCaseStudyCard';
import KBScoringBreakdown from './components/KBScoringBreakdown';
import KBRiskMetricsTable from './components/KBRiskMetricsTable';
import { SellPutStepGuide } from './components/KBStepGuide';
import KBStrategyFlowDiagram, { WheelStrategyCycle } from './components/KBStrategyFlowDiagram';

// Rich visual components mapped to chapter IDs — inserted after markdown content
function ChapterVisuals({ chapterId }: { chapterId: string }) {
  switch (chapterId) {
    case 'preface':
      return <BuffettCaseStudy />;
    case 'ch03':
      return (
        <>
          <KBStrategyFlowDiagram />
          <SellPutExample />
          <KBRiskMetricsTable />
        </>
      );
    case 'ch04':
      return <SellPutStepGuide />;
    case 'ch05':
      return <WheelStrategyCycle />;
    case 'ch06':
      return <KBScoringBreakdown />;
    default:
      return null;
  }
}

export default function KnowledgeBasePage() {
  const { chapterSlug } = useParams<{ chapterSlug?: string }>();
  const navigate = useNavigate();
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  // Default to first chapter if no slug
  const slug = chapterSlug || allChapters[0]?.slug || 'preface';
  const chapter = findChapterBySlug(slug);
  const category = chapter ? findCategoryByChapterId(chapter.id) : undefined;

  // Redirect if invalid slug
  useEffect(() => {
    if (!chapter && chapterSlug) {
      navigate('/knowledge', { replace: true });
    }
  }, [chapter, chapterSlug, navigate]);

  // Content loading
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!chapter) return;
    setIsLoading(true);
    setContent('');
    loadChapterContent(chapter.fileId)
      .then((md) => {
        setContent(md);
        setIsLoading(false);
        // Scroll to top on chapter change
        window.scrollTo(0, 0);
      })
      .catch(() => {
        setContent('');
        setIsLoading(false);
      });
  }, [chapter]);

  // Extract headings for TOC
  const headings = useMemo(() => extractHeadings(content), [content]);

  // Active section tracking
  const contentRef = useRef<HTMLDivElement>(null);
  const activeId = useActiveSection(contentRef);

  // Mobile nav
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Access control
  const hasAccess = useHasAccess(chapter?.accessLevel ?? 'guest');

  if (!chapter || !category) {
    return null;
  }

  return (
    <>
      <Helmet>
        <title>{isZh ? chapter.titleZh : chapter.titleEn} - AlphaGBM</title>
        <meta
          name="description"
          content={isZh ? `AlphaGBM知识库 - ${chapter.titleZh}` : `AlphaGBM Knowledge Base - ${chapter.titleEn}`}
        />
      </Helmet>

      <div className="min-h-[calc(100vh-4rem)] flex">
        {/* Left Sidebar - Desktop */}
        <div className="hidden lg:block w-[280px] flex-shrink-0 border-r border-white/10">
          <div className="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto">
            <KBLeftSidebar activeSlug={slug} />
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {/* Mobile menu button */}
          <div className="lg:hidden sticky top-16 z-30 bg-[#09090B]/90 backdrop-blur-sm border-b border-white/10 px-4 py-2">
            <button
              onClick={() => setMobileNavOpen(true)}
              className="flex items-center gap-2 text-sm text-[#A1A1AA] hover:text-[#FAFAFA] transition-colors"
            >
              <Menu size={18} />
              <span>{isZh ? '知识库导航' : 'Navigation'}</span>
            </button>
          </div>

          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8" ref={contentRef}>
            <KBBreadcrumb category={category} chapter={chapter} />
            <KBArticleHeader chapter={chapter} />

            {isLoading ? (
              <div className="space-y-4 animate-pulse">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-4 bg-[#27272A] rounded w-full" style={{ width: `${80 + Math.random() * 20}%` }} />
                ))}
              </div>
            ) : hasAccess ? (
              <>
                <KBMarkdownRenderer content={content} />
                <ChapterVisuals chapterId={chapter.id} />
              </>
            ) : (
              <>
                {/* Show first portion as teaser */}
                <KBMarkdownRenderer content={content.split('\n').slice(0, 8).join('\n')} />
                <BlurOverlay
                  requiredTier={chapter.accessLevel}
                  feature="knowledge-base"
                  ctaText={isZh ? '登录解锁完整内容' : 'Sign in to unlock'}
                >
                  <KBMarkdownRenderer content={content.split('\n').slice(8).join('\n')} />
                </BlurOverlay>
              </>
            )}

            {hasAccess && <KBArticleFooter chapterId={chapter.id} />}
          </div>
        </div>

        {/* Right Sidebar - Desktop */}
        <div className="hidden xl:block w-[240px] flex-shrink-0 border-l border-white/10">
          <div className="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto">
            <KBRightSidebar headings={headings} activeId={activeId} />
          </div>
        </div>
      </div>

      {/* Mobile Nav Drawer */}
      <KBMobileNav isOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} activeSlug={slug} />
    </>
  );
}
