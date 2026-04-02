"""Request ID middleware for request tracing.

Generates a unique request ID for each request and makes it available
throughout the request lifecycle for logging and audit purposes.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Header name for request ID
REQUEST_ID_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique request ID to each request.

    - Accepts incoming X-Request-Id header if present and valid
    - Generates a new UUID if not provided
    - Adds X-Request-Id header to the response
    - Makes request_id available via request.state.request_id

    Usage:
        app.add_middleware(RequestIdMiddleware)

        # In a route or dependency:
        request_id = request.state.request_id
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with request ID tracking."""
        # Get or generate request ID
        request_id = request.headers.get(REQUEST_ID_HEADER)

        # Validate the provided request ID (must be a valid UUID format)
        # If invalid, generate a new one
        if request_id:
            try:
                # Validate it's a proper UUID
                uuid.UUID(request_id)
            except ValueError:
                # Invalid format, generate new one
                request_id = str(uuid.uuid4())
        else:
            # No request ID provided, generate new one
            request_id = str(uuid.uuid4())

        # Store in request state for access by dependencies/routes
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[REQUEST_ID_HEADER] = request_id

        return response


def get_request_id(request: Request) -> str:
    """Get the request ID from request state.

    This is a utility function that can be used as a FastAPI dependency
    or called directly if you have access to the request object.

    Args:
        request: The FastAPI/Starlette Request object

    Returns:
        The request ID string

    Raises:
        AttributeError: If called before RequestIdMiddleware has processed the request
    """
    return getattr(request.state, "request_id", "unknown")
