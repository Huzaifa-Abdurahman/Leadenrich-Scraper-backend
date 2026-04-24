"""
LeadEnrich API - Main entry point

Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from app.main import app

if __name__ == '__main__':
    import uvicorn
    # Bind to 0.0.0.0 to ensure both IPv4 and IPv6 (localhost) connectivity works on Windows
    uvicorn.run(app, host='0.0.0.0', port=8000)
