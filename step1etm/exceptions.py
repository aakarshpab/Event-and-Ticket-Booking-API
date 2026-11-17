from rest_framework import exceptions
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Every error in the API looks like:
    {"error": {"status_code": 400, "code": "...", "message": "...", "details": ...}}
    """
    response = exception_handler(exc, context)
    if response is None:  # unexpected server error -> Django's own 500 handling
        return None

    if isinstance(exc, exceptions.ValidationError):
        code = "validation_error"
        message = "Validation failed."
        details = response.data
    else:
        codes = exc.get_codes() if hasattr(exc, "get_codes") else "error"
        code = codes if isinstance(codes, str) else "error"
        message = str(response.data.get("detail", "Error")) if isinstance(response.data, dict) else "Error"
        details = None

    response.data = {
        "error": {
            "status_code": response.status_code,
            "code": code,
            "message": message,
            "details": details,
        }
    }
    return response
