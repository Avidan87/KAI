import { ArrowLeft, Edit, CheckCircle, Lightbulb, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";

interface MealResultScreenProps {
  onBack: () => void;
  onConfirm: () => void;
  onEdit: () => void;
  onAddSuggestion?: (suggestion: string) => void;
  onChatWithKAI?: () => void;
  result: {
    foodName: string;
    calories: number;
    confidence: number;
    nutrients: {
      protein: number;
      carbs: number;
      fat: number;
    };
    micronutrients?: {
      iron: number;
      calcium: number;
      vitaminA: number;
      zinc: number;
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
  onChatWithKAI, 
  result, 
  imageUrl, 
  mealType = "DINNER" 
}: MealResultScreenProps) {
  // Mock daily targets and current values for nutrients
  const dailyNutrients = {
    iron: { current: 6.8, target: 18, fromMeal: result.micronutrients?.iron || 2.3 },
    calcium: { current: 520, target: 1000, fromMeal: result.micronutrients?.calcium || 180 },
    vitaminA: { current: 450, target: 700, fromMeal: result.micronutrients?.vitaminA || 95 },
    zinc: { current: 7.2, target: 11, fromMeal: result.micronutrients?.zinc || 1.8 }
  };

  // Calculate percentages for each nutrient
  const getNutrientStatus = (current: number, target: number) => {
    const percentage = (current / target) * 100;
    if (percentage >= 80) return { status: 'good', color: 'bg-primary', textColor: 'text-primary' };
    if (percentage >= 50) return { status: 'warning', color: 'bg-yellow-500', textColor: 'text-yellow-500' };
    return { status: 'low', color: 'bg-destructive', textColor: 'text-destructive' };
  };

  // Detect critical deficiency (for inline insight card)
  const criticalDeficiency = Object.entries(dailyNutrients).find(([_, data]) => {
    const percentage = (data.current / data.target) * 100;
    return percentage < 50; // Critical if below 50%
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="text-[rgb(255,246,246)]">
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

        {/* Your Key Nutrients Section */}
        <Card className="p-5">
          <h3 className="font-semibold mb-4 text-[rgb(255,249,249)]">🔬 YOUR KEY NUTRIENTS</h3>
          <div className="space-y-4">
            {/* Iron */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🩸 Iron</span>
                  <Badge variant="outline" className="text-xs px-1.5 py-0">
                    +{dailyNutrients.iron.fromMeal}mg
                  </Badge>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-semibold ${getNutrientStatus(dailyNutrients.iron.current, dailyNutrients.iron.target).textColor}`}>
                    {dailyNutrients.iron.current}/{dailyNutrients.iron.target}mg
                  </span>
                  <span className="text-xs text-muted-foreground ml-1">
                    ({Math.round((dailyNutrients.iron.current / dailyNutrients.iron.target) * 100)}%)
                  </span>
                </div>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className={`h-full ${getNutrientStatus(dailyNutrients.iron.current, dailyNutrients.iron.target).color} transition-all duration-500`}
                  style={{ width: `${Math.min((dailyNutrients.iron.current / dailyNutrients.iron.target) * 100, 100)}%` }}
                />
              </div>
            </div>

            {/* Calcium */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🦴 Calcium</span>
                  <Badge variant="outline" className="text-xs px-1.5 py-0">
                    +{dailyNutrients.calcium.fromMeal}mg
                  </Badge>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-semibold ${getNutrientStatus(dailyNutrients.calcium.current, dailyNutrients.calcium.target).textColor}`}>
                    {dailyNutrients.calcium.current}/{dailyNutrients.calcium.target}mg
                  </span>
                  <span className="text-xs text-muted-foreground ml-1">
                    ({Math.round((dailyNutrients.calcium.current / dailyNutrients.calcium.target) * 100)}%)
                  </span>
                </div>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className={`h-full ${getNutrientStatus(dailyNutrients.calcium.current, dailyNutrients.calcium.target).color} transition-all duration-500`}
                  style={{ width: `${Math.min((dailyNutrients.calcium.current / dailyNutrients.calcium.target) * 100, 100)}%` }}
                />
              </div>
            </div>

            {/* Vitamin A */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">👁️ Vitamin A</span>
                  <Badge variant="outline" className="text-xs px-1.5 py-0">
                    +{dailyNutrients.vitaminA.fromMeal}mcg
                  </Badge>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-semibold ${getNutrientStatus(dailyNutrients.vitaminA.current, dailyNutrients.vitaminA.target).textColor}`}>
                    {dailyNutrients.vitaminA.current}/{dailyNutrients.vitaminA.target}mcg
                  </span>
                  <span className="text-xs text-muted-foreground ml-1">
                    ({Math.round((dailyNutrients.vitaminA.current / dailyNutrients.vitaminA.target) * 100)}%)
                  </span>
                </div>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className={`h-full ${getNutrientStatus(dailyNutrients.vitaminA.current, dailyNutrients.vitaminA.target).color} transition-all duration-500`}
                  style={{ width: `${Math.min((dailyNutrients.vitaminA.current / dailyNutrients.vitaminA.target) * 100, 100)}%` }}
                />
              </div>
            </div>

            {/* Zinc */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">⚡ Zinc</span>
                  <Badge variant="outline" className="text-xs px-1.5 py-0">
                    +{dailyNutrients.zinc.fromMeal}mg
                  </Badge>
                </div>
                <div className="text-right">
                  <span className={`text-sm font-semibold ${getNutrientStatus(dailyNutrients.zinc.current, dailyNutrients.zinc.target).textColor}`}>
                    {dailyNutrients.zinc.current}/{dailyNutrients.zinc.target}mg
                  </span>
                  <span className="text-xs text-muted-foreground ml-1">
                    ({Math.round((dailyNutrients.zinc.current / dailyNutrients.zinc.target) * 100)}%)
                  </span>
                </div>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className={`h-full ${getNutrientStatus(dailyNutrients.zinc.current, dailyNutrients.zinc.target).color} transition-all duration-500`}
                  style={{ width: `${Math.min((dailyNutrients.zinc.current / dailyNutrients.zinc.target) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Nutrition Insight Card - Only shows when deficiency detected */}
        {criticalDeficiency && (
          <Card className="p-4 bg-amber-500/10 border-amber-500/30">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h4 className="font-semibold text-amber-500 mb-1">
                  ⚠️ {criticalDeficiency[0].charAt(0).toUpperCase() + criticalDeficiency[0].slice(1)} Deficiency Alert
                </h4>
                <p className="text-sm text-[rgb(255,250,250)] mb-2">
                  Your {criticalDeficiency[0]} is at {Math.round((criticalDeficiency[1].current / criticalDeficiency[1].target) * 100)}% of daily target. 
                  This may be causing fatigue and low energy.
                </p>
                <div className="bg-amber-500/10 rounded-lg p-3 mb-3">
                  <p className="text-xs text-[rgb(255,252,252)] mb-2">
                    <span className="font-semibold">Quick Fix:</span> Add these to your next meal:
                  </p>
                  <div className="space-y-1">
                    {criticalDeficiency[0] === 'iron' && (
                      <>
                        <p className="text-xs text-[rgb(254,251,251)]">• Ugwu (pumpkin leaves) → +4.5mg</p>
                        <p className="text-xs text-[rgb(254,251,251)]">• Moi moi (2 wraps) → +3.5mg</p>
                        <p className="text-xs text-[rgb(254,251,251)]">• Groundnuts (handful) → +1.3mg</p>
                      </>
                    )}
                    {criticalDeficiency[0] === 'calcium' && (
                      <>
                        <p className="text-xs text-[rgb(254,251,251)]">• Crayfish (2 tbsp) → +240mg</p>
                        <p className="text-xs text-[rgb(254,251,251)]">• Ewedu soup → +180mg</p>
                        <p className="text-xs text-[rgb(254,251,251)]">• Kuli kuli → +120mg</p>
                      </>
                    )}
                  </div>
                </div>
                <Button 
                  onClick={onChatWithKAI}
                  size="sm"
                  variant="outline"
                  className="w-full border-amber-500/50 text-amber-500 hover:bg-amber-500/20"
                >
                  💬 Chat with KAI for personalized plan
                </Button>
              </div>
            </div>
          </Card>
        )}

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