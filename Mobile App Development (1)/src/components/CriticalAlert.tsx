import { AlertTriangle } from "lucide-react";
import { Card } from "./ui/card";
import { motion } from "motion/react";

interface CriticalAlertProps {
  nutrient: string;
  days: number;
  onTap: () => void;
}

export function CriticalAlert({ nutrient, days, onTap }: CriticalAlertProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card 
        className="p-3 bg-accent/10 border-accent cursor-pointer hover:bg-accent/15 transition-colors"
        onClick={onTap}
      >
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-accent flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium">
              ⚠️ Low {nutrient} ({days} days) — Tap
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              to see fix
            </p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}