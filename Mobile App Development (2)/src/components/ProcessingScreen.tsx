import { ArrowLeft, CheckCircle } from "lucide-react";
import { Button } from "./ui/button";
import { ProgressBar } from "./ProgressBar";
import { useEffect, useState } from "react";

interface ProcessingScreenProps {
  onBack: () => void;
  onComplete: (result: any) => void;
  imageUrl: string;
}

export function ProcessingScreen({ onBack, onComplete, imageUrl }: ProcessingScreenProps) {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [detectedItems, setDetectedItems] = useState<string[]>([]);
  
  const steps = [
    "Detecting food items...",
    "Estimating portions...", 
    "Calculating nutrition..."
  ];

  // Dynamic detected food items that appear progressively
  const foodDetections = [
    { step: 0, message: "Found: Egusi soup 🍲", delay: 800 },
    { step: 0, message: "Found: Pounded yam 🥘", delay: 1500 },
    { step: 1, message: "Portion: ~2 cups soup", delay: 2800 },
    { step: 1, message: "Portion: ~1 medium ball yam", delay: 3500 },
    { step: 2, message: "Analyzing nutrients...", delay: 5000 }
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev + 2;
        
        if (newProgress >= 33 && currentStep === 0) {
          setCurrentStep(1);
        } else if (newProgress >= 66 && currentStep === 1) {
          setCurrentStep(2);
        } else if (newProgress >= 100) {
          clearInterval(timer);
          setTimeout(() => {
            // Mock food recognition result
            const mockResult = {
              foodName: "Egusi Soup + Pounded Yam",
              calories: 520,
              confidence: 87,
              nutrients: {
                protein: 22,
                carbs: 68,
                fat: 18
              },
              description: "Traditional Nigerian soup with vegetables and meat, served with pounded yam"
            };
            onComplete(mockResult);
          }, 500);
        }
        
        return Math.min(newProgress, 100);
      });
    }, 100);

    return () => clearInterval(timer);
  }, [currentStep, onComplete]);

  // Progressive food detection messages
  useEffect(() => {
    foodDetections.forEach((detection) => {
      setTimeout(() => {
        if (currentStep >= detection.step) {
          setDetectedItems(prev => [...prev, detection.message]);
        }
      }, detection.delay);
    });
  }, [currentStep]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="w-6 h-6" />
        </Button>
        <h1 className="text-lg font-semibold">ANALYZING</h1>
        <div className="w-10"></div>
      </div>

      <div className="px-4 py-8 space-y-8">
        {/* Food Image */}
        <div className="flex justify-center">
          <div className="w-64 h-64 rounded-2xl overflow-hidden">
            <img 
              src={imageUrl} 
              alt="Captured meal" 
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        {/* Processing Status */}
        <div className="text-center space-y-4">
          <h2 className="text-xl font-semibold">Analyzing your meal...</h2>
          
          <div className="space-y-2">
            <ProgressBar percentage={progress} color="primary" height="lg" />
            <p className="text-sm text-muted-foreground">{Math.round(progress)}%</p>
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {steps.map((step, index) => (
            <div key={index} className="flex items-center gap-3">
              {index < currentStep ? (
                <CheckCircle className="w-5 h-5 text-primary" />
              ) : index === currentStep ? (
                <div className="w-5 h-5 border-2 border-primary rounded-full border-t-transparent animate-spin" />
              ) : (
                <div className="w-5 h-5 border-2 border-muted rounded-full" />
              )}
              <span className={index <= currentStep ? "text-foreground" : "text-muted-foreground"}>
                {step}
              </span>
            </div>
          ))}
        </div>

        {/* Dynamic Detection Messages */}
        {detectedItems.length > 0 && (
          <div className="bg-primary/10 p-4 rounded-lg space-y-2">
            <p className="text-xs font-semibold text-primary mb-2">🔍 Detected:</p>
            {detectedItems.map((item, index) => (
              <div 
                key={index}
                className="text-sm text-[rgb(255,250,250)] pl-3 border-l-2 border-primary/40 animate-in fade-in slide-in-from-left-2"
              >
                {item}
              </div>
            ))}
          </div>
        )}

        {/* Fun fact while waiting */}
        <div className="bg-muted/50 p-4 rounded-lg">
          <p className="text-sm text-center text-muted-foreground">
            💡 Did you know? Nigerian meals are naturally rich in plant proteins from beans and legumes!
          </p>
        </div>
      </div>
    </div>
  );
}