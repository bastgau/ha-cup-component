"""The above classes represent the specific exceptions raised during the API calls."""


class ActionExecutionError(Exception):
    """The class `ActionExecutionError` is used to raise an exception when an action cannot be executed."""

    message: str = "The action requested has failed. Please check HA logs or Cup logs."

    def __init__(self) -> None:
        """Initialize ActionExecutionError with a default error message."""
        super().__init__(self.message)


class BadGatewayError(Exception):
    """The class `BadGatewayError` represents an exception for receiving an invalid response from an upstream server."""

    def __init__(
        self,
        message: str = "Received an invalid response from an upstream server.",
    ) -> None:
        """Initialize BadGatewayError with an optional custom message.

        Args:
            message (str): The error message describing the bad gateway condition.

        """
        self.message = message
        super().__init__(self.message)


class BadRequestError(Exception):
    """The class `BadRequestError` is defined for requests that are unacceptable."""

    def __init__(
        self,
        message: str = "The request was unacceptable, often due to a missing required parameter",
    ) -> None:
        """Initialize BadRequestError with an optional custom message.

        Args:
            message (str): The error message describing the bad request condition.

        """
        self.message = message
        super().__init__(self.message)


class ClientConnectorError(Exception):
    """The class `ClientConnectorError` is used to raise an exception when the Cup server is unreachable."""

    def __init__(
        self,
        message: str = "The Cup server seems to be unreachable.",
    ) -> None:
        """Initialize ClientConnectorError with an optional custom message.

        Args:
            message (str): The error message describing the connection failure.

        """
        self.message = message
        super().__init__(self.message)


class ContentApiTypeError(Exception):
    """The class `ContentApiTypeError` is used to raise an exception when the content type provided by the API is incorrect."""

    def __init__(
        self,
        message: str = "Invalid content type returned by the API.",
    ) -> None:
        """Initialize ContentApiTypeError with an optional custom message.

        Args:
            message (str): The error message describing the content type issue.

        """
        self.message = message
        super().__init__(self.message)


class ForbiddenError(Exception):
    """The class `ForbiddenError` represents an exception for when an API key lacks the necessary permissions for a request."""

    def __init__(
        self,
        message: str = "The API key doesn't have permissions to perform the request.",
    ) -> None:
        """Initialize ForbiddenError with an optional custom message.

        Args:
            message (str): The error message describing the forbidden access condition.

        """
        self.message = message
        super().__init__(self.message)


class GatewayTimeoutError(Exception):
    """The class `GatewayTimeoutError` represents an exception that occurs when a server acting as a gateway times out waiting for another server."""

    def __init__(
        self,
        message: str = "The server, while acting as a gateway, timed out waiting for another server.",
    ) -> None:
        """Initialize GatewayTimeoutError with an optional custom message.

        Args:
            message (str): The error message describing the gateway timeout condition.

        """
        self.message = message
        super().__init__(self.message)


class MethodNotAllowedError(Exception):
    """The class `MethodNotAllowedError` represents an exception that occurs when a request's HTTP method is not supported on the server."""

    def __init__(
        self,
        message: str = "The HTTP method is not supported on the server.",
    ) -> None:
        """Initialize MethodNotAllowedError with an optional custom message.

        Args:
            message (str): The error message describing the unsupported HTTP method.

        """
        self.message = message
        super().__init__(self.message)


class NotFoundError(Exception):
    """The class `NotFoundError` represents a situation where a requested resource does not exist."""

    def __init__(
        self,
        message: str = "The requested resource doesn't exist.",
    ) -> None:
        """Initialize NotFoundError with an optional custom message.

        Args:
            message (str): The error message describing the missing resource.

        """
        self.message = message
        super().__init__(self.message)


class RequestFailedError(Exception):
    """The class `RequestFailedError` defines an exception for when a request fails."""

    def __init__(
        self,
        message: str = "The parameters were valid but the request failed.",
    ) -> None:
        """Initialize RequestFailedError with an optional custom message.

        Args:
            message (str): The error message describing the request failure.

        """
        self.message = message
        super().__init__(self.message)


class ServerError(Exception):
    """The class `ServerError` defines an exception for internal server errors."""

    def __init__(
        self,
        message: str = "An internal server error occurred.",
    ) -> None:
        """Initialize ServerError with an optional custom message.

        Args:
            message (str): The error message describing the internal server error.

        """
        self.message = message
        super().__init__(self.message)


class ServiceUnavailableError(Exception):
    """The class `ServiceUnavailableError` defines an exception for when the server is temporarily unavailable."""

    def __init__(
        self,
        message: str = "The server is temporarily unavailable, usually due to maintenance or overload.",
    ) -> None:
        """Initialize ServiceUnavailableError with an optional custom message.

        Args:
            message (str): The error message describing the service unavailability.

        """
        self.message = message
        super().__init__(self.message)


class TooManyRequestsError(Exception):
    """The class `TooManyRequestsError` represents hitting the API with too many requests too quickly."""

    def __init__(
        self,
        message: str = "Too many requests hit the API too quickly.",
    ) -> None:
        """Initialize TooManyRequestsError with an optional custom message.

        Args:
            message (str): The error message describing the rate limit condition.

        """
        self.message = message
        super().__init__(self.message)


class UnauthorizedError(Exception):
    """The class `UnauthorizedError` is used to raise an exception when no session identity is provided for an endpoint requiring authorization."""

    def __init__(
        self,
        message: str = "No session identity provided for endpoint requiring authorization.",
    ) -> None:
        """Initialize UnauthorizedError with an optional custom message.

        Args:
            message (str): The error message describing the authorization failure.

        """
        self.message = message
        super().__init__(self.message)


def handle_status(status_code: int) -> None:
    """Raise specific exceptions based on the input status code.

    Args:
        status_code (int): Represents the status code and handles it based on the provided mapping.

    Returns:
        None.

    Raises:
        BadRequestError: If the status code is 400.
        UnauthorizedError: If the status code is 401.
        RequestFailedError: If the status code is 402.
        ForbiddenError: If the status code is 403.
        NotFoundError: If the status code is 404.
        MethodNotAllowedError: If the status code is 405.
        TooManyRequestsError: If the status code is 429.
        ServerErrorError: If the status code is 500.
        BadGatewayError: If the status code is 502.
        ServiceUnavailableError: If the status code is 503.
        GatewayTimeoutError: If the status code is 504.
        NotImplementedError: If the status code is not mapped in the exception map.

    """

    if status_code < 400:
        return

    exception_map = {
        400: BadRequestError,
        401: UnauthorizedError,
        402: RequestFailedError,
        403: ForbiddenError,
        404: NotFoundError,
        405: MethodNotAllowedError,
        429: TooManyRequestsError,
        500: ServerError,
        502: BadGatewayError,
        503: ServiceUnavailableError,
        504: GatewayTimeoutError,
    }

    if status_code in exception_map:
        raise exception_map[status_code]()  # noqa: RSE102

    msg: str = f"Unexpected error: Status code {status_code}"
    raise NotImplementedError(msg)
