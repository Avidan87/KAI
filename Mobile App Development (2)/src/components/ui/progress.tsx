"use client";

import * as React from "react";
import * as ProgressPrimitive from "@radix-ui/react-progress@1.1.2";

import { cn } from "./utils";

function Progress({
  className,
  value,
  style,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  const progressColor = (style as any)?.['--progress-color'];
  
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn(
        "bg-primary/20 relative h-2 w-full overflow-hidden rounded-full",
        className,
      )}
      style={progressColor ? { backgroundColor: `${progressColor}20` } : undefined}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="bg-primary h-full w-full flex-1 transition-all"
        style={{ 
          transform: `translateX(-${100 - (value || 0)}%)`,
          ...(progressColor ? { backgroundColor: progressColor } : {})
        }}
      />
    </ProgressPrimitive.Root>
  );
}

export { Progress };
