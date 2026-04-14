# AI Based Food Recognition with Nutrition Aware Recommendations

## Phase 1 MVP Setup Instructions

### Prerequisites
- Node.js 18+ and npm installed
- Backend server running on http://localhost:8000

### Installation

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Open browser:**
   Navigate to http://localhost:3000

### Phase 1 Features

✅ **ImageUpload Component**
- Drag-and-drop image upload
- File validation
- Loading states during analysis

✅ **NutritionLabel Component**
- Display calories, protein, carbs, fat
- Visual progress bars for macronutrients

✅ **ResultsPanel Component**
- Food identification with confidence scores
- Complete nutrition breakdown
- Mass estimation information

✅ **Main Page Integration**
- Connected to backend API at http://localhost:8000/api/analyze-food
- Error handling and loading states
- Responsive design with Tailwind CSS

### API Integration

The frontend connects to the backend `/api/analyze-food` endpoint:

```typescript
const response = await fetch('http://localhost:8000/api/analyze-food', {
  method: 'POST',
  body: formData,
})
```

### Expected Response Format

```json
{
  "food_label": "biryani",
  "display_name": "Biryani",
  "confidence": 0.91,
  "estimated_mass_g": 250,
  "mass_source": "default_serving_size",
  "macros": {
    "calories": 700,
    "protein_g": 28.8,
    "carbs_g": 87.5,
    "fat_g": 20.0
  },
  "nutrition_source": "INDB",
  "food_not_found": false
}
```

### Testing Phase 1

1. Start the backend: `cd backend && python main.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Upload any food image to test the complete flow
4. Verify nutrition data displays correctly

### Next Phase

Phase 2 will add:
- Bounding box visualization on uploaded images
- Canvas overlay for detection results
