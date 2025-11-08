import { Clock } from "lucide-react";
import { Card } from "./ui/card";
import { ImageWithFallback } from "./figma/ImageWithFallback";

interface MealCardProps {
  mealType: string;
  time: string;
  foodName: string;
  calories: number;
  imageUrl?: string;
  onClick?: () => void;
}

export function MealCard({ mealType, time, foodName, calories, imageUrl, onClick }: MealCardProps) {
  return (
    <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={onClick}>
      <div className="flex items-center gap-3">
        <div className="w-16 h-16 bg-muted rounded-lg flex items-center justify-center overflow-hidden">
          {imageUrl ? (
            <ImageWithFallback 
              src={imageUrl} 
              alt={foodName} 
              className="w-full h-full object-cover"
              fallback={<div className="text-2xl">🍽️</div>}
            />
          ) : (
            <div className="text-2xl">🍽️</div>
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm text-muted-foreground">{mealType}</span>
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {time}
            </span>
          </div>
          <h3 className="font-medium">{foodName}</h3>
          <p className="text-sm text-muted-foreground">{calories} kcal</p>
        </div>
      </div>
    </Card>
  );
}