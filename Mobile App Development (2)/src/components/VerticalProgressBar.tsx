import { motion } from "motion/react";
import { useState } from "react";
import { FuelTankDetailSheet } from "./FuelTankDetailSheet";

interface VerticalProgressBarProps {
  current: number;
  target: number;
  percentage: number;
  label?: string;
  onOpenChange?: (isOpen: boolean) => void;
}

export function VerticalProgressBar({ current, target, percentage, label = "kcal", onOpenChange }: VerticalProgressBarProps) {
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isPressed, setIsPressed] = useState(false);
  
  const remaining = Math.max(0, target - current);
  
  // Determine fill colors based on percentage
  const isOverTarget = percentage >= 100;
  
  // Calculate fill angle (max 360° of circle)
  const fillAngle = Math.min(percentage, 100) * 3.6; // 100% = 360°

  return (
    <>
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => {
          setIsDetailOpen(true);
          onOpenChange?.(true);
        }}
        onPointerDown={() => setIsPressed(true)}
        onPointerUp={() => setIsPressed(false)}
        onPointerCancel={() => setIsPressed(false)}
        className="relative grid grid-cols-[auto_1fr] gap-4 p-3 pl-3 h-[155px] bg-card rounded-2xl shadow-sm border cursor-pointer hover:shadow-md transition-all duration-200"
        role="button"
        tabIndex={0}
        aria-label={`Your body fuel, ${current} of ${target} ${label}, ${percentage} percent filled`}
      >
        {/* Ripple effect */}
        {isPressed && (
          <motion.div
            className="absolute inset-0 rounded-2xl bg-primary/10"
            initial={{ opacity: 0.5 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          />
        )}

        {/* Orange Slice Tank Visual (Left Side) - 96×96 px with 120×140 touch target */}
        <div className="flex items-center justify-center min-w-[120px] h-[140px] -my-4">
          <div className="relative w-24 h-24">
            <svg width="96" height="96" viewBox="0 0 96 96" className="drop-shadow-sm">
              <defs>
                {/* Orange gradient for filled segments */}
                <linearGradient id="orangeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#FFA72E"/>
                  <stop offset="100%" stopColor="#FF7A00"/>
                </linearGradient>
                
                {/* Radial sweep mask */}
                <mask id="sweepMask">
                  <rect x="0" y="0" width="96" height="96" fill="black"/>
                  <motion.path
                    d="M 48 48 L 48 0 A 48 48 0 0 1 48 0 Z"
                    fill="white"
                    initial={{ d: "M 48 48 L 48 0 A 48 48 0 0 0 48 0 Z" }}
                    animate={{ 
                      d: fillAngle >= 360 
                        ? "M 48 48 L 48 0 A 48 48 0 1 1 47.99 0 Z"
                        : fillAngle >= 180
                        ? `M 48 48 L 48 0 A 48 48 0 1 1 ${48 + 48 * Math.sin((fillAngle - 180) * Math.PI / 180)} ${48 - 48 * Math.cos((fillAngle - 180) * Math.PI / 180)} Z`
                        : `M 48 48 L 48 0 A 48 48 0 0 1 ${48 + 48 * Math.sin(fillAngle * Math.PI / 180)} ${48 - 48 * Math.cos(fillAngle * Math.PI / 180)} Z`
                    }}
                    transition={{ duration: 0.6, ease: "easeOut", delay: 0.3 }}
                  />
                </mask>
              </defs>
              
              {/* Outer circle - 2px outline */}
              <circle 
                cx="48" 
                cy="48" 
                r="47"
                fill="none"
                stroke="#FF7A00"
                strokeWidth="2"
              />
              
              {/* Background circle - light orange #FFE8CC */}
              <circle 
                cx="48" 
                cy="48" 
                r="45"
                fill="#FFE8CC"
              />
              
              {/* 8 segment dividers radiating from center */}
              {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => (
                <line
                  key={angle}
                  x1="48"
                  y1="48"
                  x2={48 + 45 * Math.sin(angle * Math.PI / 180)}
                  y2={48 - 45 * Math.cos(angle * Math.PI / 180)}
                  stroke="#FFE8CC"
                  strokeWidth="2"
                />
              ))}
              
              {/* Filled portion with radial sweep (uses mask) */}
              <circle 
                cx="48" 
                cy="48" 
                r="45"
                fill="url(#orangeGradient)"
                mask="url(#sweepMask)"
              />
              
              {/* Segment dividers over fill - darker */}
              {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => (
                <line
                  key={`divider-${angle}`}
                  x1="48"
                  y1="48"
                  x2={48 + 45 * Math.sin(angle * Math.PI / 180)}
                  y2={48 - 45 * Math.cos(angle * Math.PI / 180)}
                  stroke="#FFA72E"
                  strokeWidth="1.5"
                  opacity="0.4"
                />
              ))}
              
              {/* Center white circle for pulp effect */}
              <circle 
                cx="48" 
                cy="48" 
                r="8"
                fill="#FFF"
                opacity="0.9"
              />
              
              {/* Small leaf at top */}
              <motion.g
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.5 }}
              >
                <ellipse
                  cx="48"
                  cy="-2"
                  rx="4"
                  ry="6"
                  fill="#66BB6A"
                  transform="rotate(-15 48 -2)"
                />
                <path
                  d="M 48 -2 Q 50 2 48 6"
                  stroke="#4CAF50"
                  strokeWidth="1"
                  fill="none"
                />
              </motion.g>
              
              {/* Overflow droplet for ≥100% */}
              {percentage >= 100 && (
                <motion.ellipse
                  cx="48"
                  cy="98"
                  rx="3"
                  ry="4"
                  fill="#FF9800"
                  initial={{ opacity: 0, cy: 96 }}
                  animate={{ opacity: 1, cy: 98 }}
                  transition={{ duration: 0.4, delay: 0.9 }}
                />
              )}
            </svg>
            
            {/* Percentage text - 28-30px Extra-Bold, white, 1px dark shadow */}
            <div className="absolute inset-0 flex items-center justify-center">
              <motion.span 
                className="text-[28px] font-extrabold text-white"
                style={{ textShadow: "1px 1px 2px rgba(0, 0, 0, 0.8)" }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, delay: 0.7 }}
              >
                {percentage}%
              </motion.span>
            </div>
          </div>
        </div>

        {/* Text Stack (Right Side) - min 180px */}
        <div className="flex flex-col justify-center gap-1 min-w-[180px]">
          {/* Current calories - 18px Bold */}
          <motion.div 
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.4 }}
          >
            <span className="text-[18px] font-bold text-foreground">{current.toLocaleString()}</span>
          </motion.div>
          
          {/* Target - 14px Regular */}
          <motion.p 
            className="text-[14px] text-muted-foreground"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.6 }}
          >
            of {target.toLocaleString()} {label}
          </motion.p>
          
          {/* Remaining/Status - 14px Regular */}
          <motion.p
            className="text-[14px] text-muted-foreground"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.8 }}
          >
            {percentage < 100 ? (
              `${remaining.toLocaleString()} left to fuel 💚`
            ) : percentage === 100 ? (
              `🎉 Perfect fuel day!`
            ) : (
              `⚠️ ${(current - target).toLocaleString()} over target`
            )}
          </motion.p>
          
          {/* Tap hint - 12px accent green */}
          <motion.p 
            className="text-[12px] text-primary mt-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, delay: 1.0 }}
          >
            Tap for details
          </motion.p>
        </div>
      </motion.div>

      {/* Detail Sheet */}
      <FuelTankDetailSheet
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          onOpenChange?.(false);
        }}
        current={current}
        target={target}
        percentage={percentage}
        remaining={remaining}
        label={label}
      />
    </>
  );
}