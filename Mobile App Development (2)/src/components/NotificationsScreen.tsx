import { useState } from "react";
import { ArrowLeft, Bell, TrendingUp, Lightbulb, Clock, ChevronRight } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { toast } from "sonner@2.0.3";

interface NotificationsScreenProps {
  onBack: () => void;
  onNotificationTap: (notification: any) => void;
  onActionClick?: (action: string, notificationId: string) => void;
}

interface NotificationItem {
  id: string;
  type: 'health' | 'progress' | 'tip' | 'reminder';
  title: string;
  body: string;
  timestamp: string;
  isRead: boolean;
  badge: string;
  icon: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  actions?: Array<{ label: string; action: string; primary?: boolean }>;
}

export function NotificationsScreen({ onBack, onNotificationTap, onActionClick }: NotificationsScreenProps) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([
    {
      id: '1',
      type: 'health',
      title: 'Health check: Iron low 14 days',
      body: 'Feeling unusually tired? Tap to confirm and see fixes 🌿',
      timestamp: '7:42 PM',
      isRead: false,
      badge: 'Critical',
      icon: '⚠️',
      priority: 'critical',
      actions: [
        { label: 'Yes', action: 'confirm_symptoms', primary: true },
        { label: 'No', action: 'dismiss' },
        { label: 'Later', action: 'snooze' }
      ]
    },
    {
      id: '2',
      type: 'progress',
      title: 'Great progress!',
      body: 'Iron up 92% this week. Headaches improving?',
      timestamp: '2:15 PM',
      isRead: false,
      badge: 'Celebrate 🎉',
      icon: '🎉',
      priority: 'high',
      actions: [
        { label: 'View progress', action: 'view_progress', primary: true }
      ]
    },
    {
      id: '3',
      type: 'tip',
      title: 'Quick tip',
      body: 'Add ugwu to lunch soup for +4.5mg iron',
      timestamp: '12:30 PM',
      isRead: true,
      badge: 'Tip 💡',
      icon: '💡',
      priority: 'medium',
      actions: [
        { label: 'Add to plan', action: 'add_to_plan', primary: true }
      ]
    },
    {
      id: '4',
      type: 'reminder',
      title: 'Log dinner?',
      body: 'Quick photo is enough. 10 seconds 📸',
      timestamp: '8:45 PM',
      isRead: true,
      badge: 'Reminder',
      icon: '🔔',
      priority: 'low',
      actions: [
        { label: 'Open camera', action: 'open_camera', primary: true }
      ]
    },
    {
      id: '5',
      type: 'tip',
      title: 'Nigerian nutrition tip',
      body: 'Groundnuts with orange juice boost iron absorption 3x! 🥜🍊',
      timestamp: 'Yesterday',
      isRead: true,
      badge: 'Tip 💡',
      icon: '💡',
      priority: 'medium'
    }
  ]);

  const handleMarkAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, isRead: true })));
    toast.success("All notifications marked as read");
  };

  const handleClearTips = () => {
    const tipsToRemove = notifications.filter(n => n.type === 'tip').length;
    setNotifications(prev => prev.filter(n => n.type !== 'tip'));
    toast.success(`${tipsToRemove} tip${tipsToRemove !== 1 ? 's' : ''} cleared`);
  };

  const getNotificationsByType = (type?: string) => {
    if (!type || type === 'all') return notifications;
    return notifications.filter(n => n.type === type);
  };

  const getIconColor = (type: string, priority: string) => {
    if (type === 'health' && priority === 'critical') return 'text-destructive';
    if (type === 'health') return 'text-accent';
    if (type === 'progress') return 'text-primary';
    if (type === 'tip') return 'text-accent';
    return 'text-muted-foreground';
  };

  const getBadgeVariant = (priority: string) => {
    if (priority === 'critical') return 'destructive';
    if (priority === 'high') return 'secondary';
    return 'outline';
  };

  const renderNotificationCard = (notification: NotificationItem) => (
    <Card 
      key={notification.id}
      className={`p-4 cursor-pointer hover:shadow-md transition-shadow ${
        !notification.isRead ? 'bg-primary/5 border-primary/20' : ''
      }`}
      onClick={() => onNotificationTap(notification)}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`text-xl ${getIconColor(notification.type, notification.priority)} flex-shrink-0 mt-1`}>
          {notification.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3 className={`text-sm ${!notification.isRead ? 'font-semibold' : 'font-medium'}`}>
              {notification.title}
            </h3>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Badge variant={getBadgeVariant(notification.priority)} className="text-xs">
                {notification.badge}
              </Badge>
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            </div>
          </div>
          
          <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
            {notification.body}
          </p>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {notification.timestamp}
            </span>
            
            {/* Quick Actions */}
            {notification.actions && (
              <div className="flex gap-2">
                {notification.actions.slice(0, 2).map((action, index) => (
                  <Button
                    key={index}
                    variant={action.primary ? "default" : "outline"}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onActionClick) {
                        onActionClick(action.action, notification.id);
                      }
                    }}
                  >
                    {action.label}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Card>
  );

  const unreadCount = notifications.filter(n => !n.isRead).length;
  const healthCount = notifications.filter(n => n.type === 'health' && !n.isRead).length;
  const tipsCount = notifications.filter(n => n.type === 'tip' && !n.isRead).length;
  const progressCount = notifications.filter(n => n.type === 'progress' && !n.isRead).length;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 pb-6">
        <Button variant="ghost" size="icon" onClick={onBack} className="text-[rgb(254,243,243)]">
          <ArrowLeft className="w-6 h-6" />
        </Button>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold text-[rgb(255,250,250)]">Notifications</h1>
          {unreadCount > 0 && (
            <Badge variant="destructive" className="text-xs">
              {unreadCount}
            </Badge>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="px-4">
        <Tabs defaultValue="all" className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-6">
            <TabsTrigger value="all" className="text-xs">
              All
              {unreadCount > 0 && (
                <Badge variant="secondary" className="ml-2 text-xs h-5 w-5 p-0 flex items-center justify-center">
                  {unreadCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="health" className="text-xs">
              Health
              {healthCount > 0 && (
                <Badge variant="secondary" className="ml-2 text-xs h-5 w-5 p-0 flex items-center justify-center">
                  {healthCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="tip" className="text-xs">
              Tips
              {tipsCount > 0 && (
                <Badge variant="secondary" className="ml-2 text-xs h-5 w-5 p-0 flex items-center justify-center">
                  {tipsCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="progress" className="text-xs">
              Progress
              {progressCount > 0 && (
                <Badge variant="secondary" className="ml-2 text-xs h-5 w-5 p-0 flex items-center justify-center">
                  {progressCount}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-3">
            {getNotificationsByType().length > 0 ? (
              getNotificationsByType().map(renderNotificationCard)
            ) : (
              <div className="text-center py-12">
                <Bell className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-semibold mb-2">No notifications yet</h3>
                <p className="text-sm text-muted-foreground">
                  You'll see health check-ins and progress here.
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="health" className="space-y-3">
            {getNotificationsByType('health').length > 0 ? (
              getNotificationsByType('health').map(renderNotificationCard)
            ) : (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">⚠️</div>
                <h3 className="font-semibold mb-2">No health alerts</h3>
                <p className="text-sm text-muted-foreground">
                  I'll notify you about important health patterns.
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="tip" className="space-y-3">
            {getNotificationsByType('tip').length > 0 ? (
              getNotificationsByType('tip').map(renderNotificationCard)
            ) : (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">💡</div>
                <h3 className="font-semibold mb-2">No tips yet</h3>
                <p className="text-sm text-muted-foreground">
                  I'll share nutrition tips based on your meals.
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="progress" className="space-y-3">
            {getNotificationsByType('progress').length > 0 ? (
              getNotificationsByType('progress').map(renderNotificationCard)
            ) : (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">🎉</div>
                <h3 className="font-semibold mb-2">No progress updates</h3>
                <p className="text-sm text-muted-foreground">
                  Keep logging meals to see progress celebrations!
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Bulk Actions */}
        {unreadCount > 0 && (
          <div className="mt-6 pt-4 border-t">
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                size="sm" 
                className="flex-1"
                onClick={handleMarkAllAsRead}
              >
                Mark all as read
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                className="flex-1"
                onClick={handleClearTips}
              >
                Clear tips
              </Button>
            </div>
          </div>
        )}

        <div className="h-8"></div>
      </div>
    </div>
  );
}