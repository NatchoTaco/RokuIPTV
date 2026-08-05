from streamforge_api.core.redaction import redact_text


class StreamForgeError(Exception):
    status_code = 400
    public_message = "The request could not be completed."

    def __init__(self, public_message: str | None = None) -> None:
        redacted_message = redact_text(public_message or self.public_message)
        super().__init__(redacted_message)
        self.public_message = redacted_message


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


class ChannelNotFoundError(StreamForgeError):
    status_code = 404
    public_message = "Channel was not found."


class NormalizationJobNotFoundError(StreamForgeError):
    status_code = 404
    public_message = "Normalization job was not found."


class DuplicateClusterNotFoundError(StreamForgeError):
    status_code = 404
    public_message = "Duplicate cluster was not found."
