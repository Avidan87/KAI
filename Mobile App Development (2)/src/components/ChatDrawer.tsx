import { Settings, Send, X } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  initialContext?: 'iron' | 'general';
}

interface ChatMessage {
  id: string;
  type: 'kai' | 'user';
  messageType: 'text' | 'nutrient_insight' | 'food_suggestion' | 'symptom_check' | 'progress_celebration';
  content: string;
  timestamp: Date;
  data?: any;
}

export function ChatDrawer({ isOpen, onClose, initialContext = 'general' }: ChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Initialize conversation
  useEffect(() => {
    if (!isOpen) return;
    
    setMessages([]); // Reset messages when drawer opens
    
    if (initialContext === 'iron') {
      // Open with iron context
      setTimeout(() => {
        addKaiMessage({
          type: 'kai',
          messageType: 'nutrient_insight',
          content: "I noticed your iron has been low for 14 days. Let me show you your current status.",
          data: {
            nutrient: 'Iron',
            current: 6.8,
            target: 18,
            percentage: 38,
            days: 14,
            symptoms: ['Fatigue', 'Headaches', 'Difficulty concentrating']
          }
        });
      }, 500);

      setTimeout(() => {
        addKaiMessage({
          type: 'kai',
          messageType: 'symptom_check',
          content: "Are you experiencing any of these symptoms?",
          data: {
            options: ['😴 Fatigue', '🤕 Headaches', '🧠 Brain fog', '❄️ Cold hands', '✅ None', '🤔 Not sure']
          }
        });
      }, 1500);
    } else {
      // General welcome message
      setTimeout(() => {
        addKaiMessage({
          type: 'kai',
          messageType: 'text',
          content: "Good morning Adaeze! I noticed your iron has been low for 12 days. How's your energy today? 💪"
        });
      }, 300);
    }
  }, [isOpen, initialContext]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages]);

  const addKaiMessage = (messageData: Partial<ChatMessage>) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'kai',
      messageType: 'text',
      timestamp: new Date(),
      ...messageData,
      content: messageData.content || ''
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const addUserMessage = (content: string) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      messageType: 'text',
      content,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    addUserMessage(inputValue);
    setInputValue('');

    // Simulate KAI typing and responding
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      addKaiMessage({
        type: 'kai',
        messageType: 'text',
        content: "That's helpful to know! Let me create a personalized plan to help boost your iron levels naturally with Nigerian foods you love."
      });
    }, 2000);
  };

  const handleQuickReply = (option: string) => {
    addUserMessage(option);

    // Simulate KAI response based on selection
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      
      if (option.includes('Fatigue')) {
        addKaiMessage({
          type: 'kai',
          messageType: 'text',
          content: "That makes perfect sense - iron deficiency often causes fatigue. Good news: we can fix this naturally! 💪"
        });

        setTimeout(() => {
          addKaiMessage({
            type: 'kai',
            messageType: 'food_suggestion',
            content: "Here are iron-rich Nigerian foods that can help:",
            data: {
              foods: [
                { name: 'Moi moi (2 wraps)', iron: '3.5mg', icon: '🫘' },
                { name: 'Extra ugwu in soup', iron: '4.5mg', icon: '🌿' },
                { name: 'Groundnuts (handful)', iron: '1.3mg', icon: '🥜' }
              ],
              location: 'Available at Balogun Market',
              cost: '₦500-800/day'
            }
          });
        }, 1500);
      } else if (option.includes('None')) {
        addKaiMessage({
          type: 'kai',
          messageType: 'text',
          content: "That's great! Even without symptoms, it's important to address low iron before it becomes a problem. Let me suggest some easy additions to your meals."
        });
      }
    }, 1500);
  };

  const handleActionButton = (action: string) => {
    if (action === 'create_plan') {
      addUserMessage("Yes, create a plan for me");
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        addKaiMessage({
          type: 'kai',
          messageType: 'progress_celebration',
          content: "🎉 Iron Boost Plan Created! I'll track your progress and send daily reminders. You've got this! 💚"
        });
      }, 2000);
    }
  };

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

          {/* Drawer */}
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed bottom-0 left-0 right-0 z-50 bg-[rgb(13,13,13)] rounded-t-3xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl"
          >
            {/* Handle */}
            <div className="flex justify-center py-3 bg-[rgb(13,13,13)]">
              <div className="w-12 h-1 bg-muted-foreground/30 rounded-full" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 pb-3 border-b border-border bg-[rgb(13,13,13)]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-xl">
                  🤖
                </div>
                <div>
                  <h2 className="font-semibold text-[rgb(255,248,248)]">KAI Coach</h2>
                  <p className="text-xs text-muted-foreground">Your nutrition assistant</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" className="text-[rgb(255,255,255)]">
                  <Settings className="w-5 h-5" />
                </Button>
                <Button variant="ghost" size="icon" onClick={onClose} className="text-[rgb(255,255,255)]">
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Messages Area */}
            <ScrollArea className="flex-1 p-4 bg-[rgb(13,13,13)]" ref={scrollAreaRef}>
              {messages.length === 0 ? (
                <EmptyState />
              ) : (
                <div className="space-y-4 pb-4">
                  <AnimatePresence>
                    {messages.map((message) => (
                      <ChatMessageComponent 
                        key={message.id} 
                        message={message}
                        onQuickReply={handleQuickReply}
                        onAction={handleActionButton}
                      />
                    ))}
                  </AnimatePresence>

                  {/* Typing Indicator */}
                  {isTyping && <TypingIndicator />}
                </div>
              )}
            </ScrollArea>

            {/* Input Area */}
            <div className="p-4 border-t border-border bg-[rgb(13,13,13)]">
              <div className="flex items-center gap-2">
                <Input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Type message..."
                  className="flex-1 text-[rgb(252,246,246)]"
                />
                <Button 
                  size="icon" 
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim()}
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// Empty State Component
function EmptyState() {
  return (
    <motion.div 
      className="flex flex-col items-center justify-center h-full py-12 px-6 text-center"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="text-5xl mb-3">🤖</div>
      <h2 className="text-lg font-semibold text-[rgb(255,248,248)] mb-2">
        Hi Adaeze! I'm KAI,
      </h2>
      <p className="text-sm text-muted-foreground mb-2">
        your nutrition coach.
      </p>
      <p className="text-sm text-muted-foreground">
        I'll help you understand your health through the foods you love! 🇳🇬
      </p>
    </motion.div>
  );
}

// Typing Indicator Component
function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-start gap-2"
    >
      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 text-lg">
        🤖
      </div>
      <div className="bg-primary/10 rounded-2xl rounded-tl-sm p-3 max-w-[80%]">
        <p className="text-sm text-muted-foreground mb-1">KAI is typing...</p>
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 bg-primary rounded-full"
              animate={{
                y: [0, -4, 0],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{
                duration: 0.6,
                repeat: Infinity,
                delay: i * 0.2
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// Chat Message Component
interface ChatMessageComponentProps {
  message: ChatMessage;
  onQuickReply: (option: string) => void;
  onAction: (action: string) => void;
}

function ChatMessageComponent({ message, onQuickReply, onAction }: ChatMessageComponentProps) {
  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return 'Just now';
    if (minutes === 1) return '1 min ago';
    if (minutes < 60) return `${minutes} min ago`;
    
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  };

  if (message.type === 'user') {
    return (
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="flex flex-col items-end"
      >
        <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm p-3 max-w-[80%]">
          <p className="text-[14px]">{message.content}</p>
        </div>
        <p className="text-xs text-muted-foreground mt-1">{formatTime(message.timestamp)}</p>
      </motion.div>
    );
  }

  // KAI messages
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="flex flex-col items-start"
    >
      <div className="flex items-start gap-2 w-full">
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 text-lg">
          🤖
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-primary mb-1">KAI</p>
          
          {message.messageType === 'text' && (
            <div className="bg-primary/10 rounded-2xl rounded-tl-sm p-3 max-w-[85%]">
              <p className="text-[14px] text-foreground">{message.content}</p>
            </div>
          )}

          {message.messageType === 'nutrient_insight' && (
            <div className="bg-primary/10 rounded-2xl rounded-tl-sm p-4 max-w-[85%]">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">📊</span>
                <h3 className="font-semibold text-foreground">Your {message.data.nutrient} Status</h3>
              </div>
              <div className="mb-3">
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-accent transition-all duration-500"
                      style={{ width: `${message.data.percentage}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold text-foreground">{message.data.percentage}%</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {message.data.current}/{message.data.target}mg
                </p>
              </div>
              <div className="bg-accent/10 rounded-lg p-2 mb-2">
                <p className="text-sm text-accent font-medium">⚠️ Low for {message.data.days} days</p>
              </div>
              <div>
                <p className="text-sm font-medium text-foreground mb-1">Common symptoms:</p>
                <div className="flex flex-wrap gap-1">
                  {message.data.symptoms.map((symptom: string, i: number) => (
                    <span key={i} className="text-sm text-muted-foreground">
                      • {symptom}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {message.messageType === 'food_suggestion' && (
            <div className="bg-primary/10 rounded-2xl rounded-tl-sm p-4 max-w-[85%]">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">🍽️</span>
                <h3 className="font-semibold text-foreground">Iron-Rich Nigerian Foods</h3>
              </div>
              <div className="space-y-3 mb-3">
                {message.data.foods.map((food: any, i: number) => (
                  <div key={i} className="bg-card rounded-lg p-2">
                    <div className="flex items-start gap-2">
                      <span className="text-xl">{food.icon}</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-foreground">{food.name}</p>
                        <p className="text-sm text-primary">→ +{food.iron} iron</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="text-sm text-muted-foreground">
                <p>📍 {message.data.location}</p>
                <p>• {message.data.cost}</p>
              </div>
            </div>
          )}

          {message.messageType === 'symptom_check' && (
            <div className="bg-primary/10 rounded-2xl rounded-tl-sm p-3 max-w-[85%]">
              <p className="text-[14px] text-foreground mb-3">{message.content}</p>
              <div className="flex flex-wrap gap-2">
                {message.data.options.map((option: string, i: number) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    onClick={() => onQuickReply(option)}
                    className="text-xs"
                  >
                    {option}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {message.messageType === 'progress_celebration' && (
            <div className="bg-green-500/10 rounded-2xl rounded-tl-sm p-4 max-w-[85%] border border-green-500/20">
              <p className="text-[14px] text-foreground">{message.content}</p>
              <div className="flex gap-2 mt-3">
                <Button
                  size="sm"
                  onClick={() => onAction('create_plan')}
                  className="bg-green-500 hover:bg-green-600 text-white"
                >
                  📋 View Plan
                </Button>
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground mt-1">{formatTime(message.timestamp)}</p>
        </div>
      </div>
    </motion.div>
  );
}
