import { ArrowLeft, ChevronRight, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";

interface MicrosOverviewScreenProps {
  onBack: () => void;
  onNutrientTap?: (nutrient: string) => void;
}

export function MicrosOverviewScreen({ 
  onBack, 
  onNutrientTap 
}: MicrosOverviewScreenProps) {
  // Sample data for top 5 micronutrients
  const topMicros = [
    {
      name: 'Iron',
      current: 8,
      target: 18,
      unit: 'mg',
      percentage: 44,
      color: '#D64545',
      trend: 'down',
      status: 'critical',
      daysLow: 14,
      impact: 'May cause fatigue, weakness',
      foods: ['Ugwu (fluted pumpkin)', 'Red meat', 'Beans']
    },
    {
      name: 'Calcium',
      current: 850,
      target: 1000,
      unit: 'mg',
      percentage: 85,
      color: '#4C86E8',
      trend: 'up',
      status: 'good',
      daysLow: 0,
      impact: 'Supports bone health',
      foods: ['Milk', 'Yogurt', 'Sardines']
    },
    {
      name: 'Vitamin D',
      current: 12,
      target: 15,
      unit: 'μg',
      percentage: 80,
      color: '#F5A524',
      trend: 'stable',
      status: 'good',
      daysLow: 0,
      impact: 'Helps calcium absorption',
      foods: ['Eggs', 'Titus fish', 'Fortified milk']
    },
    {
      name: 'Magnesium',
      current: 280,
      target: 320,
      unit: 'mg',
      percentage: 88,
      color: '#2FB7A1',
      trend: 'up',
      status: 'excellent',
      daysLow: 0,
      impact: 'Supports muscle function',
      foods: ['Beans', 'Groundnuts', 'Dark leafy greens']
    },
    {
      name: 'Zinc',
      current: 7,
      target: 8,
      unit: 'mg',
      percentage: 88,
      color: '#7A8CA8',
      trend: 'stable',
      status: 'good',
      daysLow: 0,
      impact: 'Boosts immune system',
      foods: ['Meat', 'Shellfish', 'Cashews']
    }
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'critical':
        return <Badge variant="destructive" className="text-xs">Critical</Badge>;
      case 'warning':
        return <Badge variant="outline" className="text-xs border-yellow-500 text-yellow-500">Low</Badge>;
      case 'good':
        return <Badge variant="outline" className="text-xs border-green-500 text-green-500">Good</Badge>;
      case 'excellent':
        return <Badge variant="outline" className="text-xs border-primary text-primary">Excellent</Badge>;
      default:
        return null;
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack} className="text-[rgb(249,239,239)]">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="font-semibold text-foreground">Top 5 Micronutrients</h1>
            <p className="text-xs text-muted-foreground">Your vitamin & mineral snapshot</p>
          </div>
        </div>
      </div>

      <div className="px-4 pt-6 pb-8 space-y-4">
        {/* Overview Card */}
        <Card className="p-4 bg-primary/5 border-primary/20">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-foreground mb-1">Track Your Essential Nutrients</h3>
              <p className="text-sm text-muted-foreground">
                These 5 micronutrients are crucial for your health. Keep them balanced with Nigerian foods you love.
              </p>
            </div>
          </div>
        </Card>

        {/* Micronutrient Cards */}
        {topMicros.map((micro, index) => (
          <Card 
            key={micro.name}
            className="p-4 cursor-pointer hover:border-primary/40 transition-colors"
            onClick={() => onNutrientTap?.(micro.name)}
          >
            <div className="space-y-3">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {/* Color indicator dot */}
                  <div 
                    className="w-3 h-3 rounded-full flex-shrink-0 mt-1"
                    style={{ backgroundColor: micro.color }}
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground">{micro.name}</h3>
                      {getTrendIcon(micro.trend)}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {micro.current} / {micro.target} {micro.unit}
                    </p>
                  </div>
                </div>
                {getStatusBadge(micro.status)}
              </div>

              {/* Progress bar */}
              <div className="space-y-1">
                <Progress 
                  value={micro.percentage} 
                  className="h-2"
                  style={{
                    ['--progress-color' as any]: micro.color
                  }}
                />
                <p className="text-xs text-muted-foreground text-right">
                  {micro.percentage}% of daily target
                </p>
              </div>

              {/* Alert for critical nutrients */}
              {micro.status === 'critical' && micro.daysLow > 0 && (
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-2">
                  <p className="text-xs text-destructive-foreground">
                    ⚠️ Low for {micro.daysLow} days • {micro.impact}
                  </p>
                </div>
              )}

              {/* Food suggestions */}
              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground mb-2">
                  🥗 Rich in {micro.name}:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {micro.foods.map((food, i) => (
                    <Badge 
                      key={i} 
                      variant="outline" 
                      className="text-xs"
                      style={{
                        borderColor: `${micro.color}40`,
                        color: micro.color
                      }}
                    >
                      {food}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Tap to learn more */}
              <div className="flex items-center justify-between pt-1">
                <p className="text-xs text-muted-foreground">{micro.impact}</p>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </div>
            </div>
          </Card>
        ))}

        {/* Info footer */}
        <Card className="p-4 bg-accent/5 border-accent/20">
          <p className="text-xs text-muted-foreground text-center">
            💡 KAI tracks these nutrients across all your meals and alerts you when levels stay low for 10+ days
          </p>
        </Card>
      </div>
    </div>
  );
}
