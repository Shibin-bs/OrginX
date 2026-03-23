#!/usr/bin/env python3
"""
Production startup script for OriginX
Serves both API and frontend on port 8000
"""
import uvicorn
import sys
from pathlib import Path

if __name__ == "__main__":
    # Ensure we're in the right directory
    backend_dir = Path(__file__).parent
    sys.path.insert(0, str(backend_dir))
    
    print("=" * 60)
    print("OriginX Production Server")
    print("=" * 60)
    print(f"Backend directory: {backend_dir}")
    
    # Check frontend dist
    frontend_dist = backend_dir.parent / "orgin-frontend" / "dist"
    if frontend_dist.exists():
        print(f"✓ Frontend dist found: {frontend_dist}")
    else:
        print(f"⚠ Frontend dist not found: {frontend_dist}")
        print("  Run 'npm run build' in orgin-frontend first")
    
    print("\nStarting server on http://0.0.0.0:8000")
    print("Press Ctrl+C to stop\n")
    
    # Run with production settings
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload in production
        log_level="info",
        access_log=True,
    )
