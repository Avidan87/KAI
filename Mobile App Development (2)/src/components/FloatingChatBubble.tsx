import { MessageCircle } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

interface FloatingChatBubbleProps {
  isVisible: boolean;
  unreadCount?: number;
  onClick: () => void;
}

export function FloatingChatBubble({ isVisible, unreadCount = 0, onClick }: FloatingChatBubbleProps) {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          whileTap={{ scale: 0.9 }}
          onClick={onClick}
          className="fixed bottom-20 right-4 z-50 w-14 h-14 bg-primary rounded-full shadow-lg flex items-center justify-center text-primary-foreground hover:shadow-xl transition-shadow"
          aria-label={`Chat with KAI${unreadCount > 0 ? `, ${unreadCount} unread messages` : ''}`}
        >
          <MessageCircle className="w-6 h-6" />
          
          {unreadCount > 0 && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="absolute -top-1 -right-1 w-6 h-6 bg-accent text-accent-foreground rounded-full flex items-center justify-center text-xs font-bold"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </motion.div>
          )}

          {/* Pulse animation for new messages */}
          {unreadCount > 0 && (
            <motion.div
              className="absolute inset-0 rounded-full bg-primary"
              animate={{
                scale: [1, 1.3, 1],
                opacity: [0.5, 0, 0.5]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          )}
        </motion.button>
      )}
    </AnimatePresence>
  );
}
