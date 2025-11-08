import { ArrowLeft, Camera, Image, Lightbulb } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { useState } from "react";

interface CameraScreenProps {
  onBack: () => void;
  onCapture: (imageUrl: string) => void;
}

export function CameraScreen({ onBack, onCapture }: CameraScreenProps) {
  const [isCapturing, setIsCapturing] = useState(false);

  const handleCapture = () => {
    setIsCapturing(true);
    // Simulate camera capture with a random food image
    const sampleImages = [
      "https://images.unsplash.com/photo-1741026079488-f22297dc3036?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxuaWdlcmlhbiUyMGZvb2QlMjBha2FyYSUyMGJlYW5zfGVufDF8fHx8MTc1OTg1NjMzNnww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral",
      "https://images.unsplash.com/photo-1653981608672-aea09b857b20?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxqb2xsb2YlMjByaWNlJTIwYWZyaWNhbiUyMGRpc2h8ZW58MXx8fHwxNzU5ODU2MzM5fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
    ];
    
    setTimeout(() => {
      const randomImage = sampleImages[Math.floor(Math.random() * sampleImages.length)];
      onCapture(randomImage);
      setIsCapturing(false);
    }, 1000);
  };

  const handleGallery = () => {
    // Simulate selecting from gallery
    onCapture("https://images.unsplash.com/photo-1741026079488-f22297dc3036?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxuaWdlcmlhbiUyMGZvb2QlMjBha2FyYSUyMGJlYW5zfGVufDF8fHx8MTc1OTg1NjMzNnww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral");
  };

  return (
    <div className="min-h-screen bg-black relative">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-4 text-white">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={onBack}
          className="text-white hover:bg-white/20"
        >
          <ArrowLeft className="w-6 h-6" />
        </Button>
        <h1 className="text-lg font-semibold">SNAP MEAL</h1>
        <div className="w-10"></div>
      </div>

      {/* Camera Viewfinder */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-80 h-80 border-2 border-white/50 rounded-2xl relative overflow-hidden">
          {/* Mock camera view */}
          <div className="w-full h-full bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
            <div className="text-white/60 text-center">
              <Camera className="w-16 h-16 mx-auto mb-2" />
              <p className="text-sm">Camera View</p>
            </div>
          </div>
          
          {/* Corner indicators */}
          <div className="absolute top-2 left-2 w-6 h-6 border-l-2 border-t-2 border-white/70"></div>
          <div className="absolute top-2 right-2 w-6 h-6 border-r-2 border-t-2 border-white/70"></div>
          <div className="absolute bottom-2 left-2 w-6 h-6 border-l-2 border-b-2 border-white/70"></div>
          <div className="absolute bottom-2 right-2 w-6 h-6 border-r-2 border-b-2 border-white/70"></div>
        </div>
      </div>

      {/* Tip */}
      <div className="absolute bottom-32 left-4 right-4">
        <Card className="p-3 bg-black/70 border-white/20 backdrop-blur-sm">
          <div className="flex items-center gap-2 text-white">
            <Lightbulb className="w-4 h-4 text-accent" />
            <p className="text-sm">Tip: Include full plate for best accuracy</p>
          </div>
        </Card>
      </div>

      {/* Controls */}
      <div className="absolute bottom-8 left-0 right-0 flex items-center justify-center gap-8">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={handleGallery}
          className="text-white hover:bg-white/20 w-12 h-12"
        >
          <Image className="w-6 h-6" />
        </Button>
        
        <Button 
          size="icon" 
          onClick={handleCapture}
          disabled={isCapturing}
          className="w-16 h-16 rounded-full bg-white hover:bg-white/90 text-black"
        >
          {isCapturing ? (
            <div className="w-4 h-4 bg-primary rounded-full animate-pulse" />
          ) : (
            <div className="w-4 h-4 bg-black rounded-full" />
          )}
        </Button>
        
        <Button 
          variant="ghost" 
          size="icon" 
          className="text-white hover:bg-white/20 w-12 h-12"
        >
          <Lightbulb className="w-6 h-6" />
        </Button>
      </div>
    </div>
  );
}