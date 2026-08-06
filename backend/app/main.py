# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn
import traceback
from dotenv import load_dotenv

# Import all route modules
from .routes import auth, drivers, passengers, rides, deliveries, simulation, ratings, analytics, tracking

load_dotenv()

app = FastAPI(
    title="RidePool+ API",
    description="Hybrid Ride-Pooling and Delivery Optimisation System",
    version="1.0.0"
)

# Enable CORS for frontend
# NOTE: "*" must never be combined with allow_credentials=True - browsers reject
# that combination (and if they didn't, it would allow any site to make
# authenticated requests to this API). List explicit dev origins here, and set
# the FRONTEND_URL environment variable (in your backend host's dashboard) to
# your deployed frontend's URL - no code change/redeploy needed to update it.
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

extra_origin = os.getenv("FRONTEND_URL")
if extra_origin:
    ALLOWED_ORIGINS.append(extra_origin.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(drivers.router, prefix="/api/drivers", tags=["drivers"])
app.include_router(passengers.router, prefix="/api/passengers", tags=["passengers"])
app.include_router(rides.router, prefix="/api/rides", tags=["rides"])
app.include_router(deliveries.router, prefix="/api/deliveries", tags=["deliveries"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
app.include_router(ratings.router, prefix="/api/ratings", tags=["ratings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(tracking.router, prefix="/api/tracking", tags=["tracking"])

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch anything that isn't already an HTTPException so the browser gets a
    real JSON error (with CORS headers) instead of a broken connection that
    shows up as a generic 'failed to fetch'. The real traceback still goes
    to the backend's console for debugging.
    """
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server error: {str(exc)}"}
    )

@app.get("/")
async def root():
    return {"message": "RidePool+ API is running", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2026-07-23"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)