class APIError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class AuthenticationError(APIError):
    pass


class PermissionDenied(APIError):
    pass


class NotFound(APIError):
    pass


class RateLimited(APIError):
    pass


class ServerError(APIError):
    pass


class TransportError(APIError):
    pass


class ProtocolError(APIError):
    pass
