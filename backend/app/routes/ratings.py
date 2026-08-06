# routes/ratings.py
from fastapi import APIRouter, HTTPException, Depends
import uuid

from ..database import supabase
from ..models import RatingCreate
from ..token_auth import get_current_user, require_self
from ..audit import log_action

router = APIRouter()


@router.post("/")
async def create_rating(req: RatingCreate, current_user: dict = Depends(get_current_user)):
    """
    Submit a 1-5 star rating (+ optional comment) after a completed trip.
    One rating per (request_id, rater_role) - can't rate the same trip twice.
    Updates the target's running average rating.
    """
    require_self(current_user, req.rater_id, expected_role=req.rater_role)

    if req.stars < 1 or req.stars > 5:
        raise HTTPException(status_code=400, detail="Stars must be between 1 and 5")

    ride_result = supabase.table('ride_requests').select('status').eq('request_id', req.request_id).execute()
    if not ride_result.data:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride_result.data[0].get('status') != 'completed':
        raise HTTPException(status_code=409, detail="You can only rate a completed trip")

    existing = supabase.table('ratings').select('rating_id') \
        .eq('request_id', req.request_id).eq('rater_role', req.rater_role).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="You've already rated this trip")

    rating_id = str(uuid.uuid4())
    supabase.table('ratings').insert({
        'rating_id': rating_id,
        'request_id': req.request_id,
        'rater_role': req.rater_role,
        'rater_id': req.rater_id,
        'target_role': req.target_role,
        'target_id': req.target_id,
        'stars': req.stars,
        'comment': req.comment
    }).execute()

    # Recompute the target's running average
    table = 'drivers' if req.target_role == 'driver' else 'passengers'
    id_field = 'driver_id' if req.target_role == 'driver' else 'passenger_id'

    all_ratings = supabase.table('ratings').select('stars').eq('target_role', req.target_role).eq('target_id', req.target_id).execute()
    stars_list = [r['stars'] for r in all_ratings.data]
    avg = round(sum(stars_list) / len(stars_list), 2) if stars_list else 0

    supabase.table(table).update({
        'avg_rating': avg,
        'rating_count': len(stars_list)
    }).eq(id_field, req.target_id).execute()

    log_action(req.rater_id, req.rater_role, 'rating_submitted', {'target_id': req.target_id, 'target_role': req.target_role, 'stars': req.stars})
    return {"message": "Rating submitted", "rating_id": rating_id, "new_average": avg}


@router.get("/for/{target_role}/{target_id}")
async def get_ratings_for(target_role: str, target_id: str):
    """All ratings + running average for a driver or passenger."""
    result = supabase.table('ratings').select('*') \
        .eq('target_role', target_role).eq('target_id', target_id) \
        .order('created_at', desc=True).execute()

    stars_list = [r['stars'] for r in result.data]
    avg = round(sum(stars_list) / len(stars_list), 2) if stars_list else 0

    return {"average": avg, "count": len(stars_list), "ratings": result.data}


@router.get("/pending/{request_id}")
async def get_pending_rating_status(request_id: str):
    """Whether the passenger and/or driver have already rated this trip -
    used by the frontend to decide whether to show the 'rate your trip' prompt."""
    result = supabase.table('ratings').select('rater_role').eq('request_id', request_id).execute()
    rated_roles = [r['rater_role'] for r in result.data]
    return {
        "passenger_rated": 'passenger' in rated_roles,
        "driver_rated": 'driver' in rated_roles
    }
