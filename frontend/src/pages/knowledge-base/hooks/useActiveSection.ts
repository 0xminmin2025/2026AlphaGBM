import { useState, useEffect, useRef } from 'react';

export function useActiveSection(containerRef: React.RefObject<HTMLElement | null>) {
  const [activeId, setActiveId] = useState<string>('');
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Small delay to let markdown render
    const timer = setTimeout(() => {
      const headings = container.querySelectorAll('h2, h3');
      if (headings.length === 0) return;

      observerRef.current = new IntersectionObserver(
        (entries) => {
          // Find the first heading that is intersecting from top
          const visibleEntries = entries.filter((e) => e.isIntersecting);
          if (visibleEntries.length > 0) {
            setActiveId(visibleEntries[0].target.id);
          }
        },
        {
          // Account for sticky header (64px) + some buffer
          rootMargin: '-80px 0px -70% 0px',
          threshold: 0,
        }
      );

      headings.forEach((heading) => {
        if (heading.id) {
          observerRef.current?.observe(heading);
        }
      });
    }, 100);

    return () => {
      clearTimeout(timer);
      observerRef.current?.disconnect();
    };
  }, [containerRef]);

  return activeId;
}
