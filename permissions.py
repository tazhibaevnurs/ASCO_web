"""
Глобальные классы разрешений для проверки ролей пользователей и владения объектами.
Можно использовать в представлениях и сервисах для централизованного контроля доступа.
"""

from functools import wraps
from typing import Iterable, Sequence

from django.http import HttpRequest
from django.core.exceptions import PermissionDenied

SAFE_METHODS: Sequence[str] = ("GET", "HEAD", "OPTIONS")


class BasePermission:
    """
    Базовый класс разрешений.
    Классы-потомки могут переопределять методы has_permission / has_object_permission.
    """

    @classmethod
    def has_permission(cls, request: HttpRequest) -> bool:
        return False

    @classmethod
    def has_object_permission(cls, request: HttpRequest, obj) -> bool:
        return cls.has_permission(request)


class GuestPermission(BasePermission):
    """
    Доступ открыт для неавторизованных пользователей или пользователей с ролью guest.
    """

    @classmethod
    def has_permission(cls, request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return True
        return getattr(user, "role", None) == "guest"


class ManagerPermission(BasePermission):
    """
    Разрешает доступ менеджерам и суперадминам.
    """

    allowed_roles: Sequence[str] = ("manager", "superadmin")

    @classmethod
    def has_permission(cls, request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and (
                getattr(user, "role", None) in cls.allowed_roles
                or getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
            )
        )


class SuperAdminPermission(BasePermission):
    """
    Доступ только для суперадмина (is_superuser или роль superadmin).
    """

    @classmethod
    def has_permission(cls, request: HttpRequest) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and (getattr(user, "is_superuser", False) or getattr(user, "role", None) == "superadmin")
        )


class OwnerOrReadOnlyPermission(BasePermission):
    """
    Разрешает безопасные методы всем.
    Запросы на изменение доступны владельцу объекта или суперадмину.
    """

    owner_attributes: Sequence[str] = ("owner", "user", "created_by", "vendor", "customer")

    @classmethod
    def _resolve_owner(cls, obj, attribute: str):
        owner = getattr(obj, attribute, None)
        if callable(owner):
            try:
                owner = owner()
            except TypeError:
                # Метод без аргументов, например obj.user()
                owner = owner
        return owner

    @classmethod
    def has_permission(cls, request: HttpRequest) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False))

    @classmethod
    def has_object_permission(cls, request: HttpRequest, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True

        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False

        if getattr(user, "is_superuser", False) or getattr(user, "role", None) == "superadmin":
            return True

        for attribute in cls.owner_attributes:
            owner = cls._resolve_owner(obj, attribute)
            if owner == user:
                return True

        return False


def permission_required(*permission_classes):
    """
    Декоратор для проверки разрешений на уровне представления.
    """

    if not permission_classes:
        raise ValueError("Необходимо передать хотя бы один класс разрешений")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            for permission_class in permission_classes:
                if not permission_class.has_permission(request):
                    raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def check_object_permission(request: HttpRequest, permission_class, obj) -> None:
    """
    Хелпер для проверки разрешений на уровне объекта.
    """

    if not permission_class.has_object_permission(request, obj):
        raise PermissionDenied


__all__: Iterable[str] = (
    "SAFE_METHODS",
    "BasePermission",
    "GuestPermission",
    "ManagerPermission",
    "SuperAdminPermission",
    "OwnerOrReadOnlyPermission",
    "permission_required",
    "check_object_permission",
)

