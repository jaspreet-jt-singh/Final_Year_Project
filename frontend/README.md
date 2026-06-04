# AI-Based Food Recognition Frontend

This frontend implements the user-facing application for the AI-based food recognition and nutrition recommendation system. It is built with Next.js 14, React, TypeScript, Tailwind CSS, and Lucide React icons.

## Implemented Features

| Feature | Implementation |
|---|---|
| Image upload | Drag-and-drop upload with file picker fallback |
| Image preview | Local preview generated through FileReader |
| Backend integration | Sends uploaded image as `FormData` to `http://localhost:8000/api/analyze-food` |
| Detection results | Displays all detected food items with confidence values |
| Bounding boxes | Renders detection boxes over the uploaded image |
| Nutrition display | Shows calories, protein, carbs, and fat per 100g |
| Serving adjustment | Allows per-food serving multipliers from 0.25x to 10x |
| Daily goals | Supports Weight Loss, Muscle Gain, Maintenance, and Endurance |
| Calorie target | Supports manual target entry and quick calorie presets |
| Macro tracking | Calculates remaining calories, carbs, protein, and fat |
| Health conditions | Supports condition-aware macro and recommendation adjustments |
| Recommendations | Fetches dietary guidance from the backend recommendation endpoint |
| Fallback behavior | Uses local goal, condition, and macro calculation when backend metadata calls fail |
| Error handling | Handles timeout, backend connection, server, and no-food states |

## Main Files

| File | Purpose |
|---|---|
| `app/page.tsx` | Main screen, state management, API calls, macro tracking, goal controls |
| `app/layout.tsx` | App shell and metadata |
| `app/globals.css` | Tailwind and global styles |
| `components/ImageUpload.tsx` | Upload area, drag/drop behavior, preview, loading overlay |
| `components/ResultsPanel.tsx` | Detection summary, overlays, nutrition cards, servings, recommendations |
| `components/NutritionLabel.tsx` | Nutrition metric cards |
| `components/ImageOverlay.tsx` | Canvas-based overlay component retained for detection visualization support |

## User Flow

1. Select a dietary goal.
2. Set a daily calorie target.
3. Select a health condition.
4. Upload a food image.
5. View detected foods and bounding boxes.
6. Review nutrition values per detected item.
7. Adjust serving multipliers.
8. Track remaining daily calories and macros.
9. Read personalized dietary recommendations.

## API Integration

The frontend calls the backend food-analysis endpoint:

```typescript
const response = await fetch('http://localhost:8000/api/analyze-food', {
  method: 'POST',
  body: formData,
})
```

Expected analysis response:

```json
{
  "detections": [
    {
      "food_label": "Biryani",
      "display_name": "Biryani",
      "confidence": 0.91,
      "bounding_box": [120, 80, 520, 430],
      "macros": {
        "calories": 170,
        "protein_g": 5.2,
        "carbs_g": 25,
        "fat_g": 4.5
      },
      "macros_unit": "per_100g",
      "nutrition_source": "INDB"
    }
  ],
  "img_width": 640,
  "img_height": 480,
  "food_not_found": false
}
```

The frontend also uses these backend endpoints:

| Endpoint | Use |
|---|---|
| `/api/user/goals` | Load available dietary goals |
| `/api/user/health-conditions` | Load available health condition options |
| `/api/user/calculate-macros` | Calculate macro targets |
| `/api/recommendations` | Generate personalized dietary guidance |

## Local Run

Prerequisites:

- Node.js 18+
- npm
- Backend running at `http://localhost:8000`

Commands:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:3000`
