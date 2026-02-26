import { Link } from 'react-router-dom';
import { BookOpen, ArrowRight } from 'lucide-react';

interface Props {
  slug: string;
  label: string;
  className?: string;
}

export default function KBQuickLink({ slug, label, className = '' }: Props) {
  return (
    <Link
      to={`/knowledge/${slug}`}
      className={`inline-flex items-center gap-1.5 text-sm text-[#0D9B97] hover:text-[#10B5B0] transition-colors group ${className}`}
    >
      <BookOpen size={14} className="flex-shrink-0" />
      <span>{label}</span>
      <ArrowRight size={12} className="opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
    </Link>
  );
}
