import type { KBCategory, KBChapter } from './types';

export const kbCategories: KBCategory[] = [
  {
    id: 'getting-started',
    titleZh: '入门指南',
    titleEn: 'Getting Started',
    icon: 'BookOpen',
    chapters: [
      {
        id: 'preface',
        slug: 'preface',
        fileId: 'preface',
        titleZh: '前言：巴菲特的期权智慧与投资哲学',
        titleEn: "Preface: Buffett's Options Wisdom",
        accessLevel: 'guest',
        readTimeMin: 3,
        updatedAt: '2026-02-26',
        sections: [
          { id: 'scenario-a', titleZh: '情景A与情景B', titleEn: 'Scenario A & B' },
          { id: 'options-charm', titleZh: '期权交易的独特魅力', titleEn: 'The Charm of Options' },
        ],
      },
      {
        id: 'ch01',
        slug: 'risk-myths',
        fileId: 'ch01-risk-myths',
        titleZh: '第一章 破除高风险迷思：认识期权的真正价值',
        titleEn: 'Ch1: Breaking Risk Myths',
        accessLevel: 'guest',
        readTimeMin: 4,
        updatedAt: '2026-02-26',
        sections: [
          { id: 'house-deposit', titleZh: '房子"定金"就是期权金', titleEn: 'House Deposit as Premium' },
          { id: 'three-values', titleZh: '期权带来的三大核心价值', titleEn: 'Three Core Values' },
        ],
      },
      {
        id: 'ch02',
        slug: 'key-terms',
        fileId: 'ch02-key-terms',
        titleZh: '第二章 22个关键词与定价逻辑完成期权入门',
        titleEn: 'Ch2: 22 Key Terms & Pricing Logic',
        accessLevel: 'guest',
        readTimeMin: 6,
        updatedAt: '2026-02-26',
        sections: [
          { id: 'call-put', titleZh: '核心方向：Call 与 Put', titleEn: 'Call vs Put' },
          { id: 'pricing', titleZh: '期权价格的解剖学', titleEn: 'Options Pricing Anatomy' },
          { id: 'iv', titleZh: '波动率（IV）', titleEn: 'Implied Volatility' },
          { id: 'greeks', titleZh: '希腊字母', titleEn: 'The Greeks' },
        ],
      },
    ],
  },
  {
    id: 'core-strategies',
    titleZh: '核心策略',
    titleEn: 'Core Strategies',
    icon: 'Target',
    chapters: [
      {
        id: 'ch03',
        slug: 'beginner-strategies',
        fileId: 'ch03-beginner-strategies',
        titleZh: '第三章 五大新手友善策略（逻辑与实战）',
        titleEn: 'Ch3: 5 Beginner-Friendly Strategies',
        accessLevel: 'free',
        readTimeMin: 8,
        updatedAt: '2026-02-26',
        sections: [
          { id: 'buy-call', titleZh: '单边买入看涨（Buy Call）', titleEn: 'Buy Call' },
          { id: 'sell-put', titleZh: '卖出看跌期权（Sell Put）', titleEn: 'Sell Put' },
          { id: 'covered-call', titleZh: '卖出备兑看涨（Covered Call）', titleEn: 'Covered Call' },
          { id: 'protective-put', titleZh: '保护性看跌（Protective Put）', titleEn: 'Protective Put' },
          { id: 'short-strangle', titleZh: '卖空宽跨式（Short Strangle）', titleEn: 'Short Strangle' },
        ],
      },
    ],
  },
  {
    id: 'advanced-topics',
    titleZh: '高级主题',
    titleEn: 'Advanced Topics',
    icon: 'Zap',
    chapters: [
      {
        id: 'ch05',
        slug: 'advanced-strategies',
        fileId: 'ch05-advanced-strategies',
        titleZh: '第五章 高手的回报率放大器：四大进阶玩法',
        titleEn: 'Ch5: 4 Advanced Strategies',
        accessLevel: 'free',
        readTimeMin: 6,
        updatedAt: '2026-02-26',
        sections: [
          { id: '0dte', titleZh: '末日期权（0DTE）卖方', titleEn: '0DTE Selling' },
          { id: 'vertical-spread', titleZh: '垂直价差（Vertical Spread）', titleEn: 'Vertical Spreads' },
          { id: 'leaps', titleZh: 'LEAPS Call（长期杠杆替身）', titleEn: 'LEAPS Calls' },
          { id: 'wheel', titleZh: '车轮策略（Wheel Strategy）', titleEn: 'Wheel Strategy' },
        ],
      },
      {
        id: 'ch08',
        slug: 'pitfalls',
        fileId: 'ch08-pitfalls',
        titleZh: '第八章 五个帮你节省学费的意外踩坑故事',
        titleEn: 'Ch8: 5 Common Pitfalls',
        accessLevel: 'free',
        readTimeMin: 3,
        updatedAt: '2026-02-26',
        sections: [],
      },
      {
        id: 'ch09',
        slug: 'advanced-psychology',
        fileId: 'ch09-advanced-psychology',
        titleZh: '第九章 期权进阶高手的盈利策略与心法',
        titleEn: 'Ch9: Advanced Mindset & Strategies',
        accessLevel: 'free',
        readTimeMin: 3,
        updatedAt: '2026-02-26',
        sections: [],
      },
    ],
  },
  {
    id: 'platform-guides',
    titleZh: '平台指南',
    titleEn: 'Platform Guides',
    icon: 'Monitor',
    chapters: [
      {
        id: 'ch04',
        slug: 'simulation-trade',
        fileId: 'ch04-simulation-trade',
        titleZh: '第四章 30分钟完成第一笔期权模拟全流程',
        titleEn: 'Ch4: First Simulation Trade',
        accessLevel: 'guest',
        readTimeMin: 4,
        updatedAt: '2026-02-26',
        sections: [
          { id: 'liquidity', titleZh: '被忽视的隐形杀手：流动性', titleEn: 'Liquidity' },
          { id: 'three-outcomes', titleZh: '建仓后的三种命运结局', titleEn: 'Three Outcomes' },
        ],
      },
      {
        id: 'ch06',
        slug: 'pain-points',
        fileId: 'ch06-pain-points',
        titleZh: '第六章 期权交易五大痛点及 AlphaGBM 智能解决方案',
        titleEn: 'Ch6: 5 Pain Points & AlphaGBM Solutions',
        accessLevel: 'free',
        readTimeMin: 7,
        updatedAt: '2026-02-26',
        sections: [
          { id: 'pain-1', titleZh: 'Sell Put 行权价定在哪里', titleEn: 'Strike Price Selection' },
          { id: 'pain-2', titleZh: '期权贵还是便宜', titleEn: 'IV Assessment' },
          { id: 'pain-3', titleZh: '大盘见底了吗', titleEn: 'Market Bottom' },
          { id: 'pain-4', titleZh: '期权值多少钱', titleEn: 'Option Calculator' },
          { id: 'pain-5', titleZh: '寻找最高年化Sell Put', titleEn: 'Best Sell Put' },
        ],
      },
      {
        id: 'ch07',
        slug: 'ai-assistant',
        fileId: 'ch07-ai-assistant',
        titleZh: '第七章 让投资事半功倍——AI智能助手的五大经典用法',
        titleEn: 'Ch7: 5 AI Assistant Use Cases',
        accessLevel: 'free',
        readTimeMin: 3,
        updatedAt: '2026-02-26',
        sections: [],
      },
      {
        id: 'ch10',
        slug: 'seven-day-plan',
        fileId: 'ch10-seven-day-plan',
        titleZh: '第十章 零基础学7天可以达到什么程度？',
        titleEn: 'Ch10: 7-Day Learning Outcome',
        accessLevel: 'guest',
        readTimeMin: 3,
        updatedAt: '2026-02-26',
        sections: [],
      },
      {
        id: 'appendix',
        slug: 'appendix',
        fileId: 'appendix',
        titleZh: '附：新手7天破局实操路径指南',
        titleEn: 'Appendix: 7-Day Action Plan',
        accessLevel: 'guest',
        readTimeMin: 3,
        updatedAt: '2026-02-26',
        sections: [],
      },
    ],
  },
  {
    id: 'conclusion',
    titleZh: '写于最后',
    titleEn: 'Conclusion',
    icon: 'PenLine',
    chapters: [
      {
        id: 'conclusion',
        slug: 'conclusion',
        fileId: 'conclusion',
        titleZh: '写于最后：实践出真知，财富始于行动',
        titleEn: 'Practice Makes Perfect',
        accessLevel: 'guest',
        readTimeMin: 1,
        updatedAt: '2026-02-26',
        sections: [],
      },
    ],
  },
];

// Flatten all chapters for easy lookup
export const allChapters: KBChapter[] = kbCategories.flatMap((cat) => cat.chapters);

// Find chapter by slug
export function findChapterBySlug(slug: string): KBChapter | undefined {
  return allChapters.find((ch) => ch.slug === slug);
}

// Find category by chapter id
export function findCategoryByChapterId(chapterId: string): KBCategory | undefined {
  return kbCategories.find((cat) => cat.chapters.some((ch) => ch.id === chapterId));
}

// Get previous and next chapters
export function getAdjacentChapters(chapterId: string): { prev?: KBChapter; next?: KBChapter } {
  const idx = allChapters.findIndex((ch) => ch.id === chapterId);
  return {
    prev: idx > 0 ? allChapters[idx - 1] : undefined,
    next: idx < allChapters.length - 1 ? allChapters[idx + 1] : undefined,
  };
}

// Content loader map (static imports for Vite bundling)
const contentModules = import.meta.glob<string>('/src/content/knowledge-base/zh/*.md', {
  query: '?raw',
  import: 'default',
});

export async function loadChapterContent(fileId: string): Promise<string> {
  const path = `/src/content/knowledge-base/zh/${fileId}.md`;
  const loader = contentModules[path];
  if (!loader) {
    throw new Error(`Chapter content not found: ${fileId}`);
  }
  return loader();
}
