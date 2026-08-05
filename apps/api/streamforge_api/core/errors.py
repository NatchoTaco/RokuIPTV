class StreamForgeError(Exception):
    status_code = 400
    public_message = "The request could not be completed."

    def __init__(self, public_message: str | None = None) -> None:
        super().__init__(public_message or self.public_message)
        self.public_message = public_message or self.public_message


class AuthenticationFailedError(StreamForgeError):
    status_code = 401
    public_message = "Invalid email or password."


class NotAuthenticatedError(StreamForgeError):
    status_code = 401
    public_message = "Authentication is required."


class AuthorizationError(StreamForgeError):
    status_code = 403
    public_message = "You are not allowed to perform this action."


class BootstrapClosedError(StreamForgeError):
    status_code = 409
    public_message = "Administrator bootstrap is no longer available."


class InvalidSessionError(StreamForgeError):
    status_code = 401
    public_message = "The session is invalid or expired."


class SourceValidationError(StreamForgeError):
    status_code = 422
    public_message = "The source could not be validated."


class SourceNotFoundError(StreamForgeError):
    status_code = 404
    public_message = "Source was not found."


class SourceDisabledError(StreamForgeError):
    status_code = 409
    public_message = "Source is disabled."


class ImportJobNotFoundError(StreamForgeError):
    status_code = 404
    public_message = "Import job was not found."
