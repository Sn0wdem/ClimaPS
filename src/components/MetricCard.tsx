import React from 'react';
import { HelpCircle } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  subtext?: string;
  tone?: 'neutral' | 'positive' | 'warning' | 'negative';
  help?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  tone = 'neutral',
  help,
}) => {
  const subColor =
    tone === 'positive'
      ? 'var(--nominal)'
      : tone === 'warning'
      ? 'var(--warning)'
      : tone === 'negative'
      ? 'var(--danger)'
      : 'var(--text-muted)';

  return (
    <div className="surface-panel px-4 py-3.5 flex flex-col justify-between min-h-[96px]">
      <div className="flex items-center justify-between gap-2">
        <span
          className="text-[0.78rem] font-medium leading-tight truncate"
          style={{ color: 'var(--text-muted)' }}
          title={label}
        >
          {label}
        </span>
        {help && (
          <span
            title={help}
            className="cursor-help shrink-0 opacity-70 hover:opacity-100 transition-opacity"
            style={{ color: 'var(--text-muted)' }}
          >
            <HelpCircle size={14} />
          </span>
        )}
      </div>

      <div className="mt-2 flex items-baseline gap-1.5">
        <span
          className="font-mono-tabular text-[1.5rem] font-semibold tracking-tight leading-none"
          style={{ color: 'var(--text-primary)' }}
        >
          {value}
        </span>
        {unit && (
          <span
            className="font-mono-tabular text-[0.78rem] font-medium"
            style={{ color: 'var(--text-muted)' }}
          >
            {unit}
          </span>
        )}
      </div>

      {subtext && (
        <div
          className="mt-2 text-[0.76rem] font-medium truncate"
          style={{ color: subColor }}
          title={subtext}
        >
          {subtext}
        </div>
      )}
    </div>
  );
};
