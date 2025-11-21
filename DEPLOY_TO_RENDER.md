# Deploy to Render

## Quick Setup

1. **Push to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Create Render Service**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Select this project

3. **Configure Service**:
   - **Name**: `email-responder`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Set Environment Variables**:
   - `GEMINI_API_KEY`: Your Google AI API key
   - `AI_ENABLED`: `true`

5. **Deploy**: Click "Create Web Service"

## Files Created for Deployment:

- ✅ `main.py` (root level)
- ✅ `requirements.txt` (root level)  
- ✅ `render.yaml` (optional config)
- ✅ `templates/` (copied from backend)

## Your API will be available at:
`https://your-service-name.onrender.com`

## Test Endpoints:
- `GET /` - Health check
- `GET /health` - Detailed health
- `POST /generate-response` - Main API
- `GET /stats` - Usage statistics

## Environment Variables Needed:
- `GEMINI_API_KEY` - Your Google AI API key (required for AI responses)
- `AI_ENABLED` - Set to "true" to enable AI features

That's it! Your FastAPI app will be live on Render.
