from fastapi import APIRouter
from ..driver_analysis import decompose_revenue_drivers

router = APIRouter(prefix="/api/driver-tree", tags=["driver"])

@router.get("")
def get_driver_tree():
    return decompose_revenue_drivers()
