import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import { Button } from "./ui/button";
import { ProgressBar } from "./ProgressBar";

interface HexagonDetailSheetProps {
  isOpen: boolean;
  onClose: () => void;
  label: string;
  current: number;
  target: number;
  unit: string;
  percentage: number;
  status: 'good' | 'warning' | 'critical';
  color: string;
  sources?: Array<{ meal: string; amount: number; time: string }>;
  education?: string;
  tip?: string;
}

export function HexagonDetailSheet({
  isOpen,
  onClose,
  label,
  current,
  target,
  unit,
  percentage,
  status,
  color,
  sources = [],
  education,
  tip
}: HexagonDetailSheetProps) {
  
  // Calculate fill height for larger hexagon (140px height)
  const fillHeight = Math.min(percentage, 100) * 1.0; // 100px max height for larger hex

  const defaultSources = [
    { meal: "🌅 Breakfast", amount: Math.floor(current * 0.3), time: "7:30 AM" },
    { meal: "🍽️ Lunch", amount: Math.floor(current * 0.5), time: "1:15 PM" },
    { meal: "🌙 Dinner", amount: current - Math.floor(current * 0.3) - Math.floor(current * 0.5), time: "7:00 PM" }
  ].filter(source => source.amount > 0);

  const displaySources = sources.length > 0 ? sources : defaultSources;

  const statusMessages = {
    good: {
      title: "Excellent! 💪",
      message: `You're doing great with your ${label.toLowerCase()} intake. Keep up the good work!`,
      cta: "Keep going!"
    },
    warning: {
      title: "⚠️ Watch This",
      message: `You're close to your ${label.toLowerCase()} target. Consider lighter options for your next meal.`,
      cta: "Got it"
    },
    critical: {
      title: "❌ Needs Attention",
      message: `Your ${label.toLowerCase()} is quite low. Try adding ${label.toLowerCase()}-rich foods to your next meal.`,
      cta: "Show me foods"
    }
  };

  const currentMessage = statusMessages[status];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Sheet */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 z-50 bg-background rounded-t-3xl max-h-[85vh] overflow-hidden"
          >
            {/* Handle */}
            <div className="flex justify-center py-4">
              <div className="w-12 h-1 bg-muted-foreground/30 rounded-full" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-6 pb-4">
              <h2 className="text-xl font-semibold text-[rgb(255,253,253)]">{label.toUpperCase()} DETAIL</h2>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="w-6 h-6" />
              </Button>
            </div>

            {/* Content */}
            <div className="px-6 pb-8 overflow-y-auto">
              {/* Large Hexagon */}
              <div className="flex justify-center mb-6">
                <div className="relative">
                  <svg width="140" height="121" viewBox="0 0 140 121" className="drop-shadow-lg">
                    <defs>
                      <clipPath id={`hexClipLarge-${label}`}>
                        <path d="M70 3 L134 33 L134 88 L70 118 L6 88 L6 33 Z"/>
                      </clipPath>
                    </defs>
                    
                    {/* Background hexagon */}
                    <path 
                      d="M70 3 L134 33 L134 88 L70 118 L6 88 L6 33 Z"
                      fill="rgb(var(--color-card))"
                      stroke="rgb(var(--color-border))"
                      strokeWidth="3"
                    />
                    
                    {/* Progress fill */}
                    <motion.rect 
                      x="6" 
                      y={118 - fillHeight}
                      width="128" 
                      height={fillHeight}
                      fill={color}
                      clipPath={`url(#hexClipLarge-${label})`}
                      initial={{ height: 0, y: 118 }}
                      animate={{ height: fillHeight, y: 118 - fillHeight }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                    />
                  </svg>
                  
                  {/* Center content */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-4xl font-bold text-foreground mb-1">{percentage}%</span>
                  </div>
                </div>
              </div>

              {/* Summary */}
              <div className="text-center mb-6">
                <p className="text-2xl font-bold mb-3 text-[rgb(255,248,248)]">
                  {current}{unit} of {target}{unit}
                </p>
                <ProgressBar percentage={percentage} color="primary" />
              </div>

              {/* Divider */}
              <hr className="border-border mb-6" />

              {/* Today's Breakdown */}
              <div className="mb-6">
                <h3 className="font-semibold mb-4 text-[rgb(255,252,252)]">TODAY'S BREAKDOWN:</h3>
                <div className="space-y-4">
                  {displaySources.map((source, index) => {
                    const sourcePercentage = Math.round((source.amount / target) * 100);
                    return (
                      <div key={index} className="space-y-2">
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-medium text-[rgb(255,248,248)]">{source.meal}</p>
                            <p className="text-sm text-muted-foreground">{source.time}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium text-[rgb(255,252,252)]">{source.amount}{unit}</p>
                            <p className="text-xs text-muted-foreground">{sourcePercentage}%</p>
                          </div>
                        </div>
                        {/* Mini progress bar for each meal */}
                        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            className="h-full rounded-full"
                            style={{ backgroundColor: color }}
                            initial={{ width: 0 }}
                            animate={{ width: `${sourcePercentage}%` }}
                            transition={{ duration: 0.6, delay: index * 0.1 }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Divider */}
              <hr className="border-border mb-6" />

              {/* Status Message */}
              <div className="mb-6">
                <h3 className="font-semibold mb-3 text-[rgb(255,251,251)]">{currentMessage.title}</h3>
                <p className="text-muted-foreground mb-4">
                  {currentMessage.message}
                </p>
                
                {/* Education */}
                {education && (
                  <div className="bg-muted/50 rounded-lg p-4 mb-4">
                    <h4 className="font-medium mb-2">💡 WHY IT MATTERS</h4>
                    <p className="text-sm text-muted-foreground">{education}</p>
                  </div>
                )}

                {/* Tip */}
                {tip && (
                  <div className="bg-accent/10 rounded-lg p-4 mb-4">
                    <h4 className="font-medium mb-2">🌿 TIP</h4>
                    <p className="text-sm">{tip}</p>
                  </div>
                )}
              </div>

              {/* Action Button */}
              <Button 
                onClick={onClose}
                className="w-full"
                style={{ backgroundColor: color }}
              >
                {currentMessage.cta}
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}