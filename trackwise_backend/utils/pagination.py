from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for all list endpoints.
    Usage: GET /api/v1/expenses/?page=1&page_size=25
    """
    page_size             = 50
    page_size_query_param = 'page_size'
    max_page_size         = 200
    page_query_param      = 'page'

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'pagination': {
                'count':    self.page.paginator.count,
                'pages':    self.page.paginator.num_pages,
                'current':  self.page.number,
                'next':     self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'results': data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'success':    {'type': 'boolean'},
                'pagination': {'type': 'object'},
                'results':    schema,
            }
        }
