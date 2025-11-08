interface ProgressBarProps {
  percentage: number;
  color?: 'primary' | 'accent' | 'destructive' | 'secondary';
  showPercentage?: boolean;
  height?: 'sm' | 'md' | 'lg';
}

export function ProgressBar({ 
  percentage, 
  color = 'primary', 
  showPercentage = false,
  height = 'md'
}: ProgressBarProps) {
  const heightClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  };

  const colorClasses = {
    primary: 'bg-primary',
    accent: 'bg-accent',
    destructive: 'bg-destructive',
    secondary: 'bg-secondary'
  };

  return (
    <div className="w-full">
      <div className={`w-full bg-muted rounded-full overflow-hidden ${heightClasses[height]}`}>
        <div 
          className={`${heightClasses[height]} ${colorClasses[color]} transition-all duration-500 ease-in-out rounded-full`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      {showPercentage && (
        <div className="text-sm text-muted-foreground mt-1">
          {Math.round(percentage)}%
        </div>
      )}
    </div>
  );
}