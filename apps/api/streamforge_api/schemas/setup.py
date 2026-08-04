from typing import Literal

from pydantic import BaseModel, ConfigDict

InstallationMode = Literal["local_only", "remote_access"]


class SetupStateResponse(BaseModel):
    is_complete: bool
    current_step: str
    completed_steps: list[str]
    installation_mode: InstallationMode | None
    administrator_exists: bool

    model_config = ConfigDict(from_attributes=True)


class SetupStateUpdate(BaseModel):
    installation_mode: InstallationMode
