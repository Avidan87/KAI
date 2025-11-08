import { useState } from "react";
import { HomeScreen } from "./components/HomeScreen";
import { CameraScreen } from "./components/CameraScreen";
import { ProcessingScreen } from "./components/ProcessingScreen";
import { MealResultScreen } from "./components/MealResultScreen";
import { HealthAlertScreen } from "./components/HealthAlertScreen";
import { MicrosOverviewScreen } from "./components/MicrosOverviewScreen";
import { ProfileScreen } from "./components/ProfileScreen";
import { NotificationsScreen } from "./components/NotificationsScreen";
import { ChatScreen } from "./components/ChatScreen";
import { ChatDrawer } from "./components/ChatDrawer";
import { MenuDrawer } from "./components/MenuDrawer";
import { BottomActionBar } from "./components/BottomActionBar";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner@2.0.3";

type Screen = 'home' | 'camera' | 'processing' | 'result' | 'alert' | 'micros' | 'profile' | 'notifications';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('home');
  const [capturedImage, setCapturedImage] = useState<string>('');
  const [mealResult, setMealResult] = useState<any>(null);
  const [isMenuOpen, setIsMenuOpen] = useState<boolean>(false);
  const [isChatDrawerOpen, setIsChatDrawerOpen] = useState<boolean>(false);
  const [chatContext, setChatContext] = useState<'iron' | 'general'>('general');
  const [isDetailSheetOpen, setIsDetailSheetOpen] = useState<boolean>(false);

  const navigateToScreen = (screen: Screen) => {
    setCurrentScreen(screen);
  };

  const handleLogMeal = () => {
    navigateToScreen('camera');
  };

  const handleCapture = (imageUrl: string) => {
    setCapturedImage(imageUrl);
    navigateToScreen('processing');
  };

  const handleProcessingComplete = (result: any) => {
    setMealResult(result);
    navigateToScreen('result');
  };

  const handleMealConfirm = () => {
    toast.success("Meal logged successfully! 🎉");
    navigateToScreen('home');
  };

  const handleMealEdit = () => {
    toast.info("Edit functionality coming soon!");
  };

  const handleAddSuggestion = (suggestion: string) => {
    if (suggestion === 'ugwu') {
      toast.success("Ugwu added! +4.5mg iron boost 🌿");
      // In a real app, this would update the meal result with ugwu
      // and recalculate nutritional values
    } else {
      toast.success(`${suggestion} added to your meal!`);
    }
  };

  const handleStartPlan = () => {
    toast.success("Iron boost plan started! We'll track your progress 💪");
    navigateToScreen('home');
  };

  const handleMenuClick = () => {
    setIsMenuOpen(true);
  };

  const handleNotificationClick = () => {
    navigateToScreen('notifications');
  };

  const handleProfileClick = () => {
    navigateToScreen('profile');
  };

  const handleShareProgress = () => {
    toast.success("Progress shared! 🎉");
  };

  const handleLogout = () => {
    toast.success("Logged out successfully");
    // In a real app, clear user data and redirect to login
  };

  const handleNotificationTap = (notification: any) => {
    if (notification.type === 'health') {
      navigateToScreen('alert');
    } else if (notification.type === 'progress') {
      toast.info(`${notification.title} - Check your weekly progress in the fuel tank!`);
    } else {
      toast.info(`${notification.title} - Feature coming soon!`);
    }
  };

  const handleNotificationAction = (action: string, notificationId: string) => {
    switch (action) {
      case 'open_camera':
        navigateToScreen('camera');
        break;
      case 'confirm_symptoms':
        navigateToScreen('alert');
        break;
      case 'view_progress':
        toast.info("Check your weekly progress by tapping the fuel tank! 📊");
        break;
      case 'add_to_plan':
        toast.success("Added to your nutrition plan! 🌿");
        break;
      case 'dismiss':
        toast.info("Notification dismissed");
        break;
      case 'snooze':
        toast.info("We'll remind you later ⏰");
        break;
      default:
        toast.info("Action coming soon!");
    }
  };

  const handleChatWithKAI = (context: 'iron' | 'general' = 'general') => {
    setChatContext(context);
    setIsChatDrawerOpen(true);
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case 'home':
        return (
          <HomeScreen 
            onLogMeal={handleLogMeal}
            onMenuClick={handleMenuClick}
            onNotificationClick={handleNotificationClick}
            onProfileClick={handleProfileClick}
            onChatWithKAI={() => handleChatWithKAI('iron')}
            onSheetOpenChange={setIsDetailSheetOpen}
          />
        );
      case 'camera':
        return (
          <CameraScreen 
            onBack={() => navigateToScreen('home')}
            onCapture={handleCapture}
          />
        );
      case 'processing':
        return (
          <ProcessingScreen 
            onBack={() => navigateToScreen('camera')}
            onComplete={handleProcessingComplete}
            imageUrl={capturedImage}
          />
        );
      case 'result':
        return (
          <MealResultScreen 
            onBack={() => navigateToScreen('processing')}
            onConfirm={handleMealConfirm}
            onEdit={handleMealEdit}
            onAddSuggestion={handleAddSuggestion}
            onChatWithKAI={() => handleChatWithKAI('iron')}
            result={mealResult}
            imageUrl={capturedImage}
          />
        );
      case 'alert':
        return (
          <HealthAlertScreen 
            onBack={() => navigateToScreen('home')}
            onStartPlan={handleStartPlan}
          />
        );
      case 'micros':
        return (
          <MicrosOverviewScreen 
            onBack={() => navigateToScreen('home')}
            onNutrientTap={(nutrient) => {
              if (nutrient === 'Iron') {
                navigateToScreen('alert');
              } else {
                toast.info(`${nutrient} details coming soon!`);
              }
            }}
          />
        );
      case 'profile':
        return (
          <ProfileScreen 
            onBack={() => navigateToScreen('home')}
            onShare={handleShareProgress}
            onLogout={handleLogout}
          />
        );
      case 'notifications':
        return (
          <NotificationsScreen 
            onBack={() => navigateToScreen('home')}
            onNotificationTap={handleNotificationTap}
            onActionClick={handleNotificationAction}
          />
        );
      default:
        return (
          <HomeScreen 
            onLogMeal={handleLogMeal}
            onMenuClick={handleMenuClick}
            onNotificationClick={handleNotificationClick}
            onProfileClick={handleProfileClick}
            onChatWithKAI={() => handleChatWithKAI('iron')}
            onSheetOpenChange={setIsDetailSheetOpen}
          />
        );
    }
  };

  // Bottom action bar only shows on Home screen and when detail sheet is not open
  // Explicitly hidden on: camera, processing, chat, and all other screens
  const shouldShowActionBar = currentScreen === 'home' && !isDetailSheetOpen;

  return (
    <div className="dark min-h-screen bg-background max-w-md mx-auto relative overflow-hidden">
      {renderScreen()}
      {shouldShowActionBar && (
        <BottomActionBar 
          onChatClick={() => handleChatWithKAI('general')}
          onLogMealClick={handleLogMeal}
          onMicrosClick={() => navigateToScreen('micros')}
        />
      )}
      <MenuDrawer 
        isOpen={isMenuOpen}
        onClose={() => setIsMenuOpen(false)}
        onNavigate={navigateToScreen}
        currentScreen={currentScreen}
      />
      <ChatDrawer 
        isOpen={isChatDrawerOpen}
        onClose={() => setIsChatDrawerOpen(false)}
        initialContext={chatContext}
      />
      <Toaster position="top-center" />
    </div>
  );
}