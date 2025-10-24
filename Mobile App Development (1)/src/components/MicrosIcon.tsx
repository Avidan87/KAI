interface MicrosIconProps {
  className?: string;
}

export function MicrosIcon({ className = "w-6 h-6" }: MicrosIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Micronutrients"
    >
      {/* Pentagon cluster of 5 dots representing key micronutrients */}
      
      {/* Iron - Deep Red - Top center (largest, most critical) */}
      <circle cx="12" cy="5.5" r="2.8" fill="#D64545" opacity="0.95">
        <animate
          attributeName="opacity"
          values="0.95;1;0.95"
          dur="3s"
          repeatCount="indefinite"
        />
      </circle>
      
      {/* Calcium - Cool Blue - Top right */}
      <circle cx="17.5" cy="9.5" r="2.4" fill="#4C86E8" opacity="0.9">
        <animate
          attributeName="opacity"
          values="0.9;0.95;0.9"
          dur="3s"
          begin="0.6s"
          repeatCount="indefinite"
        />
      </circle>
      
      {/* Magnesium - Teal - Bottom right */}
      <circle cx="15.5" cy="16.5" r="2.2" fill="#2FB7A1" opacity="0.85">
        <animate
          attributeName="opacity"
          values="0.85;0.9;0.85"
          dur="3s"
          begin="1.2s"
          repeatCount="indefinite"
        />
      </circle>
      
      {/* Zinc - Slate/Steel - Bottom left */}
      <circle cx="8.5" cy="16.5" r="2" fill="#7A8CA8" opacity="0.8">
        <animate
          attributeName="opacity"
          values="0.8;0.85;0.8"
          dur="3s"
          begin="1.8s"
          repeatCount="indefinite"
        />
      </circle>
      
      {/* Vitamin D - Warm Amber - Top left */}
      <circle cx="6.5" cy="9.5" r="2.5" fill="#F5A524" opacity="0.92">
        <animate
          attributeName="opacity"
          values="0.92;0.97;0.92"
          dur="3s"
          begin="2.4s"
          repeatCount="indefinite"
        />
      </circle>
      
      {/* Subtle connecting lines to suggest interconnection */}
      <path
        d="M12 5.5 L17.5 9.5 L15.5 16.5 L8.5 16.5 L6.5 9.5 Z"
        stroke="currentColor"
        strokeWidth="0.5"
        opacity="0.12"
        fill="none"
      />
    </svg>
  );
}

export function MicrosIconFlask({ className = "w-6 h-6" }: MicrosIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Micronutrients"
    >
      {/* Flask outline */}
      <path
        d="M9 2 L9 9 L5.5 16.5 C4.8 18 4.8 19 5.5 20 L18.5 20 C19.2 19 19.2 18 18.5 16.5 L15 9 L15 2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        opacity="0.9"
      />
      <line 
        x1="9" y1="2" x2="15" y2="2" 
        stroke="currentColor" 
        strokeWidth="1.8" 
        strokeLinecap="round" 
        opacity="0.9"
      />
      
      {/* Liquid inside with gradient effect */}
      <path
        d="M6.2 17.5 C5.9 18 5.9 18.5 6.2 19 L17.8 19 C18.1 18.5 18.1 18 17.8 17.5 L15 12.5 L9 12.5 Z"
        fill="currentColor"
        opacity="0.15"
      />
      
      {/* Sparkles with animation */}
      <g opacity="0.7">
        <path d="M10 6 L10.4 7 L11 6.5 L10.6 6 Z" fill="currentColor">
          <animate
            attributeName="opacity"
            values="0.7;1;0.7"
            dur="2s"
            repeatCount="indefinite"
          />
        </path>
        <path d="M13.5 4 L13.9 5 L14.5 4.5 L14.1 4 Z" fill="currentColor">
          <animate
            attributeName="opacity"
            values="0.7;1;0.7"
            dur="2s"
            begin="0.5s"
            repeatCount="indefinite"
          />
        </path>
        <path d="M8.5 14 L8.7 14.5 L9 14.3 L8.8 14 Z" fill="currentColor">
          <animate
            attributeName="opacity"
            values="0.5;0.9;0.5"
            dur="2s"
            begin="1s"
            repeatCount="indefinite"
          />
        </path>
        <path d="M15.2 15 L15.4 15.5 L15.7 15.3 L15.5 15 Z" fill="currentColor">
          <animate
            attributeName="opacity"
            values="0.5;0.9;0.5"
            dur="2s"
            begin="1.5s"
            repeatCount="indefinite"
          />
        </path>
      </g>
      
      {/* Top sparkle accent */}
      <circle cx="11.5" cy="3" r="0.8" fill="currentColor" opacity="0.6">
        <animate
          attributeName="opacity"
          values="0.6;1;0.6"
          dur="1.5s"
          repeatCount="indefinite"
        />
      </circle>
    </svg>
  );
}
