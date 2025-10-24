import { ArrowLeft, AlertTriangle, Lightbulb, MapPin, Clock } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";

interface HealthAlertScreenProps {
  onBack: () => void;
  onStartPlan: () => void;
}

export function HealthAlertScreen({ onBack, onStartPlan }: HealthAlertScreenProps) {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="w-6 h-6" />
        </Button>
        <h1 className="text-lg font-semibold">YOUR IRON BOOST PLAN</h1>
        <div className="w-10"></div>
      </div>

      <div className="px-4 py-4 space-y-6">
        {/* Alert Message */}
        <Card className="p-4 bg-destructive/5 border-destructive/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-destructive mt-1 flex-shrink-0" />
            <div>
              <h3 className="font-semibold text-destructive mb-2">That explains it! 💡</h3>
              <p className="text-sm">
                Your tiredness is likely from low iron. Good news: we can fix this with food you know!
              </p>
            </div>
          </div>
        </Card>

        {/* Weekly Plan */}
        <div>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            🍽️ ADD THESE THIS WEEK:
          </h3>

          <div className="space-y-4">
            {/* Breakfast */}
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">BREAKFAST</Badge>
                  </div>
                  <h4 className="font-semibold">Moi moi (2 wraps)</h4>
                  <p className="text-sm text-primary">→ +3.5mg iron 🫘</p>
                </div>
              </div>
            </Card>

            {/* Lunch */}
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">LUNCH</Badge>
                  </div>
                  <h4 className="font-semibold">Ask for extra ugwu in your soup</h4>
                  <p className="text-sm text-primary">→ +4.5mg iron 🌿</p>
                </div>
              </div>
            </Card>

            {/* Snack */}
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 bg-primary rounded-full mt-2"></div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">SNACK</Badge>
                  </div>
                  <h4 className="font-semibold">Groundnuts instead of biscuits</h4>
                  <p className="text-sm text-primary">→ +1.3mg iron 🥜</p>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Pro Tip */}
        <Card className="p-4 bg-accent/10 border-accent/20">
          <div className="flex items-start gap-3">
            <Lightbulb className="w-5 h-5 text-accent mt-1 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-accent mb-1">PRO TIP</h4>
              <p className="text-sm">
                Eat orange after meals (Vitamin C boosts iron absorption 3x!) 🍊
              </p>
            </div>
          </div>
        </Card>

        {/* Where to Get */}
        <Card className="p-4">
          <div className="flex items-start gap-3">
            <MapPin className="w-5 h-5 text-muted-foreground mt-1 flex-shrink-0" />
            <div>
              <h4 className="font-semibold mb-2">Where to get:</h4>
              <ul className="text-sm space-y-1">
                <li>• Any buka near you</li>
                <li>• Balogun/Oshodi market</li>
              </ul>
            </div>
          </div>
        </Card>

        {/* Budget */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">💰 Budget:</span>
          <span className="font-semibold">₦500-800/day</span>
        </div>

        {/* Timeline */}
        <Card className="p-4 bg-secondary/10 border-secondary/20">
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-secondary mt-1 flex-shrink-0" />
            <div>
              <p className="text-sm">
                ⏱️ You should feel better in <span className="font-semibold">7-10 days</span>. I'll track it!
              </p>
            </div>
          </div>
        </Card>

        {/* Start Plan Button */}
        <Button 
          onClick={onStartPlan}
          className="w-full h-12 bg-primary hover:bg-primary/90"
          size="lg"
        >
          Start This Plan
        </Button>

        {/* Bottom spacing */}
        <div className="h-8"></div>
      </div>
    </div>
  );
}