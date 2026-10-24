import React from 'react';
import { AlertTriangle, Info, AlertCircle } from 'lucide-react';

interface AlertBannerProps {
  flags: string[];
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ flags }) => {
  if (!flags || flags.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.25rem' }}>
      {flags.map((flag, idx) => {
        const isWarning = flag.includes('WARNING') || flag.includes('LOW_COVERAGE');
        const isError = flag.includes('UNAVAILABLE') || flag.includes('FAILED');

        const borderColor = isError
          ? 'rgba(244, 63, 94, 0.35)'
          : isWarning
          ? 'rgba(245, 158, 11, 0.35)'
          : 'rgba(56, 189, 248, 0.35)';

        const bgColor = isError
          ? 'rgba(244, 63, 94, 0.08)'
          : isWarning
          ? 'rgba(245, 158, 11, 0.08)'
          : 'rgba(56, 189, 248, 0.08)';

        const textColor = isError
          ? '#FB7185'
          : isWarning
          ? '#FBBF24'
          : '#38BDF8';

        const Icon = isError ? AlertCircle : isWarning ? AlertTriangle : Info;

        return (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              padding: '0.65rem 1rem',
              borderRadius: 'var(--radius-sm)',
              background: bgColor,
              border: `1px solid ${borderColor}`,
              color: textColor,
              fontSize: '0.78rem',
            }}
          >
            <Icon size={16} />
            <span style={{ fontWeight: 500 }}>{flag}</span>
          </div>
        );
      })}
    </div>
  );
};
