import { Camera, Utensils } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { MicrosIcon } from "./MicrosIcon";

interface MicrosEmptyStateProps {
  onLogMeal: () => void;
}

export function MicrosEmptyState({ onLogMeal }: MicrosEmptyStateProps) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <Card className="p-8 max-w-sm w-full text-center">
        <div className="space-y-6">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="relative">
              <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center">
                <MicrosIcon className="w-10 h-10 text-primary" />
              </div>
              {/* Floating food icons */}
              <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
                <Utensils className="w-4 h-4 text-accent" />
              </div>
            </div>
          </div>

          {/* Heading */}
          <div>
            <h3 className="font-semibold text-foreground mb-2">
              No Micronutrient Data Yet
            </h3>
            <p className="text-sm text-muted-foreground">
              Log your first meal to see your top 5 vitamins and minerals tracked across Nigerian foods
            </p>
          </div>

          {/* Benefits list */}
          <div className="space-y-2 text-left bg-muted/20 rounded-lg p-4">
            <p className="text-xs font-semibold text-foreground mb-2">
              What you'll track:
            </p>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#D64545' }} />
                <span className="text-muted-foreground">Iron for energy & focus</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#4C86E8' }} />
                <span className="text-muted-foreground">Calcium for strong bones</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#F5A524' }} />
                <span className="text-muted-foreground">Vitamin D for immunity</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#2FB7A1' }} />
                <span className="text-muted-foreground">Magnesium for muscles</span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: '#7A8CA8' }} />
                <span className="text-muted-foreground">Zinc for immune health</span>
              </div>
            </div>
          </div>

          {/* CTA */}
          <Button 
            onClick={onLogMeal}
            className="w-full"
            size="lg"
          >
            <Camera className="w-5 h-5 mr-2" />
            Log Your First Meal
          </Button>

          {/* Hint */}
          <p className="text-xs text-muted-foreground">
            💡 KAI recognizes jollof, egusi, ugwu, and 100+ Nigerian foods
          </p>
        </div>
      </Card>
    </div>
  );
}
