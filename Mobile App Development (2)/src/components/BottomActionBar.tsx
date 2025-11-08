import { MessageCircle, Plus } from "lucide-react";
import { MicrosIcon } from "./MicrosIcon";
import { useEffect, useState } from "react";

interface BottomActionBarProps {
  onChatClick: () => void;
  onLogMealClick: () => void;
  onMicrosClick: () => void;
  isCapturing?: boolean;
}

export function BottomActionBar({ 
  onChatClick, 
  onLogMealClick, 
  onMicrosClick,
  isCapturing = false 
}: BottomActionBarProps) {
  const [scrolled, setScrolled] = useState(false);
  const [activeButton, setActiveButton] = useState<'chat' | 'plus' | 'micros' | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleButtonClick = (button: 'chat' | 'plus' | 'micros', callback: () => void) => {
    setActiveButton(button);
    setTimeout(() => setActiveButton(null), 800);
    callback();
  };

  return (
    <>
      <div 
        className={`fixed bottom-0 left-0 right-0 z-50 flex justify-center pointer-events-none transition-all duration-300 ease-out ${
          scrolled ? '-translate-y-0.5' : ''
        }`}
        style={{
          paddingBottom: 'max(12px, env(safe-area-inset-bottom))'
        }}
      >
        <div className="w-full max-w-md px-5 pointer-events-auto">
          {/* Clean, professional bar */}
          <div 
            className="relative mx-auto transition-all duration-300"
            style={{ 
              width: 'calc(100% - 40px)',
              maxWidth: '360px',
              height: '64px',
              background: 'rgba(255, 255, 255, 0.08)',
              backdropFilter: 'blur(16px)',
              WebkitBackdropFilter: 'blur(16px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '16px',
              boxShadow: scrolled 
                ? '0 12px 32px rgba(0, 0, 0, 0.35)'
                : '0 8px 24px rgba(0, 0, 0, 0.25)',
            }}
          >
            {/* Bar content */}
            <div className="flex items-center justify-between h-full px-5">
              {/* Left - Chat */}
              <div className="relative flex flex-col items-center">
                <button
                  onClick={() => handleButtonClick('chat', onChatClick)}
                  className={`flex items-center justify-center w-11 h-11 rounded-full transition-all duration-200 ${
                    activeButton === 'chat' 
                      ? 'bg-primary/20 text-primary scale-95' 
                      : 'text-muted-foreground hover:bg-primary/10 hover:text-primary active:scale-95'
                  }`}
                  aria-label="Open chat"
                >
                  <MessageCircle className="w-6 h-6" strokeWidth={2} />
                </button>
                {/* Optional micro underline */}
                {activeButton === 'chat' && (
                  <div 
                    className="absolute -bottom-2 h-0.5 bg-primary rounded-full animate-underline"
                    style={{ width: '28px' }}
                  />
                )}
              </div>

              {/* Center - Log Meal (Primary, no glow, no notch) */}
              <div className="relative flex flex-col items-center">
                <button
                  onClick={() => handleButtonClick('plus', onLogMealClick)}
                  disabled={isCapturing}
                  className={`flex items-center justify-center rounded-full transition-all duration-200 ${
                    activeButton === 'plus' ? 'scale-95' : 'scale-100'
                  } ${
                    isCapturing 
                      ? 'opacity-70 cursor-not-allowed' 
                      : 'hover:scale-105 active:scale-95'
                  }`}
                  aria-label="Log meal"
                  style={{
                    width: '56px',
                    height: '56px',
                    background: 'var(--primary)',
                    color: 'var(--primary-foreground)',
                  }}
                >
                  {isCapturing ? (
                    <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
                  ) : (
                    <Plus className="w-7 h-7" strokeWidth={2.5} />
                  )}
                </button>
                {/* Optional micro underline */}
                {activeButton === 'plus' && (
                  <div 
                    className="absolute -bottom-2 h-0.5 bg-primary rounded-full animate-underline"
                    style={{ width: '28px' }}
                  />
                )}
              </div>

              {/* Right - Micros */}
              <div className="relative flex flex-col items-center">
                <button
                  onClick={() => handleButtonClick('micros', onMicrosClick)}
                  className={`flex items-center justify-center w-11 h-11 rounded-full transition-all duration-200 ${
                    activeButton === 'micros' 
                      ? 'bg-primary/20 text-primary scale-95' 
                      : 'text-muted-foreground hover:bg-primary/10 hover:text-primary active:scale-95'
                  }`}
                  aria-label="View micronutrients"
                >
                  <MicrosIcon className="w-6 h-6" />
                </button>
                {/* Optional micro underline */}
                {activeButton === 'micros' && (
                  <div 
                    className="absolute -bottom-2 h-0.5 bg-primary rounded-full animate-underline"
                    style={{ width: '28px' }}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes underline {
          0% {
            opacity: 0;
            transform: scaleX(0.5);
          }
          20% {
            opacity: 1;
            transform: scaleX(1);
          }
          80% {
            opacity: 1;
            transform: scaleX(1);
          }
          100% {
            opacity: 0;
            transform: scaleX(0.8);
          }
        }

        .animate-underline {
          animation: underline 800ms ease-out;
        }
      `}</style>
    </>
  );
}
