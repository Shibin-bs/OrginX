# 🚀 OriginX Production Deployment Guide

## Quick Start

### Option 1: Using Production Script (Recommended)
```bash
cd orgin-backend
python start_production.py
```

### Option 2: Direct Uvicorn
```bash
cd orgin-backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --no-reload
```

## Access Points

Once started, access the application at:

- **🌐 Frontend UI**: http://localhost:8000/
- **🔧 API Health**: http://localhost:8000/api/health
- **📋 API Registry**: http://localhost:8000/api/consent/registry
- **📚 API Docs**: http://localhost:8000/docs (FastAPI auto-generated)

## What's Deployed

### Backend (Port 8000)
- ✅ FastAPI server with all API endpoints
- ✅ SQLite database (originx.db)
- ✅ CORS enabled for all origins
- ✅ Static file serving for frontend

### Frontend (Served from Backend)
- ✅ React application (built)
- ✅ Static assets served from `/assets/`
- ✅ SPA routing (all routes serve index.html)

## API Endpoints

### Health & Registry
- `GET /api/health` - System status
- `GET /api/consent/registry` - List registered users

### Consent
- `POST /api/consent/register` - Register new identity
- `GET /api/consent/registry` - Get registry

### Watermark
- `POST /api/watermark/embed` - Embed watermark
- `POST /api/watermark/extract` - Extract watermark
- `POST /api/watermark/verify` - Verify image

### Detection
- `POST /api/detect/analyze` - Analyze image for deepfake

## Testing

### Manual Testing
1. Open browser: http://localhost:8000
2. Test registration
3. Test watermark embedding
4. Test watermark extraction
5. Test image analysis

### API Testing
```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/api/health"

# Registry
Invoke-RestMethod -Uri "http://localhost:8000/api/consent/registry"
```

## Troubleshooting

### Port Already in Use
If port 8000 is busy:
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### Frontend Not Loading
1. Ensure frontend is built: `cd orgin-frontend && npm run build`
2. Check `orgin-frontend/dist` folder exists
3. Verify `index.html` and `assets/` folder exist

### API Routes Not Working
- Ensure API routes are registered before catch-all route
- Check server logs for errors
- Verify database file exists (`originx.db`)

## Production Notes

- ✅ No auto-reload (production mode)
- ✅ Proper error handling
- ✅ CORS configured
- ✅ Static file serving optimized
- ✅ SPA routing configured

## Status

🟢 **READY FOR TESTING**

The application is fully deployed and ready for testing on port 8000.
