from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
import time


app = FastAPI(title="Chennai Flood Nowcast API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start time for uptime calculation
start_time = time.time()

@app.get("/api/health")
def health_check():
    return {
        "status": "Running",
        "uptime_seconds": int(time.time() - start_time),
        "service": "Chennai Flood Nowcast API"
    }

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
