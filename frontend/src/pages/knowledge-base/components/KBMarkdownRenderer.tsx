import { Children, isValidElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';
import { AlertTriangle, Lightbulb } from 'lucide-react';

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Extract plain text from React children
function extractText(children: React.ReactNode): string {
  let text = '';
  Children.forEach(children, (child) => {
    if (typeof child === 'string') {
      text += child;
    } else if (isValidElement(child) && (child.props as Record<string, unknown>)?.children) {
      text += extractText((child.props as Record<string, unknown>).children as React.ReactNode);
    }
  });
  return text;
}

// Warning keywords that trigger amber-styled blockquote
const WARNING_KEYWORDS = ['务必', '牢记', '建议新手', '严格规避', '大忌', '切记', '危害', '注意', '风险'];

interface Props {
  content: string;
}

export default function KBMarkdownRenderer({ content }: Props) {

  const components: Components = {
    h2({ children }) {
      const text = String(children);
      const id = slugify(text);
      return (
        <h2 id={id} className="text-2xl font-semibold text-[#FAFAFA] mt-12 mb-5 scroll-mt-20 border-b border-white/10 pb-3">
          {children}
        </h2>
      );
    },
    h3({ children }) {
      const text = String(children);
      const id = slugify(text);
      return (
        <h3 id={id} className="text-xl font-semibold text-[#FAFAFA] mt-9 mb-4 scroll-mt-20">
          {children}
        </h3>
      );
    },
    h4({ children }) {
      const text = String(children);
      const id = slugify(text);
      return (
        <h4 id={id} className="text-lg font-medium text-[#FAFAFA] mt-7 mb-3 scroll-mt-20">
          {children}
        </h4>
      );
    },
    p({ children }) {
      return <p className="text-[#A1A1AA] leading-[1.8] mb-5">{children}</p>;
    },
    strong({ children }) {
      return <strong className="text-[#FAFAFA] font-semibold">{children}</strong>;
    },
    em({ children }) {
      return <em className="text-[#A1A1AA] italic">{children}</em>;
    },
    a({ href, children }) {
      return (
        <a href={href} className="text-[#0D9B97] hover:text-[#10B5B0] underline underline-offset-2 transition-colors" target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
    ul({ children }) {
      return <ul className="list-disc list-outside ml-6 mb-5 space-y-2.5 text-[#A1A1AA]">{children}</ul>;
    },
    ol({ children }) {
      return <ol className="list-decimal list-outside ml-6 mb-5 space-y-2.5 text-[#A1A1AA]">{children}</ol>;
    },
    li({ children }) {
      return <li className="leading-[1.8] pl-1">{children}</li>;
    },
    blockquote({ children }) {
      // Detect warning vs tip by scanning text content
      const text = extractText(children);
      const isWarning = WARNING_KEYWORDS.some((kw) => text.includes(kw));

      if (isWarning) {
        return (
          <div className="my-5 flex gap-3 rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/5 px-4 py-4">
            <div className="flex-shrink-0 mt-0.5">
              <div className="w-7 h-7 rounded-full bg-[#F59E0B]/20 flex items-center justify-center">
                <AlertTriangle size={14} className="text-[#F59E0B]" />
              </div>
            </div>
            <div className="text-[#A1A1AA] leading-[1.8] [&>p]:mb-1 [&>p:last-child]:mb-0">
              {children}
            </div>
          </div>
        );
      }

      return (
        <div className="my-5 flex gap-3 rounded-xl border border-[#0D9B97]/20 bg-[#0D9B97]/5 px-4 py-4">
          <div className="flex-shrink-0 mt-0.5">
            <div className="w-7 h-7 rounded-full bg-[#0D9B97]/20 flex items-center justify-center">
              <Lightbulb size={14} className="text-[#0D9B97]" />
            </div>
          </div>
          <div className="text-[#A1A1AA] leading-[1.8] [&>p]:mb-1 [&>p:last-child]:mb-0">
            {children}
          </div>
        </div>
      );
    },
    code({ className, children }) {
      const isInline = !className;
      if (isInline) {
        return (
          <code className="bg-[#27272A] text-[#0D9B97] px-1.5 py-0.5 rounded text-sm font-mono">
            {children}
          </code>
        );
      }
      return (
        <code className={`block bg-[#18181B] border border-white/10 rounded-xl p-4 text-sm font-mono text-[#A1A1AA] overflow-x-auto my-5 ${className}`}>
          {children}
        </code>
      );
    },
    pre({ children }) {
      return <pre className="my-5">{children}</pre>;
    },
    table({ children }) {
      return (
        <div className="overflow-x-auto my-6 rounded-xl border border-white/10">
          <table className="w-full text-sm border-collapse">
            {children}
          </table>
        </div>
      );
    },
    thead({ children }) {
      return <thead className="bg-[#18181B]">{children}</thead>;
    },
    th({ children }) {
      return <th className="text-left p-3.5 text-[#FAFAFA] font-semibold border-b border-white/10">{children}</th>;
    },
    td({ children }) {
      return <td className="p-3.5 text-[#A1A1AA] border-b border-white/5">{children}</td>;
    },
    tr({ children }) {
      return <tr className="hover:bg-[#27272A]/30 transition-colors">{children}</tr>;
    },
    hr() {
      return <hr className="my-10 border-white/10" />;
    },
  };

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  );
}

// Utility: extract headings from markdown content (for TOC)
export function extractHeadings(content: string): { id: string; text: string; level: number }[] {
  const headings: { id: string; text: string; level: number }[] = [];
  const lines = content.split('\n');
  for (const line of lines) {
    const match = line.match(/^(#{2,3})\s+(.+)$/);
    if (match) {
      const level = match[1].length;
      const rawText = match[2];
      const text = rawText.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1');
      const id = slugify(text);
      headings.push({ id, text, level });
    }
  }
  return headings;
}
