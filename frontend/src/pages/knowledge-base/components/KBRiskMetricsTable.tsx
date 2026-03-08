import { useTranslation } from 'react-i18next';

interface Metric {
  label: string;
  labelEn: string;
  value: string;
  note: string;
  noteEn: string;
  color?: 'green' | 'red' | 'orange' | 'default';
}

interface Props {
  title?: string;
  metrics?: Metric[];
}

const defaultMetrics: Metric[] = [
  {
    label: '最大利润',
    labelEn: 'Max Profit',
    value: '$350 (每张合约)',
    note: '收取的全部权利金',
    noteEn: 'Full premium received',
    color: 'green',
  },
  {
    label: '最大损失',
    labelEn: 'Max Loss',
    value: '$17,150',
    note: '行权价($175) × 100 - 权利金($350)',
    noteEn: 'Strike($175) × 100 - Premium($350)',
    color: 'red',
  },
  {
    label: '盈亏平衡',
    labelEn: 'Breakeven',
    value: '$171.50',
    note: '行权价 - 每股权利金 ($175 - $3.50)',
    noteEn: 'Strike - Premium per share ($175 - $3.50)',
    color: 'orange',
  },
  {
    label: '胜率',
    labelEn: 'Win Probability',
    value: '60-75%',
    note: '取决于Delta值，通常选30Delta以下',
    noteEn: 'Depends on Delta, typically < 30 Delta',
    color: 'default',
  },
  {
    label: '年化收益',
    labelEn: 'Annualized Return',
    value: '~24%',
    note: '$350 / $17,500 × (365/30)',
    noteEn: '$350 / $17,500 × (365/30)',
    color: 'green',
  },
];

const colorValueMap = {
  green: 'text-[#10B981]',
  red: 'text-[#EF4444]',
  orange: 'text-[#F59E0B]',
  default: 'text-[#FAFAFA]',
};

export default function KBRiskMetricsTable({ title, metrics }: Props) {
  const { i18n } = useTranslation();
  const isZh = i18n.language === 'zh';
  const data = metrics ?? defaultMetrics;

  return (
    <div className="my-8 rounded-xl border border-white/10 overflow-hidden">
      {title && (
        <div className="px-5 py-3 bg-[#18181B] border-b border-white/10">
          <h4 className="text-sm font-semibold text-[#FAFAFA]">{title}</h4>
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#27272A]/50">
            <th className="text-left p-3.5 text-[#FAFAFA] font-semibold">{isZh ? '指标' : 'Metric'}</th>
            <th className="text-left p-3.5 text-[#FAFAFA] font-semibold">{isZh ? '数值' : 'Value'}</th>
            <th className="text-left p-3.5 text-[#FAFAFA] font-semibold hidden sm:table-cell">{isZh ? '说明' : 'Note'}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((m) => (
            <tr key={m.label} className="border-b border-white/5 hover:bg-[#27272A]/20 transition-colors">
              <td className="p-3.5 text-[#A1A1AA] font-medium">{isZh ? m.label : m.labelEn}</td>
              <td className={`p-3.5 font-mono font-semibold ${colorValueMap[m.color ?? 'default']}`}>
                {m.value}
              </td>
              <td className="p-3.5 text-[#71717A] hidden sm:table-cell">{isZh ? m.note : m.noteEn}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
