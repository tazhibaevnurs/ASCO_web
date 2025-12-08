from functools import wraps

from django.core.exceptions import PermissionDenied


def role_required(allowed_roles):
    """
    Restrict access to authenticated users whose role matches the given list.
    Superusers are always allowed.
    """

    if not isinstance(allowed_roles, (list, tuple, set)):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied

            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role = getattr(user, "role", None)
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied

        return _wrapped_view

    return decorator

