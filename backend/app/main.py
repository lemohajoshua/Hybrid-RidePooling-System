# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Import all route modules
from .routes import auth, drivers, passengers, rides, deliveries, simulation

load_dotenv()

app = FastAPI(
    title="RidePool+ API",
    description="Hybrid Ride-Pooling and Delivery Optimisation System",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5500", "*"],
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

@app.get("/")
async def root():
    return {"message": "RidePool+ API is running", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2026-07-23"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)