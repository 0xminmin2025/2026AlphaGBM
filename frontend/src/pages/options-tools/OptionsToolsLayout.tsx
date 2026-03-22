/**
 * 期权工具集布局 - Tab 导航框架
 * 遵循 alpha_quantum 设计规范：深色主题、无边框、层级背景
 */

import { useSearchParams } from 'react-router-dom';
import {
  Activity, Calculator, TrendingUp, Search,
  Lock
} from 'lucide-react';
import { useUserData } from '@/components/auth/UserDataProvider';

import VolatilityPage from './VolatilityPage';
import StrategyBuilderPage from './StrategyBuilderPage';
import PnLSimulatorPage from './PnLSimulatorPage';
import OptionScannerPage from './OptionScannerPage';

const TOOLS_TABS = [
  {
    id: 'volatility',
    label: '波动率分析',
    icon: Activity,
    description: 'IV 微笑曲线 · 3D 波动率曲面',
    tier: 'free',   // free 可看基础
  },
  {
    id: 'calculator',
    label: '策略构建器',
    icon: Calculator,
    description: 'Greeks 计算 · 多腿策略组合',
    tier: 'free',
  },
  {
    id: 'simulator',
    label: '盈亏模拟',
    icon: TrendingUp,
    description: 'P/L 场景分析 · What-if 模拟',
    tier: 'plus',
  },
  {
    id: 'scanner',
    label: '机会扫描',
    icon: Search,
    description: '期权机会筛选 · GBM 评分',
    tier: 'plus',
  },
] as const;

type TabId = typeof TOOLS_TABS[number]['id'];

// 用户层级权限判断
function canAccessTab(userTier: string, tabTier: string): boolean {
  const tierLevel: Record<string, number> = { free: 0, plus: 1, pro: 2 };
  return (tierLevel[userTier] ?? 0) >= (tierLevel[tabTier] ?? 0);
}

export default function OptionsToolsLayout() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = (searchParams.get('tab') as TabId) || 'volatility';
  const { credits } = useUserData();

  const userTier = credits?.subscription?.plan_tier || 'free';

  const setActiveTab = (tab: TabId) => {
    setSearchParams({ tab });
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'volatility':
        return <VolatilityPage userTier={userTier} />;
      case 'calculator':
        return <StrategyBuilderPage userTier={userTier} />;
      case 'simulator':
        return <PnLSimulatorPage userTier={userTier} />;
      case 'scanner':
        return <OptionScannerPage userTier={userTier} />;
      default:
        return <VolatilityPage userTier={userTier} />;
    }
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          期权<span className="text-[#66d8d3]">工具集</span>
        </h1>
        <p className="text-sm text-[#bcc9c8]">
          专业级期权分析工具 · 波动率 · 策略 · 模拟 · 扫描
        </p>
      </div>

      {/* Tab 导航 */}
      <div className="flex flex-wrap justify-center gap-2 sm:gap-3">
        {TOOLS_TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          const hasAccess = canAccessTab(userTier, tab.tier);

          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                group relative flex items-center gap-2 px-4 py-2.5 rounded-lg
                text-sm font-medium transition-all duration-200
                ${isActive
                  ? 'bg-[#1a2f2e] text-[#66d8d3] shadow-[0_0_20px_rgba(102,216,211,0.1)]'
                  : 'bg-[#1a1a1c] text-[#bcc9c8] hover:bg-[#222224] hover:text-[#e0e0e0]'
                }
              `}
            >
              <Icon size={16} className={isActive ? 'text-[#66d8d3]' : 'text-[#6b7280]'} />
              <span>{tab.label}</span>
              {!hasAccess && (
                <Lock size={12} className="text-[#6b7280] ml-1" />
              )}
              {/* 底部指示条 */}
              {isActive && (
                <div className="absolute bottom-0 left-2 right-2 h-[2px] bg-[#66d8d3] rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* 内容区域 */}
      <div className="min-h-[600px]">
        {renderContent()}
      </div>
    </div>
  );
}
