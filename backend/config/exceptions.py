from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_msg = ''
        if isinstance(response.data, dict):
            for key, value in response.data.items():
                if isinstance(value, list):
                    error_msg = value[0] if value else str(response.data)
                else:
                    error_msg = str(value)
                break
        else:
            error_msg = str(response.data)

        response.data = {
            'success': False,
            'error': error_msg,
            'code': 'ERROR',
        }

    return response
