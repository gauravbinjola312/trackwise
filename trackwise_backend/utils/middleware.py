import time
import logging
import uuid

logger = logging.getLogger('trackwise_backend')


class RequestLoggingMiddleware:
    """Logs every request with timing, user info, and status code."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Assign request ID
        request.request_id = str(uuid.uuid4())[:8]
        start = time.time()

        response = self.get_response(request)

        duration_ms = round((time.time() - start) * 1000)
        user_info   = getattr(request.user, 'email', 'anon') if hasattr(request, 'user') else 'anon'

        logger.info(
            f'[{request.request_id}] {request.method} {request.path} '
            f'→ {response.status_code} ({duration_ms}ms) user={user_info}'
        )

        response['X-Request-ID'] = request.request_id
        return response
