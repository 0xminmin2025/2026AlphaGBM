interface Step {
  title: string;
  description: string;
  tip?: string;
}

interface Props {
  title?: string;
  steps: Step[];
}

export default function KBStepGuide({ title, steps }: Props) {
  return (
    <div className="my-8">
      {title && (
        <h4 className="text-lg font-semibold text-[#FAFAFA] mb-5">{title}</h4>
      )}
      <div className="space-y-4">
        {steps.map((step, i) => (
          <div key={i} className="flex gap-4 group">
            {/* Number circle */}
            <div className="flex-shrink-0">
              <div className="w-9 h-9 rounded-full bg-[#0D9B97] flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-[#0D9B97]/20">
                {i + 1}
              </div>
              {i < steps.length - 1 && (
                <div className="w-px h-full bg-[#0D9B97]/20 mx-auto mt-1" />
              )}
            </div>

            {/* Content */}
            <div className="pb-4 flex-1 min-w-0">
              <h5 className="text-base font-semibold text-[#FAFAFA] mb-1.5 group-hover:text-[#0D9B97] transition-colors">
                {step.title}
              </h5>
              <p className="text-sm text-[#A1A1AA] leading-relaxed">{step.description}</p>
              {step.tip && (
                <div className="mt-2.5 text-xs text-[#71717A] bg-[#0D9B97]/5 border border-[#0D9B97]/10 rounded-lg px-3 py-2">
                  💡 {step.tip}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Pre-built: Sell Put execution steps
export function SellPutStepGuide() {
  return (
    <KBStepGuide
      title="如何执行 Sell Put 交易（7步流程）"
      steps={[
        { title: '确定目标股票', description: '选择你看好且愿意持有的优质股票', tip: '优先选择你已经做过基本面分析的个股' },
        { title: '使用 AlphaGBM 分析', description: '进入期权分析页面，查看 Sell Put 评分最高的机会', tip: '关注评分 70 分以上的合约' },
        { title: '审查评分明细', description: '查看7维评分（权利金、趋势、支撑、ATR、流动性、时间价值、IV排名）' },
        { title: '确认保证金充足', description: '确保账户有 行权价 × 100 股 的现金作为担保' },
        { title: '下单交易', description: '在券商平台使用限价单卖出 Put，避免市价单造成滑点' },
        { title: '监控持仓', description: '关注股价走势和时间价值衰减，设定心理止损线' },
        { title: '到期处理', description: '若股价高于行权价则权利金落袋；若被行权则以折扣价接盘股票', tip: '被行权后可立即开始 Covered Call 进入车轮策略' },
      ]}
    />
  );
}
