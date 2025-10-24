import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import { Button } from "./ui/button";

interface FuelTankDetailSheetProps {
  isOpen: boolean;
  onClose: () => void;
  current: number;
  target: number;
  percentage: number;
  remaining: number;
  label: string;
}

export function FuelTankDetailSheet({
  isOpen,
  onClose,
  current,
  target,
  percentage,
  remaining,
  label
}: FuelTankDetailSheetProps) {
  
  // Sample meal breakdown data
  const mealBreakdown = [
    {
      meal: "🌅 Breakfast",
      food: "Akara + Pap",
      calories: 380,
      percentage: Math.round((380 / target) * 100),
      time: "7:30 AM"
    },
    {
      meal: "🍽️ Lunch", 
      food: "Jollof + Fish",
      calories: 650,
      percentage: Math.round((650 / target) * 100),
      time: "1:15 PM"
    },
    {
      meal: "🌙 Dinner Budget",
      food: "Suggest: Eba + Soup",
      calories: remaining,
      percentage: Math.round((remaining / target) * 100),
      time: "Available",
      isBudget: true
    }
  ].filter(meal => meal.calories > 0);

  const getStatusMessage = () => {
    if (percentage === 100) {
      return {
        icon: "🎉",
        title: "Perfect Fuel Day!",
        message: "You've hit your calorie target perfectly. Great balance!",
        tip: "Keep this momentum going tomorrow 💚"
      };
    } else if (percentage > 100) {
      return {
        icon: "⚠️",
        title: "Over Target",
        message: `You've consumed ${current - target} extra calories today.`,
        tip: "That's okay! One day won't derail your progress. Try lighter options tomorrow."
      };
    } else if (percentage >= 80) {
      return {
        icon: "💚",
        title: "On Track!",
        message: `You're doing great! ${remaining} calories left for the day.`,
        tip: "Perfect for a light dinner. Maybe some vegetable soup?"
      };
    } else {
      return {
        icon: "🔋",
        title: "More Fuel Needed",
        message: `You still need ${remaining} calories to reach your target.`,
        tip: "Don't forget to fuel your body properly for energy and health."
      };
    }
  };

  const statusMessage = getStatusMessage();
  
  // Calculate fill height for large tank
  const fillHeight = Math.min(percentage, 100);

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
            className="fixed bottom-0 left-0 right-0 z-50 bg-background rounded-t-3xl max-h-[90vh] overflow-hidden shadow-2xl"
          >
            {/* Handle */}
            <div className="flex justify-center py-4">
              <div className="w-12 h-1 bg-muted-foreground/30 rounded-full" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-6 pb-4">
              <h2 className="text-xl font-semibold text-[rgb(255,248,248)]">FUEL BREAKDOWN</h2>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="w-6 h-6" />
              </Button>
            </div>

            {/* Content */}
            <div className="px-6 pb-8 overflow-y-auto max-h-[calc(90vh-100px)] bg-background">
              {/* Large Fuel Tank */}
              <div className="flex justify-center mb-6">
                <div className="relative">
                  <svg width="140" height="180" viewBox="0 0 140 180" className="drop-shadow-lg">
                    <defs>
                      <clipPath id="largeTankClip">
                        <path d="M20 0 L120 0 L140 20 L140 160 L120 180 L20 180 L0 160 L0 20 Z"/>
                      </clipPath>
                      
                      <linearGradient id="largeFillGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#4CAF50"/>
                        <stop offset="100%" stopColor="#66BB6A"/>
                      </linearGradient>
                    </defs>
                    
                    {/* Tank outline */}
                    <path 
                      d="M20 0 L120 0 L140 20 L140 160 L120 180 L20 180 L0 160 L0 20 Z"
                      fill="none"
                      stroke="rgb(var(--color-border))"
                      strokeWidth="3"
                    />
                    
                    {/* Empty portion */}
                    <rect 
                      x="0" y="0" width="140" height="180"
                      fill="rgb(var(--color-fuel-empty))"
                      clipPath="url(#largeTankClip)"
                    />
                    
                    {/* Filled portion */}
                    <motion.rect 
                      x="0" 
                      y={180 - (fillHeight * 1.8)}
                      width="140" 
                      height={fillHeight * 1.8}
                      fill="url(#largeFillGradient)"
                      clipPath="url(#largeTankClip)"
                      initial={{ height: 0, y: 180 }}
                      animate={{ 
                        height: fillHeight * 1.8, 
                        y: 180 - (fillHeight * 1.8) 
                      }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                    />
                  </svg>
                  
                  {/* Percentage text */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <motion.span 
                      className="text-4xl font-black text-foreground"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.5, delay: 0.5 }}
                    >
                      {percentage}%
                    </motion.span>
                  </div>
                </div>
              </div>

              {/* Summary */}
              <div className="text-center mb-6">
                <p className="text-2xl font-bold mb-1 text-[rgb(255,243,243)]">
                  {current.toLocaleString()} of {target.toLocaleString()} {label}
                </p>
                <p className="text-muted-foreground">
                  {remaining > 0 
                    ? `${remaining.toLocaleString()} remaining (${Math.round((remaining/target)*100)}%)`
                    : percentage > 100 
                    ? `${current - target} over target`
                    : "Target reached!"
                  }
                </p>
              </div>

              {/* Divider */}
              <hr className="border-border mb-6" />

              {/* Today's Meals */}
              <div className="mb-6">
                <h3 className="font-semibold mb-4 text-[rgb(250,250,250)]">TODAY'S MEALS:</h3>
                <div className="space-y-4">
                  {mealBreakdown.map((meal, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-medium text-[rgb(255,255,255)]">{meal.meal}</p>
                          <p className="text-sm text-muted-foreground">
                            {meal.food} • {meal.time}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-[rgb(255,246,246)]">
                            {meal.isBudget ? `${meal.calories}` : meal.calories} {label}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {meal.percentage}%
                          </p>
                        </div>
                      </div>
                      
                      {/* Mini progress bar */}
                      <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                        <motion.div
                          className={`h-full rounded-full ${
                            meal.isBudget 
                              ? 'bg-muted-foreground/40' 
                              : 'bg-primary'
                          }`}
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min(meal.percentage, 100)}%` }}
                          transition={{ duration: 0.6, delay: index * 0.1 }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Divider */}
              <hr className="border-border mb-6" />

              {/* This Week's Progress */}
              <div className="mb-6">
                <h3 className="font-semibold mb-4 text-[rgb(255,249,249)] flex items-center gap-2">
                  🚀 This Week's Progress
                </h3>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <span className="text-sm text-muted-foreground">Meals logged</span>
                    <span className="font-semibold text-[rgb(255,246,246)]">18/21</span>
                  </div>
                  
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <span className="text-sm text-muted-foreground">Calorie target hit</span>
                    <span className="font-semibold text-[rgb(255,246,246)]">5/7 days</span>
                  </div>
                  
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <span className="text-sm text-muted-foreground">Best day</span>
                    <span className="font-semibold text-primary">Tuesday (92%)</span>
                  </div>
                </div>
              </div>

              {/* Divider */}
              <hr className="border-border mb-6" />

              {/* Status Message */}
              <div className="mb-6">
                <h3 className="font-semibold mb-3 text-[rgb(255,249,249)]">{statusMessage.title}</h3>
                <p className="text-muted-foreground mb-4">
                  {statusMessage.message}
                </p>
                
                <div className="bg-primary/10 rounded-lg p-4">
                  <h4 className="font-medium mb-2 text-[rgb(255,247,247)]">{statusMessage.icon} Tip</h4>
                  <p className="text-sm text-[rgb(255,248,248)]">{statusMessage.tip}</p>
                </div>
              </div>

              {/* Action Button */}
              <Button 
                onClick={onClose}
                className="w-full mb-6"
                variant="default"
              >
                Got it!
              </Button>

              {/* Extra bottom spacing for scroll */}
              <div className="h-4"></div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}