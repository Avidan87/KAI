interface MacroBarProps {
  label: string;
  current: number;
  target: number;
  unit: string;
  status: 'good' | 'warning' | 'critical';
}

export function MacroBar({ label, current, target, unit, status }: MacroBarProps) {
  const percentage = Math.round((current / target) * 100);
  const dots = 10;
  const filledDots = Math.min(Math.round((percentage / 100) * dots), dots);

  const getStatusIcon = () => {
    if (status === 'good') return '✓';
    if (status === 'warning') return '⚠️';
    return '❌';
  };

  const getStatusColor = () => {
    if (status === 'good') return 'text-primary';
    if (status === 'warning') return 'text-accent';
    return 'text-destructive';
  };

  const getDotColor = () => {
    if (status === 'good') return 'text-primary';
    if (status === 'warning') return 'text-accent';
    return 'text-destructive';
  };

  return (
    <div className="flex items-center justify-between py-2">
      {/* Label */}
      <div className="w-12">
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
      </div>

      {/* Values */}
      <div className="flex-1 px-3">
        <span className="text-sm font-medium">{current}{unit}/{target}{unit}</span>
      </div>

      {/* Visual Dots */}
      <div className={`flex gap-0.5 ${getDotColor()}`}>
        {Array.from({ length: dots }, (_, i) => (
          <span key={i} className="text-sm">
            {i < filledDots ? '●' : '○'}
          </span>
        ))}
      </div>

      {/* Status Icon */}
      <div className={`w-6 flex justify-center ${getStatusColor()}`}>
        <span className="text-sm">{getStatusIcon()}</span>
      </div>
    </div>
  );
}