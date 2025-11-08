import { Bell, Menu, User, Lightbulb, ChevronRight, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Separator } from "./ui/separator";
import { ProgressBar } from "./ProgressBar";
import { VerticalProgressBar } from "./VerticalProgressBar";
import { HexagonProgress } from "./HexagonProgress";
import { CriticalAlert } from "./CriticalAlert";
import { MealCard } from "./MealCard";
import { useState } from "react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";

interface HomeScreenProps {
  onLogMeal: () => void;
  onMenuClick: () => void;
  onNotificationClick: () => void;
  onProfileClick: () => void;
  onChatWithKAI: () => void;
  onSheetOpenChange?: (isOpen: boolean) => void;
}

export function HomeScreen({ onLogMeal, onMenuClick, onNotificationClick, onProfileClick, onChatWithKAI, onSheetOpenChange }: HomeScreenProps) {
  const [isFuelExpanded, setIsFuelExpanded] = useState(false);
  const [isMacrosExpanded, setIsMacrosExpanded] = useState(false);
  
  const today = new Date();
  const dayName = today.toLocaleDateString('en-US', { weekday: 'long' });
  const dateString = today.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });

  // Sample data - in real app this would come from state/API
  const dailyData = {
    calories: { current: 1370, target: 1900, percentage: 72 },
    macros: [
      { label: 'PRO', current: 42, target: 50, unit: 'g', status: 'good' as const },
      { label: 'CARB', current: 205, target: 250, unit: 'g', status: 'good' as const },
      { label: 'FAT', current: 43, target: 65, unit: 'g', status: 'warning' as const },
    ],
    criticalNutrients: [
      { nutrient: 'Iron', days: 14 }
    ]
  };

  const todaysMeals = [
    {
      id: 1,
      mealType: "🌅 Breakfast",
      time: "7:30 AM",
      foodName: "Akara + Pap",
      calories: 380,
      imageUrl: "https://images.unsplash.com/photo-1741026079488-f22297dc3036?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxuaWdlcmlhbiUyMGZvb2QlMjBha2FyYSUyMGJlYW5zfGVufDF8fHx8MTc1OTg1NjMzNnww&ixlib=rb-4.1.0&q=80&w=1080"
    },
    {
      id: 2,
      mealType: "🌞 Lunch", 
      time: "1:15 PM",
      foodName: "Jollof Rice + Chicken",
      calories: 650,
      imageUrl: "https://images.unsplash.com/photo-1653981608672-aea09b857b20?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxqb2xsb2YlMjByaWNlJTIwYWZyaWNhbiUyMGRpc2h8ZW58MXx8fHwxNzU5ODU2MzM5fDA&ixlib=rb-4.1.0&q=80&w=1080"
    }
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 pb-6">
        <Button variant="ghost" size="icon" onClick={onMenuClick} className="text-[rgb(239,228,228)]">
          <Menu className="w-6 h-6" />
        </Button>
        <h1 className="text-xl font-semibold text-primary">KAI</h1>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="relative text-[rgb(248,231,231)]" onClick={onNotificationClick}>
            <Bell className="w-6 h-6" />
            <div className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center text-xs">
              1
            </div>
          </Button>
          <Button variant="ghost" size="icon" onClick={onProfileClick} className="text-[rgb(253,237,237)]">
            <User className="w-6 h-6" />
          </Button>
        </div>
      </div>

      <div className="px-4 space-y-6">
        {/* Greeting */}
        <div>
          <h2 className="text-2xl font-semibold text-[rgb(244,230,230)]">Good morning, Adaeze! 👋</h2>
          <p className="text-muted-foreground">{dayName}, {dateString}</p>
        </div>

        {/* Critical Nutrient Alerts - MOVED TO TOP PRIORITY */}
        {dailyData.criticalNutrients.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-destructive">⚠️ PRIORITY ALERTS</span>
            </div>
            {dailyData.criticalNutrients.map((alert, index) => (
              <CriticalAlert
                key={index}
                nutrient={alert.nutrient}
                days={alert.days}
                onTap={onChatWithKAI}
              />
            ))}
          </div>
        )}

        {/* Collapsible Fuel Tank */}
        <Collapsible open={isFuelExpanded} onOpenChange={setIsFuelExpanded}>
          <div className="border border-border rounded-lg overflow-hidden">
            <CollapsibleTrigger className="w-full p-4 bg-card hover:bg-muted/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg">⛽</span>
                  <div className="text-left">
                    <h3 className="font-semibold text-[rgb(255,247,247)]">Daily Fuel</h3>
                    <p className="text-sm text-muted-foreground">
                      {dailyData.calories.current}/{dailyData.calories.target} kcal ({dailyData.calories.percentage}%)
                    </p>
                  </div>
                </div>
                {isFuelExpanded ? (
                  <ChevronUp className="w-5 h-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-muted-foreground" />
                )}
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="p-4 pt-0">
                <VerticalProgressBar 
                  current={dailyData.calories.current}
                  target={dailyData.calories.target}
                  percentage={dailyData.calories.percentage}
                  onOpenChange={onSheetOpenChange}
                />
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>

        {/* Collapsible Macros */}
        <Collapsible open={isMacrosExpanded} onOpenChange={setIsMacrosExpanded}>
          <div className="border border-border rounded-lg overflow-hidden">
            <CollapsibleTrigger className="w-full p-4 bg-card hover:bg-muted/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg">🎯</span>
                  <div className="text-left">
                    <h3 className="font-semibold text-[rgb(255,247,247)]">Today's Macros</h3>
                    <p className="text-sm text-muted-foreground">
                      Protein • Carbs • Fat
                    </p>
                  </div>
                </div>
                {isMacrosExpanded ? (
                  <ChevronUp className="w-5 h-5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-muted-foreground" />
                )}
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="p-4 pt-0">
                <div className="flex items-center gap-3 mb-4">
                  <Separator className="flex-1" />
                  <span className="text-sm font-medium text-muted-foreground">MACROS</span>
                  <Separator className="flex-1" />
                </div>

                {/* Hexagon Grid - 3 in a row */}
                <div className="flex justify-center gap-3 px-2 sm:gap-4 sm:px-4">
                  {dailyData.macros.map((macro, index) => (
                    <HexagonProgress
                      key={macro.label}
                      label={macro.label === 'PRO' ? 'PROTEIN' : macro.label === 'CARB' ? 'CARBS' : macro.label}
                      current={macro.current}
                      target={macro.target}
                      unit={macro.unit}
                      percentage={macro.percentage}
                      status={macro.status}
                      delay={index * 0.1}
                      sources={[
                        { meal: "🌅 Breakfast", amount: Math.floor(macro.current * 0.3), time: "7:30 AM" },
                        { meal: "🍽️ Lunch", amount: Math.floor(macro.current * 0.5), time: "1:15 PM" },
                        { meal: "🌙 Dinner", amount: macro.current - Math.floor(macro.current * 0.3) - Math.floor(macro.current * 0.5), time: "7:00 PM" }
                      ].filter(source => source.amount > 0)}
                      education={
                        macro.label === 'PRO' 
                          ? "Protein helps build muscle, repair tissue, and keeps you full longer. Essential for recovery and growth." 
                          : macro.label === 'CARB'
                          ? "Carbs provide energy for your brain and muscles throughout the day. Choose complex carbs for sustained energy."
                          : "Healthy fats support hormone production, brain function, and help absorb vitamins A, D, E, and K."
                      }
                      tip={
                        macro.label === 'PRO' 
                          ? "Add fish, beans, or eggs to your next meal for complete protein 🐟" 
                          : macro.label === 'CARB'
                          ? "Choose brown rice, yam, or plantain for sustained energy 🍠"
                          : "Use palm oil in moderation - try grilled over fried foods 🔥"
                      }
                      onOpenChange={onSheetOpenChange}
                    />
                  ))}
                </div>

                {/* Tap hint */}
                <p className="text-center text-xs text-muted-foreground mt-4">
                  Tap macros to see more details
                </p>
              </div>
            </CollapsibleContent>
          </div>
        </Collapsible>

        {/* Today's Meals */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-[rgb(244,233,233)]">──── TODAY'S MEALS ────</h3>
          <div className="space-y-3">
            {todaysMeals.map((meal) => (
              <MealCard
                key={meal.id}
                mealType={meal.mealType}
                time={meal.time}
                foodName={meal.foodName}
                calories={meal.calories}
                imageUrl={meal.imageUrl}
                onClick={() => {/* Navigate to meal details */}}
              />
            ))}
          </div>
        </div>

        {/* Health Tip */}
        <Card className="p-4 bg-accent/10 border-accent/20">
          <div className="flex items-start gap-3">
            <Lightbulb className="w-5 h-5 text-accent mt-1 flex-shrink-0" />
            <div>
              <p className="text-sm">
                <span className="font-semibold">Tip:</span> Add ugwu to dinner for extra iron! 🌿
              </p>
            </div>
          </div>
        </Card>

        {/* Bottom spacing for action bar */}
        <div className="h-24"></div>
      </div>
    </div>
  );
}