# KAI Bottom Action Bar - Clean & Professional Design

## Overview
Clean, modern bottom action bar for the Home screen only. Features three core actions with subtle, professional motion and a calm premium feel.

## Key Design Principles
- **Restrained & Professional**: No glow, no notch, no floating animations
- **Home-Only**: Appears exclusively on the Home screen
- **Thumb-Friendly**: Comfortable reach with 44px+ touch targets
- **Premium Feel**: Glassy translucent material with subtle depth

## Components

### 1. BottomActionBar.tsx
Main navigation bar with three actions:
- **Left**: Chat (opens Coach screen) - Speech bubble icon
- **Center**: Log Meal (opens Camera) - Plus icon, primary fill
- **Right**: Micros (opens Micros Overview) - 5-dot vitamin cluster

### 2. MicrosIcon.tsx
Custom 5-dot pentagon cluster representing key micronutrients:
- Iron (#D64545) - Deep red, top center
- Calcium (#4C86E8) - Cool blue, top right
- Magnesium (#2FB7A1) - Teal, bottom right
- Zinc (#7A8CA8) - Slate, bottom left
- Vitamin D (#F5A524) - Warm amber, top left

Alternative flask+sparkles variant included for future use.

## Visual Design

### Bar Styling
- **Container**: 64px height, rounded-16, max-width 360px
- **Material**: Translucent with 16px backdrop blur
- **Background**: rgba(255, 255, 255, 0.08)
- **Border**: 1px solid rgba(255, 255, 255, 0.1)
- **Shadow**: 
  - Rest: `0 8px 24px rgba(0, 0, 0, 0.25)`
  - Scrolled: `0 12px 32px rgba(0, 0, 0, 0.35)`
- **Safe Area**: Respects device safe-area-inset-bottom with `max(12px, env(...))`
- **Spacing**: 20px horizontal padding (5 in Tailwind), comfortable thumb reach

### Button Specifications

#### Center Plus Button
- **Size**: 56px diameter circle
- **Background**: `var(--primary)` solid fill (#7FFFD4 in dark mode)
- **Foreground**: `var(--primary-foreground)`
- **Icon**: Plus (+), 28px (w-7), stroke-width 2.5
- **States**:
  - Default: scale 1
  - Hover: scale 1.05
  - Active/Pressed: scale 0.95
  - Disabled (capturing): opacity 70%, pulsing dot

#### Side Buttons (Chat & Micros)
- **Touch Target**: 44px (w-11 h-11)
- **Icon Size**: 24px (w-6 h-6), stroke-width 2
- **Default State**: 
  - Text: muted-foreground
  - Background: transparent
- **Hover State**:
  - Text: primary
  - Background: primary/10
- **Active/Pressed State**:
  - Text: primary
  - Background: primary/20
  - Scale: 0.95

### Optional Micro Underline
- **Appearance**: 2px height × 28px width
- **Color**: Primary
- **Position**: 8px below button (-bottom-2)
- **Animation**: 
  - Duration: 800ms
  - Easing: ease-out
  - Fade in (0-20%): opacity 0→1, scaleX 0.5→1
  - Hold (20-80%): opacity 1, scaleX 1
  - Fade out (80-100%): opacity 1→0, scaleX 1→0.8

## Motion Specifications

### Tap Feedback
- **Scale Down**: 0.95
- **Duration**: 120ms down, 160ms spring back
- **Easing**: Default transition-all
- **Visual**: Background halo on active state (primary/20 for side buttons)

### Bar Elevation on Scroll
- **Trigger**: `window.scrollY > 10px`
- **Effect**: 
  - Shadow intensifies (md → xl)
  - Bar translates -0.5px (barely perceptible lift)
- **Duration**: 300ms
- **Easing**: ease-out

### No Idle Animations
- Center button does NOT float
- No glowing effects
- No pulsing (except when disabled/capturing)

## Screen Visibility

### Shown On:
- **Home** (ONLY)

### Hidden On:
- Camera (full-screen capture)
- Processing (full-screen analysis)
- Insights (has native header)
- Micros Overview (has native header)
- Coach/Chat (has native header + input)
- Profile (has native header)
- Notifications (has native header)

## Accessibility

### ARIA Labels
- Chat: "Open chat"
- Plus: "Log meal"
- Micros: "View micronutrients"

### Contrast
- AA compliant in dark mode
- Icons use muted-foreground (#B4B4B4 equivalent) with primary (#7FFFD4) on interaction
- Primary button has high contrast white foreground on aquamarine background

### Touch Targets
- All buttons ≥ 44px (iOS/Android guideline)
- Comfortable spacing between targets (minimum 24px gap)

### Motion
- All animations are decorative
- No essential information conveyed only through motion
- Respects `prefers-reduced-motion` via browser defaults

## Color Tokens

Micronutrient colors (defined in globals.css):
```css
--micro-iron: #D64545;
--micro-calcium: #4C86E8;
--micro-magnesium: #2FB7A1;
--micro-zinc: #7A8CA8;
--micro-vitamin-d: #F5A524;
```

## Integration

### App.tsx Updates
- Bottom action bar **only** shows when `currentScreen === 'home'`
- Routes:
  - Chat → `handleChatWithKAI('general')`
  - Plus → `handleLogMeal()` → Camera screen
  - Micros → `navigateToScreen('micros')` → Micros Overview

### HomeScreen Updates
- Bottom padding: `h-24` (96px) to prevent content overlap
- Removed standalone "LOG MEAL" and "Chat with KAI" buttons
- Actions now exclusively through bottom bar

## Technical Implementation

### CSS Features
- Uses CSS custom properties for colors (`var(--primary)`, etc.)
- Backdrop blur with WebKit prefix for iOS compatibility
- Safe area insets with `max()` for universal compatibility
- Inline styles for dynamic values (shadows, backgrounds)

### Animation Performance
- CSS @keyframes for underline animation
- Transform-based animations (GPU-accelerated)
- No layout thrashing (only opacity and transform changes)

### Browser Compatibility
- Backdrop blur: iOS 9+, Android 10+, all modern desktop browsers
- Safe area insets: iOS 11+, modern browsers
- Fallback: Works without blur on older browsers (solid background)

## Differences from Previous Design

### Removed Features
- ❌ Center notch cutout
- ❌ Elevated plus button (now inline at 56px)
- ❌ Gradient background on plus
- ❌ Inner glow effects
- ❌ Idle floating animation
- ❌ Scroll bump animation with ring
- ❌ Separator ring around plus
- ❌ Showing on all screens

### Added Features
- ✅ Optional micro underline feedback
- ✅ Cleaner, single-height bar design
- ✅ Home-only visibility
- ✅ Simpler, more professional aesthetic

## Design Philosophy

This redesign prioritizes **calm professionalism** over visual excitement:

1. **Subtlety**: Motion is minimal and purposeful
2. **Clarity**: Three clear actions, no visual complexity
3. **Focus**: Bar doesn't compete with content
4. **Restraint**: Premium through simplicity, not effects

## Future Enhancements

### Optional Features
1. **Badge on Micros**: 3-4px dot for new critical alerts
2. **Haptic Feedback**: Subtle tap response on supported devices
3. **Dynamic Micros Color**: Dot cluster changes based on current deficiencies
4. **Gesture Support**: Swipe up on plus for quick meal type selection

### Potential Variations
1. **Compact Mode**: 56px height for more screen real estate
2. **Label Mode**: Small labels appear below icons (e.g., "Chat", "Log", "Micros")
3. **Notification Badges**: Unread counts on Chat icon
4. **Progress Indicator**: Subtle ring around plus showing daily calorie progress
