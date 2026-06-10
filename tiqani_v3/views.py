from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS
from django.http import JsonResponse


def health(request):
    """Health check endpoint that verifies the application and database are running.

    Returns:
        200 — {"status": "ok", "service": "tiqani_v3", "database": "ok", "debug": bool}
        503 — {"status": "error", "service": "tiqani_v3", "database": "error", "debug": bool}
    """
    db_status = "ok"
    status_code = 200
    try:
        conn = connections[DEFAULT_DB_ALIAS]
        conn.ensure_connection()
    except Exception:
        db_status = "error"
        status_code = 503

    response = {
        "status": "ok" if db_status == "ok" else "error",
        "service": "tiqani_v3",
        "database": db_status,
        "debug": settings.DEBUG,
    }
    return JsonResponse(response, status=status_code)
