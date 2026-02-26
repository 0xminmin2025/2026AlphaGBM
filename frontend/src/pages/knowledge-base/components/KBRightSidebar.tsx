import { useTranslation } from 'react-i18next';
import { useReadingProgress } from '../hooks/useReadingProgress';

interface Heading {
  id: string;
  text: string;
  level: number;
}

interface Props {
  headings: Heading[];
  activeId: string;
}

export default function KBRightSidebar({ headings, activeId }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';
  const progress = useReadingProgress();

  if (headings.length === 0) return null;

  const handleClick = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <aside className="w-full h-full">
      <div className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
        <div className="px-4 pt-5">
          <h3 className="text-sm font-semibold text-[#FAFAFA] mb-4">
            {isZh ? '目录' : 'Table of Contents'}
          </h3>

          <nav className="space-y-1">
            {headings.map((h) => (
              <button
                key={h.id}
                onClick={() => handleClick(h.id)}
                className={`block w-full text-left text-sm py-1.5 transition-all duration-200 border-l-2 rounded-r-md ${
                  h.level === 3 ? 'pl-6' : 'pl-3'
                } ${
                  activeId === h.id
                    ? 'border-[#0D9B97] text-[#0D9B97] font-medium bg-[#0D9B97]/8'
                    : 'border-transparent text-[#71717A] hover:text-[#A1A1AA] hover:border-white/20 hover:bg-[#27272A]/30'
                }`}
              >
                <span className="line-clamp-2">{h.text}</span>
              </button>
            ))}
          </nav>

          {/* Reading Progress */}
          <div className="mt-6 pt-4 border-t border-white/10">
            <div className="flex items-center justify-between text-xs text-[#71717A] mb-2">
              <span>{isZh ? '阅读进度' : 'Reading Progress'}</span>
              <span className="text-[#0D9B97] font-medium">{progress}%</span>
            </div>
            <div className="w-full h-1.5 bg-[#27272A] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#0D9B97] rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
