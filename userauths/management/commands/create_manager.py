import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from userauths import models as userauths_models


class Command(BaseCommand):
    help = "Создаёт или обновляет пользователя-менеджера (is_staff=True, роль 'manager')."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            dest="email",
            required=True,
            help="Email менеджера (используется как логин).",
        )
        parser.add_argument(
            "--password",
            dest="password",
            help="Пароль менеджера. Если не указан, будет запрошен интерактивно.",
        )
        parser.add_argument(
            "--full-name",
            dest="full_name",
            help="Полное имя менеджера. По умолчанию совпадает с email.",
        )
        parser.add_argument(
            "--mobile",
            dest="mobile",
            help="Телефон менеджера (необязательно).",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options.get("password")
        full_name = (options.get("full_name") or "").strip()
        mobile = (options.get("mobile") or "").strip()

        if not password:
            password = self._prompt_password()

        full_name = full_name or email

        User = get_user_model()

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Создан новый пользователь {email}"))
            else:
                self.stdout.write(self.style.WARNING(f"Пользователь {email} уже существует, данные будут обновлены"))

            user.is_staff = True
            user.is_active = True
            if not user.username:
                user.username = email.split("@")[0]
            user.full_name = full_name
            if password:
                user.set_password(password)
            user.save()

            profile, profile_created = userauths_models.Profile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": full_name,
                    "mobile": mobile or None,
                    "user_type": "manager",
                },
            )

            profile.full_name = full_name
            if mobile:
                profile.mobile = mobile
            profile.user_type = "manager"
            profile.save()

            self.stdout.write(self.style.SUCCESS(f"Менеджер {email} активирован (is_staff=True, роль=manager)"))

    def _prompt_password(self) -> str:
        password = getpass.getpass("Пароль менеджера: ")
        confirm = getpass.getpass("Подтверждение пароля: ")
        if password != confirm:
            raise CommandError("Пароли не совпадают.")
        if not password:
            raise CommandError("Пароль не может быть пустым.")
        return password

