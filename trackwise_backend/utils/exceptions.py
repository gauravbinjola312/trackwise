"""Custom exception handler — consistent JSON error format across all endpoints."""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('trackwise_backend')


def custom_exception_handler(exc, context):
    """
    Returns consistent error responses:
    {
        "success": false,
        "error": {
            "code":    "VALIDATION_ERROR",
            "message": "Human-readable message",
            "detail":  { field-level errors or None }
        }
    }
    """
    # Handle our custom ApplicationError subclasses first
    if isinstance(exc, ApplicationError):
        return exc.to_response()

    response = exception_handler(exc, context)

    if response is not None:
        error_code    = _get_error_code(response.status_code)
        error_message = _extract_message(response.data)
        error_detail  = response.data if isinstance(response.data, dict) else None

        response.data = {
            'success': False,
            'error': {
                'code':    error_code,
                'message': error_message,
                'detail':  error_detail,
            }
        }

        # Log 5xx errors
        if response.status_code >= 500:
            logger.error(f'Server error: {exc}', exc_info=True, extra={'request': context.get('request')})

    return response


def _get_error_code(status_code):
    codes = {
        400: 'VALIDATION_ERROR',
        401: 'AUTHENTICATION_REQUIRED',
        403: 'PERMISSION_DENIED',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        409: 'CONFLICT',
        429: 'RATE_LIMIT_EXCEEDED',
        500: 'INTERNAL_SERVER_ERROR',
        503: 'SERVICE_UNAVAILABLE',
    }
    return codes.get(status_code, 'API_ERROR')


def _extract_message(data):
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'non_field_errors' in data:
            errs = data['non_field_errors']
            return errs[0] if errs else 'Validation failed'
        # Field-level errors → pick first one
        for field, errors in data.items():
            if isinstance(errors, list) and errors:
                return f"{field}: {errors[0]}"
        return 'Validation failed'
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)


class ApplicationError(Exception):
    """Base application-level exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'APPLICATION_ERROR'
    default_message = 'An error occurred'

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code    = code    or self.default_code
        super().__init__(self.message)

    def to_response(self):
        return Response({
            'success': False,
            'error': { 'code': self.code, 'message': self.message, 'detail': None }
        }, status=self.status_code)


class SubscriptionRequiredError(ApplicationError):
    status_code   = status.HTTP_402_PAYMENT_REQUIRED
    default_code  = 'SUBSCRIPTION_REQUIRED'
    default_message = 'An active subscription is required to access this feature.'


class UserLimitReachedError(ApplicationError):
    status_code   = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code  = 'USER_LIMIT_REACHED'
    default_message = 'The platform is currently at capacity. Please try again later.'
