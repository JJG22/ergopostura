from apps.accounts.permissions import capabilities_of

from .navigation import items_for


def navigation(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"nav_items": [], "caps": frozenset()}

    match = getattr(request, "resolver_match", None)
    namespace = match.namespace if match else None
    return {
        "nav_items": items_for(user, namespace),
        "caps": frozenset(str(capability) for capability in capabilities_of(user)),
    }
