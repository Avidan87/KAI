import { ArrowLeft, Edit, Share, LogOut, ChevronRight, Download, Trash2 } from "lucide-react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";

interface ProfileScreenProps {
  onBack: () => void;
  onShare: () => void;
  onLogout: () => void;
}

export function ProfileScreen({ onBack, onShare, onLogout }: ProfileScreenProps) {
  const profileData = {
    name: "Adaeze Okafor",
    location: "Lagos, Nigeria",
    streak: 7,
    avatar: "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150&h=150&fit=crop&crop=face",
    goals: {
      calories: 1900,
      protein: 50,
      focusNutrient: "Iron"
    },
    personal: {
      age: 28,
      sex: "Female",
      activity: "Moderately Active",
      dietary: ["Halal", "No shellfish"]
    },
    preferences: {
      language: "English",
      units: "Metric",
      location: "Nigeria"
    },
    healthFocus: [
      { nutrient: "Iron", status: "improving", icon: "✅" },
      { nutrient: "Calcium", status: "low", icon: "⚠️" },
      { nutrient: "Magnesium", status: "good", icon: "✅" }
    ]
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 pb-6">
        <Button variant="ghost" size="icon" onClick={onBack} className="text-[rgb(254,237,237)]">
          <ArrowLeft className="w-6 h-6" />
        </Button>
        <h1 className="text-xl font-semibold text-[rgb(255,240,240)]">Profile</h1>
        <Button variant="ghost" size="icon" className="text-[rgb(247,230,230)]">
          <Edit className="w-6 h-6" />
        </Button>
      </div>

      <div className="px-4 space-y-6">
        {/* Profile Header */}
        <div className="text-center space-y-4">
          <div className="relative inline-block">
            <Avatar className="w-24 h-24">
              <AvatarImage src={profileData.avatar} alt={profileData.name} />
              <AvatarFallback className="text-2xl">AO</AvatarFallback>
            </Avatar>
            <Button 
              size="sm" 
              className="absolute -bottom-2 -right-2 h-8 w-8 rounded-full p-0"
              variant="secondary"
            >
              <Edit className="w-4 h-4" />
            </Button>
          </div>
          
          <div>
            <h2 className="text-2xl font-semibold text-[rgb(206,201,201)]">{profileData.name}</h2>
            <p className="text-muted-foreground">{profileData.location}</p>
            <p className="text-sm text-muted-foreground mt-1">Built for Nigerians 🇳🇬</p>
          </div>

          <div className="flex items-center justify-center gap-4">
            <Badge variant="secondary" className="bg-accent/10 text-[rgba(91,25,25,1)]">
              🔥 {profileData.streak}-day streak
            </Badge>
          </div>
        </div>

        {/* Goals Card */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Goals</h3>
            <Button variant="ghost" size="sm" className="text-primary">
              Edit goals <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Daily calories</span>
              <span className="text-sm font-medium">{profileData.goals.calories.toLocaleString()} kcal</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Protein target</span>
              <span className="text-sm font-medium">{profileData.goals.protein}g</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Focus nutrient</span>
              <Badge variant="outline" className="text-xs">{profileData.goals.focusNutrient}</Badge>
            </div>
          </div>
        </Card>

        {/* Personal Details Card */}
        <Card className="p-4">
          <h3 className="font-semibold mb-4">Personal Details</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Age</span>
              <span className="text-sm font-medium">{profileData.personal.age} years</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Sex</span>
              <span className="text-sm font-medium">{profileData.personal.sex}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Activity level</span>
              <span className="text-sm font-medium">{profileData.personal.activity}</span>
            </div>
            <div className="flex justify-between items-start">
              <span className="text-sm text-muted-foreground">Dietary preferences</span>
              <div className="flex flex-col gap-1">
                {profileData.personal.dietary.map((pref, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {pref}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Preferences Card */}
        <Card className="p-4">
          <h3 className="font-semibold mb-4">Preferences</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Language</span>
              <span className="text-sm font-medium">{profileData.preferences.language}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Units</span>
              <span className="text-sm font-medium">{profileData.preferences.units}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Location focus</span>
              <span className="text-sm font-medium">{profileData.preferences.location} (auto)</span>
            </div>
          </div>
        </Card>

        {/* Health Focus Card */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Health Focus</h3>
            <Button variant="ghost" size="sm" className="text-primary">
              Manage watchlist <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground mb-3">Current watchlist</p>
            {profileData.healthFocus.map((item, index) => (
              <div key={index} className="flex items-center justify-between py-2">
                <span className="text-sm font-medium">{item.nutrient}</span>
                <div className="flex items-center gap-2">
                  <Badge 
                    variant={item.status === 'low' ? 'destructive' : item.status === 'improving' ? 'secondary' : 'outline'}
                    className="text-xs"
                  >
                    {item.status === 'improving' ? 'improving' : item.status === 'low' ? 'low' : 'good'} {item.icon}
                  </Badge>
                </div>
              </div>
            ))}
            <p className="text-xs text-muted-foreground mt-3">
              💡 I'll nudge you when nutrients stay low for 10+ days
            </p>
          </div>
        </Card>

        {/* Privacy & Data Card */}
        <Card className="p-4">
          <h3 className="font-semibold mb-4">Privacy & Data</h3>
          <div className="space-y-3">
            <Button variant="ghost" className="w-full justify-between p-0 h-auto">
              <div className="flex items-center gap-3">
                <Download className="w-5 h-5 text-muted-foreground" />
                <span className="text-sm">Download data</span>
              </div>
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            </Button>
            
            <Button variant="ghost" className="w-full justify-between p-0 h-auto text-destructive">
              <div className="flex items-center gap-3">
                <Trash2 className="w-5 h-5" />
                <span className="text-sm">Delete account</span>
              </div>
              <ChevronRight className="w-4 h-4" />
            </Button>

            <Separator className="my-4" />
            
            <Button variant="link" className="p-0 h-auto text-xs text-muted-foreground">
              Data policy & privacy
            </Button>
          </div>
        </Card>

        {/* Footer Actions */}
        <div className="space-y-3 pb-8">
          <Button 
            onClick={onShare}
            variant="outline" 
            className="w-full"
          >
            <Share className="w-4 h-4 mr-2" />
            Share progress
          </Button>
          
          <Button 
            onClick={onLogout}
            variant="ghost" 
            className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Log out
          </Button>
        </div>
      </div>
    </div>
  );
}