from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from streamforge_api.models import SetupState, User
from streamforge_api.schemas.setup import InstallationMode, SetupStateResponse


class SetupService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_state(self) -> SetupState:
        state = self.db.scalar(select(SetupState).limit(1))
        if state is not None:
            return state
        state = SetupState()
        self.db.add(state)
        self.db.flush()
        return state

    def administrator_exists(self) -> bool:
        admin_count = self.db.scalar(select(func.count()).select_from(User).where(User.is_admin))
        return bool(admin_count)

    def to_response(self, state: SetupState | None = None) -> SetupStateResponse:
        setup_state = state or self.get_or_create_state()
        installation_mode = (
            setup_state.installation_mode
            if setup_state.installation_mode in {"local_only", "remote_access"}
            else None
        )
        return SetupStateResponse(
            is_complete=setup_state.is_complete,
            current_step=setup_state.current_step,
            completed_steps=list(setup_state.completed_steps_json),
            installation_mode=cast(InstallationMode | None, installation_mode),
            administrator_exists=self.administrator_exists(),
        )

    def mark_account_created(self) -> SetupState:
        state = self.get_or_create_state()
        completed = set(state.completed_steps_json)
        completed.add("account")
        state.completed_steps_json = sorted(completed)
        state.current_step = "installation_mode"
        return state

    def set_installation_mode(self, installation_mode: InstallationMode) -> SetupState:
        state = self.get_or_create_state()
        completed = set(state.completed_steps_json)
        completed.update({"account", "installation_mode"})
        state.completed_steps_json = sorted(completed)
        state.installation_mode = installation_mode
        state.current_step = "dashboard"
        state.is_complete = True
        return state
