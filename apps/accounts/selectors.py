from django.contrib.auth import get_user_model
from django.db.models import Count

from .models import Role


def users_by_role() -> list[dict]:
    counts = dict(
        get_user_model()
        .objects.filter(is_active=True)
        .order_by()
        .values_list("role")
        .annotate(total=Count("pk"))
    )
    return [{"label": role.label, "total": counts.get(role.value, 0)} for role in Role]
