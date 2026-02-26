import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fff]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

interface Props {
  content: string;
}

export default function KBMarkdownRenderer({ content }: Props) {

  const components: Components = {
    h2({ children }) {
      const text = String(children);
      const id = slugify(text);
      return (
        <h2 id={id} className="text-2xl font-semibold text-[#FAFAFA] mt-10 mb-4 scroll-mt-20 border-b border-white/10 pb-3">
          {children}
        </h2>
      );
    },
    h3({ children }) {
      const text = String(children);
      const id = slugify(text);
      return (
        <h3 id={id} className="text-xl font-semibold text-[#FAFAFA] mt-8 mb-3 scroll-mt-20">
          {children}
        </h3>
      );
    },
    h4({ children }) {
      const text = String(children);
      const id = slugify(text);
      return (
        <h4 id={id} className="text-lg font-medium text-[#FAFAFA] mt-6 mb-2 scroll-mt-20">
          {children}
        </h4>
      );
    },
    p({ children }) {
      return <p className="text-[#A1A1AA] leading-7 mb-4">{children}</p>;
    },
    strong({ children }) {
      return <strong className="text-[#FAFAFA] font-semibold">{children}</strong>;
    },
    em({ children }) {
      return <em className="text-[#A1A1AA] italic">{children}</em>;
    },
    a({ href, children }) {
      return (
        <a href={href} className="text-[#0D9B97] hover:text-[#10B5B0] underline underline-offset-2" target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
    ul({ children }) {
      return <ul className="list-disc list-outside ml-6 mb-4 space-y-2 text-[#A1A1AA]">{children}</ul>;
    },
    ol({ children }) {
      return <ol className="list-decimal list-outside ml-6 mb-4 space-y-2 text-[#A1A1AA]">{children}</ol>;
    },
    li({ children }) {
      return <li className="leading-7">{children}</li>;
    },
    blockquote({ children }) {
      return (
        <blockquote className="my-4 border-l-4 border-[#0D9B97] bg-[#0D9B97]/5 rounded-r-lg px-4 py-3 text-[#A1A1AA]">
          {children}
        </blockquote>
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
        <code className={`block bg-[#18181B] border border-white/10 rounded-lg p-4 text-sm font-mono text-[#A1A1AA] overflow-x-auto my-4 ${className}`}>
          {children}
        </code>
      );
    },
    pre({ children }) {
      return <pre className="my-4">{children}</pre>;
    },
    table({ children }) {
      return (
        <div className="overflow-x-auto my-6">
          <table className="w-full text-sm border-collapse">
            {children}
          </table>
        </div>
      );
    },
    thead({ children }) {
      return <thead className="border-b border-white/20">{children}</thead>;
    },
    th({ children }) {
      return <th className="text-left p-3 text-[#FAFAFA] font-semibold bg-[#18181B]">{children}</th>;
    },
    td({ children }) {
      return <td className="p-3 text-[#A1A1AA] border-b border-white/5">{children}</td>;
    },
    hr() {
      return <hr className="my-8 border-white/10" />;
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
      // Strip markdown formatting from heading text
      const text = rawText.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1');
      const id = slugify(text);
      headings.push({ id, text, level });
    }
  }
  return headings;
}
