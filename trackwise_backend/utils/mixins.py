from rest_framework.response import Response
from rest_framework import status


class SuccessResponseMixin:
    """
    Wraps all successful responses in:
    { "success": true, "data": { ... } }
    """

    def success(self, data=None, message=None, status_code=status.HTTP_200_OK):
        payload = {'success': True}
        if message:
            payload['message'] = message
        if data is not None:
            payload['data'] = data
        return Response(payload, status=status_code)

    def created(self, data, message='Created successfully'):
        return self.success(data, message, status.HTTP_201_CREATED)

    def deleted(self, message='Deleted successfully'):
        return Response({'success': True, 'message': message}, status=status.HTTP_204_NO_CONTENT)


class UserOwnedQuerysetMixin:
    """
    Restricts queryset to objects owned by the requesting user.
    All data endpoints extend this.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)
