import { useTranslation } from 'react-i18next';
import { ArrowRight, DollarSign, Clock, CheckCircle, AlertCircle } from 'lucide-react';

export default function KBStrategyFlowDiagram() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  const steps = isZh
    ? [
        { icon: DollarSign, label: '收取权利金', desc: '卖出 Put 期权', color: '#0D9B97' },
        { icon: Clock, label: '等待到期', desc: '时间价值衰减', color: '#F59E0B' },
        { icon: CheckCircle, label: '权利金到手', desc: '股价 > 行权价', color: '#10B981' },
        { icon: AlertCircle, label: '折扣接盘', desc: '股价 < 行权价', color: '#EF4444' },
      ]
    : [
        { icon: DollarSign, label: 'Collect Premium', desc: 'Sell Put Option', color: '#0D9B97' },
        { icon: Clock, label: 'Wait for Expiry', desc: 'Time decay works for you', color: '#F59E0B' },
        { icon: CheckCircle, label: 'Keep Premium', desc: 'Stock > Strike', color: '#10B981' },
        { icon: AlertCircle, label: 'Buy at Discount', desc: 'Stock < Strike', color: '#EF4444' },
      ];

  return (
    <div className="my-8 rounded-xl border border-white/10 bg-[#18181B] p-5 overflow-x-auto">
      <h4 className="text-sm font-semibold text-[#FAFAFA] mb-5">
        {isZh ? 'Sell Put 策略流程' : 'Sell Put Strategy Flow'}
      </h4>

      {/* Desktop: horizontal flow */}
      <div className="hidden sm:flex items-center justify-between gap-2 min-w-[500px]">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="flex flex-col items-center text-center w-28">
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center mb-2"
                style={{ backgroundColor: `${step.color}15`, border: `1px solid ${step.color}30` }}
              >
                <step.icon size={20} style={{ color: step.color }} />
              </div>
              <p className="text-sm font-medium text-[#FAFAFA] leading-tight">{step.label}</p>
              <p className="text-xs text-[#71717A] mt-0.5">{step.desc}</p>
            </div>
            {i < steps.length - 1 && (
              <ArrowRight size={16} className="text-[#71717A] flex-shrink-0" />
            )}
          </div>
        ))}
      </div>

      {/* Mobile: vertical flow */}
      <div className="sm:hidden space-y-3">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: `${step.color}15`, border: `1px solid ${step.color}30` }}
            >
              <step.icon size={18} style={{ color: step.color }} />
            </div>
            <div>
              <p className="text-sm font-medium text-[#FAFAFA]">{step.label}</p>
              <p className="text-xs text-[#71717A]">{step.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Wheel Strategy cycle diagram
export function WheelStrategyCycle() {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';

  const phases = isZh
    ? [
        { step: '1', label: 'Sell Put', desc: '收权利金等接盘', color: '#0D9B97' },
        { step: '2', label: '被行权', desc: '折扣价买入股票', color: '#F59E0B' },
        { step: '3', label: 'Sell Call', desc: '持股卖出看涨收租', color: '#10B981' },
        { step: '4', label: '股票卖出', desc: '资金回笼重新循环', color: '#0D9B97' },
      ]
    : [
        { step: '1', label: 'Sell Put', desc: 'Collect premium', color: '#0D9B97' },
        { step: '2', label: 'Assigned', desc: 'Buy stock at discount', color: '#F59E0B' },
        { step: '3', label: 'Sell Call', desc: 'Collect premium on stock', color: '#10B981' },
        { step: '4', label: 'Called Away', desc: 'Cash returns, restart', color: '#0D9B97' },
      ];

  return (
    <div className="my-8 rounded-xl border border-white/10 bg-[#18181B] p-5">
      <h4 className="text-sm font-semibold text-[#FAFAFA] mb-4">
        {isZh ? '车轮策略 (Wheel) 循环流程' : 'Wheel Strategy Cycle'}
      </h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {phases.map((p) => (
          <div key={p.step} className="relative rounded-lg border border-white/10 p-3 text-center bg-[#09090B]">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center mx-auto mb-2 text-sm font-bold text-white"
              style={{ backgroundColor: p.color }}
            >
              {p.step}
            </div>
            <p className="text-sm font-medium text-[#FAFAFA]">{p.label}</p>
            <p className="text-xs text-[#71717A] mt-0.5">{p.desc}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-center">
        <span className="text-xs text-[#0D9B97] font-medium">
          {isZh ? '♻️ 循环往复，持续产生现金流' : '♻️ Repeat cycle for continuous cash flow'}
        </span>
      </div>
    </div>
  );
}
