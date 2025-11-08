import { X, Home, Camera, BarChart3, User, MessageCircle } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";

interface MenuDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (screen: string) => void;
  currentScreen: string;
}

export function MenuDrawer({ isOpen, onClose, onNavigate, currentScreen }: MenuDrawerProps) {
  const primaryMenuItems = [
    { id: 'home', label: 'Home', icon: Home, badge: null },
    { id: 'chat', label: 'Chat with KAI', icon: MessageCircle, badge: null },
    { id: 'camera', label: 'Log meal', icon: Camera, badge: null },
    { id: 'profile', label: 'Profile', icon: User, badge: null },
  ];

  const handleNavigate = (screenId: string) => {
    onNavigate(screenId);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed left-0 top-0 h-full w-80 bg-background z-50 shadow-xl overflow-y-auto">
        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-semibold text-primary">KAI</h2>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="w-6 h-6" />
            </Button>
          </div>

          {/* Primary Navigation */}
          <div className="space-y-2 mb-6">
            {primaryMenuItems.map((item) => (
              <Button
                key={item.id}
                variant={currentScreen === item.id ? "secondary" : "ghost"}
                className="w-full justify-start h-12"
                onClick={() => handleNavigate(item.id)}
              >
                <item.icon className="w-5 h-5 mr-3" />
                <span className="flex-1 text-left">{item.label}</span>
                {item.badge && (
                  <Badge variant="secondary" className="ml-2">
                    {item.badge}
                  </Badge>
                )}
              </Button>
            ))}
          </div>

          {/* User Info Card */}
          <Card 
            className="mt-8 p-4 bg-primary/5 border-primary/20 cursor-pointer hover:bg-primary/10 transition-colors duration-200"
            onClick={() => handleNavigate('profile')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                handleNavigate('profile');
              }
            }}
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center">
                <span className="text-primary font-semibold">AO</span>
              </div>
              <div className="flex-1">
                <p className="font-medium text-sm">Adaeze Okafor</p>
                <p className="text-xs text-muted-foreground">🔥 7-day streak</p>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-primary/10">
              <p className="text-xs text-primary font-medium">
                Built for Nigerians 🇳🇬
              </p>
            </div>
          </Card>

          {/* App Version */}
          <div className="mt-6 text-center">
            <p className="text-xs text-muted-foreground">KAI v1.0.0</p>
          </div>
        </div>
      </div>
    </>
  );
}