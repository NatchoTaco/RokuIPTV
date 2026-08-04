from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from streamforge_api.api.deps import get_current_admin, get_db
from streamforge_api.models import User
from streamforge_api.schemas.setup import SetupStateResponse, SetupStateUpdate
from streamforge_api.services.setup import SetupService

router = APIRouter()


@router.get("/state", response_model=SetupStateResponse)
def get_setup_state(db: Session = Depends(get_db)) -> SetupStateResponse:
    return SetupService(db).to_response()


@router.patch("/state", response_model=SetupStateResponse)
def update_setup_state(
    payload: SetupStateUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(get_current_admin),
) -> SetupStateResponse:
    setup_service = SetupService(db)
    state = setup_service.set_installation_mode(payload.installation_mode)
    db.commit()
    return setup_service.to_response(state)
