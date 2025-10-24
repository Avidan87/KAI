import { motion } from "motion/react";
import { useState } from "react";
import { HexagonDetailSheet } from "./HexagonDetailSheet";

interface HexagonProgressProps {
  label: string;
  current: number;
  target: number;
  unit: string;
  percentage: number;
  status: 'good' | 'warning' | 'critical';
  sources?: Array<{ meal: string; amount: number; time: string }>;
  education?: string;
  tip?: string;
  delay?: number;
  onOpenChange?: (isOpen: boolean) => void;
}

export function HexagonProgress({ 
  label, 
  current, 
  target, 
  unit, 
  percentage, 
  status, 
  sources,
  education,
  tip,
  delay = 0,
  onOpenChange
}: HexagonProgressProps) {
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  // Macro-specific color configuration
  const getMacroConfig = () => {
    const normalizedLabel = label.toUpperCase();
    
    if (normalizedLabel.includes('PROTEIN') || normalizedLabel === 'PRO') {
      return {
        ringColor: '#3AB0FF',
        labelColor: '#3AB0FF',
        iconBg: '#E6F4FF',
        icon: '🫘'
      };
    } else if (normalizedLabel.includes('CARB')) {
      return {
        ringColor: '#FFB547',
        labelColor: '#FFB547',
        iconBg: '#FFF3E0',
        icon: '🍚'
      };
    } else { // FAT
      return {
        ringColor: '#7CB342',
        labelColor: '#7CB342',
        iconBg: '#ECF6E6',
        icon: '🥑'
      };
    }
  };

  const macroConfig = getMacroConfig();
  
  // Calculate actual percentage (capped at 100 for display)
  const actualPercentage = Math.round((current / target) * 100);
  const displayPercentage = Math.min(actualPercentage, 100);
  
  // Progress ring logic: 0-49% red tint, 50-79% 70% opacity, ≥80% full sat, >100% adds a subtle glow of that macro color.
  const getRingStyle = () => {
    if (actualPercentage < 50) {
      return {
        color: '#F44336', // Red tint overlay
        opacity: 1
      };
    } else if (actualPercentage < 80) {
      return {
        color: macroConfig.ringColor,
        opacity: 0.7 // 70% opacity
      };
    } else {
      return {
        color: macroConfig.ringColor,
        opacity: 1 // Full saturation
      };
    }
  };

  const ringStyle = getRingStyle();
  
  // Status glyph: ✓ ≥80%, ⚠️ 50-79%, ❌ <50%
  const getStatusGlyph = () => {
    if (actualPercentage >= 80) return '✓';
    if (actualPercentage >= 50) return '⚠️';
    return '❌';
  };

  // SVG circle properties
  const radius = 33; // Circle radius (72px total - 6px ring = 33px radius)
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (displayPercentage / 100) * circumference;

  return (
    <>
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay }}
        whileTap={{ scale: 0.98 }}
        onClick={() => {
          setIsDetailOpen(true);
          onOpenChange?.(true);
        }}
        onPointerDown={() => setIsPressed(true)}
        onPointerUp={() => setIsPressed(false)}
        onPointerCancel={() => setIsPressed(false)}
        className="flex flex-col items-center cursor-pointer"
        role="button"
        tabIndex={0}
        aria-label={`${label}, ${current} of ${target} ${unit}, ${actualPercentage} percent`}
      >
        {/* Circular Badge with Touch Target 88×96 px */}
        <div className="relative w-[88px] h-24 flex items-start justify-center pt-2">
          {/* Rounded Hex Badge - 72×80 px */}
          <div className="relative w-[72px] h-20">
            <svg width="72" height="80" viewBox="0 0 72 80" className="drop-shadow-sm hover:drop-shadow-md transition-all duration-200">
              {/* Background Track Ring - unfilled #2A2F33 */}
              <circle
                cx="36"
                cy="40"
                r={radius}
                fill="#0E1216"
                stroke="#2A2F33"
                strokeWidth="6"
              />
              
              {/* Progress Ring - animated stroke-dasharray */}
              <motion.circle
                cx="36"
                cy="40"
                r={radius}
                fill="none"
                stroke={ringStyle.color}
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                opacity={ringStyle.opacity}
                transform="rotate(-90 36 40)"
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset }}
                transition={{ duration: 0.6, ease: "easeOut", delay: delay + 0.3 }}
              />
              
              {/* Icon in Center */}
              <motion.text
                x="36"
                y="45"
                textAnchor="middle"
                fontSize="24"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.12, delay: delay + 0.7 }}
              >
                {macroConfig.icon}
              </motion.text>
            </svg>
          </div>
        </div>

        {/* Label Stack Below */}
        <motion.div
          className="mt-2 text-center flex flex-col items-center gap-0.5"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: delay + 0.9 }}
        >
          {/* UPPERCASE label - 12px Medium */}
          <p 
            className="text-[12px] font-medium uppercase tracking-wide"
            style={{ color: macroConfig.labelColor }}
          >
            {label === 'PRO' ? 'PROTEIN' : label === 'CARB' ? 'CARBS' : label}
          </p>
          
          {/* Grams bold (14px/700) + status glyph on same line */}
          <div className="flex items-center gap-1.5">
            <p className="text-[14px] font-bold" style={{ color: '#E7EDF2' }}>
              {current > 0 ? `${current}${unit}` : `0${unit}`}
            </p>
            <span className="text-[14px] text-[rgb(237,239,249)]">
              {getStatusGlyph()}
            </span>
          </div>
        </motion.div>
      </motion.div>

      {/* Detail Sheet */}
      <HexagonDetailSheet
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          onOpenChange?.(false);
        }}
        label={label}
        current={current}
        target={target}
        unit={unit}
        percentage={actualPercentage}
        status={status}
        color={macroConfig.ringColor}
        sources={sources}
        education={education}
        tip={tip}
      />
    </>
  );
}