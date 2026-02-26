import { X } from 'lucide-react';
import KBLeftSidebar from './KBLeftSidebar';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  activeSlug: string;
}

export default function KBMobileNav({ isOpen, onClose, activeSlug }: Props) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 z-40 lg:hidden" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed inset-y-0 left-0 w-80 max-w-[85vw] z-50 lg:hidden bg-[#18181B] shadow-2xl">
        <div className="flex items-center justify-end p-3 border-b border-white/10">
          <button onClick={onClose} className="p-1 text-[#71717A] hover:text-[#FAFAFA] transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="h-[calc(100%-3.5rem)] overflow-y-auto" onClick={onClose}>
          <KBLeftSidebar activeSlug={activeSlug} />
        </div>
      </div>
    </>
  );
}
