import { ArrowLeft, Edit, CheckCircle, Lightbulb } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";

interface MealResultScreenProps {
  onBack: () => void;
  onConfirm: () => void;
  onEdit: () => void;
  onAddSuggestion?: (suggestion: string) => void;
  result: {
    foodName: string;
    calories: number;
    confidence: number;
    nutrients: {
      protein: number;
      carbs: number;
      fat: number;
    };
    description: string;
  };
  imageUrl: string;
  mealType?: string;
}

export function MealResultScreen({ 
  onBack, 
  onConfirm, 
  onEdit,
  onAddSuggestion, 
  result, 
  imageUrl, 
  mealType = "DINNER" 
}: MealResultScreenProps) {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="w-6 h-6" />
        </Button>
        <h1 className="text-lg font-semibold text-[rgb(251,244,244)]">{mealType} LOGGED</h1>
        <div className="w-10"></div>
      </div>

      <div className="px-4 py-4 space-y-6">
        {/* Food Image */}
        <div className="flex justify-center">
          <div className="w-64 h-64 rounded-2xl overflow-hidden">
            <img 
              src={imageUrl} 
              alt={result.foodName} 
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        {/* Food Name */}
        <div className="text-center">
          <h2 className="text-xl font-semibold flex items-center justify-center gap-2 text-[rgb(249,242,242)]">
            🥘 {result.foodName}
          </h2>
        </div>

        {/* Nutrition Summary */}
        <Card className="p-6">
          <div className="text-center mb-4">
            <div className="text-3xl font-bold text-primary">{result.calories} kcal</div>
          </div>
          
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center">
              <div className="font-semibold">Protein</div>
              <div className="text-2xl text-primary">{result.nutrients.protein}g</div>
            </div>
            <div className="text-center">
              <div className="font-semibold">Carbs</div>
              <div className="text-2xl text-secondary">{result.nutrients.carbs}g</div>
            </div>
            <div className="text-center">
              <div className="font-semibold">Fat</div>
              <div className="text-2xl text-accent">{result.nutrients.fat}g</div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-2">
            <span className="text-sm text-muted-foreground">Confidence:</span>
            <Badge variant={result.confidence >= 80 ? "default" : "secondary"}>
              {result.confidence}%
            </Badge>
          </div>
        </Card>

        {/* Confirmation Question */}
        <div className="text-center">
          <p className="text-lg mb-4 text-[rgb(255,250,250)]">Does this look right?</p>
          
          <div className="flex gap-3">
            <Button 
              onClick={onConfirm}
              className="flex-1 bg-primary hover:bg-primary/90"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Looks Good
            </Button>
            <Button 
              onClick={onEdit}
              variant="outline"
              className="flex-1"
            >
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </Button>
          </div>
        </div>

        {/* Quick tip */}
        <Card className="p-4 bg-primary/5 border-primary/20">
          <div className="flex items-start gap-3">
            <Lightbulb className="w-5 h-5 text-primary mt-1 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm mb-3">
                <span className="font-semibold text-primary">Quick tip</span>
                <br />
                Add ugwu to lunch soup for +4.5mg iron
              </p>
              {onAddSuggestion && (
                <Button 
                  onClick={() => onAddSuggestion('ugwu')}
                  className="bg-primary hover:bg-primary/90 h-9"
                  size="sm"
                >
                  Add ugwu
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* Bottom spacing */}
        <div className="h-8"></div>
      </div>
    </div>
  );
}