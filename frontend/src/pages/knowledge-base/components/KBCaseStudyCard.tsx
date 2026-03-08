import { useTranslation } from 'react-i18next';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface DataRow {
  label: string;
  value: string;
  color?: 'default' | 'green' | 'red' | 'teal';
}

interface Scenario {
  title: string;
  description: string;
  outcome: 'profit' | 'loss';
}

interface Props {
  title: string;
  subtitle?: string;
  data: DataRow[];
  scenarios?: Scenario[];
}

const colorMap = {
  default: 'text-[#FAFAFA]',
  green: 'text-[#10B981]',
  red: 'text-[#EF4444]',
  teal: 'text-[#0D9B97]',
};

export default function KBCaseStudyCard({ title, subtitle, data, scenarios }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  return (
    <div className="my-8 rounded-xl border border-white/10 bg-[#18181B] overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/10 bg-[#27272A]/30">
        <h4 className="text-base font-semibold text-[#FAFAFA]">{title}</h4>
        {subtitle && <p className="text-sm text-[#71717A] mt-1">{subtitle}</p>}
      </div>

      {/* Data Grid */}
      <div className="p-5">
        <div className="grid grid-cols-2 gap-4">
          {data.map((row) => (
            <div key={row.label} className="flex flex-col gap-1">
              <span className="text-xs text-[#71717A] uppercase tracking-wider">{row.label}</span>
              <span className={`text-sm font-mono font-medium ${colorMap[row.color ?? 'default']}`}>
                {row.value}
              </span>
            </div>
          ))}
        </div>

        {/* Scenarios */}
        {scenarios && scenarios.length > 0 && (
          <div className="mt-5 pt-5 border-t border-white/10 space-y-3">
            <p className="text-xs text-[#71717A] uppercase tracking-wider mb-3">
              {isZh ? '场景分析' : 'Scenarios'}
            </p>
            {scenarios.map((s) => (
              <div
                key={s.title}
                className={`flex items-start gap-3 rounded-lg p-3 ${
                  s.outcome === 'profit' ? 'bg-[#10B981]/5 border border-[#10B981]/15' : 'bg-[#EF4444]/5 border border-[#EF4444]/15'
                }`}
              >
                <div className={`flex-shrink-0 mt-0.5 w-6 h-6 rounded-full flex items-center justify-center ${
                  s.outcome === 'profit' ? 'bg-[#10B981]/20' : 'bg-[#EF4444]/20'
                }`}>
                  {s.outcome === 'profit'
                    ? <TrendingUp size={12} className="text-[#10B981]" />
                    : <TrendingDown size={12} className="text-[#EF4444]" />
                  }
                </div>
                <div>
                  <p className={`text-sm font-medium ${s.outcome === 'profit' ? 'text-[#10B981]' : 'text-[#EF4444]'}`}>
                    {s.title}
                  </p>
                  <p className="text-sm text-[#A1A1AA] mt-0.5">{s.description}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Pre-built case study: Buffett's Coca-Cola Sell Put (used in preface)
export function BuffettCaseStudy() {
  return (
    <KBCaseStudyCard
      title="实战案例：巴菲特的可口可乐 Sell Put"
      subtitle="1993年经典期权操作"
      data={[
        { label: '标的股票', value: 'KO (可口可乐)', color: 'teal' },
        { label: '当时股价', value: '$40.00' },
        { label: '行权价', value: '$35.00' },
        { label: '期权费', value: '$1.50 / 股', color: 'green' },
        { label: '合约数量', value: '50,000 张 (500万股)' },
        { label: '总收入', value: '$7,500,000', color: 'green' },
      ]}
      scenarios={[
        {
          title: '情景A：股价跌破 $35',
          description: '以 $33.5 的实际成本买入（远低于市价 $40），获得打折建仓机会',
          outcome: 'profit',
        },
        {
          title: '情景B：股价维持在 $35 以上',
          description: '期权过期作废，白赚 $750万 权利金 — 最终结果',
          outcome: 'profit',
        },
      ]}
    />
  );
}

// Pre-built: Sell Put strategy example
export function SellPutExample() {
  return (
    <KBCaseStudyCard
      title="Sell Put 实战示例"
      subtitle="以 AAPL 为例的现金担保卖出看跌"
      data={[
        { label: '标的股票', value: 'AAPL', color: 'teal' },
        { label: '当前股价', value: '$180.00' },
        { label: '行权价', value: '$175.00' },
        { label: '到期日', value: '2025-02-21 (30天)' },
        { label: '期权费', value: '$3.50 / 股', color: 'green' },
        { label: '保证金', value: '$17,500 (175 × 100)' },
      ]}
      scenarios={[
        {
          title: '股价高于 $175 到期',
          description: '期权作废，保留全部 $350 权利金。年化收益率约 24%',
          outcome: 'profit',
        },
        {
          title: '股价跌破 $175',
          description: '以 $171.50 实际成本接盘 100 股 AAPL（$175 - $3.50 权利金）',
          outcome: 'loss',
        },
      ]}
    />
  );
}
