from django.http import JsonResponse


def health(request):
    """Simple GET endpoint so Simple Browser can render something."""
    return JsonResponse({
        "status": "ok",
        "app": "tiqani_v3",
    })
