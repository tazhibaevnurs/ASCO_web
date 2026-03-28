from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Токен привязан к is_active: после активации ссылка не сработает повторно.
    Срок жизни — settings.PASSWORD_RESET_TIMEOUT (по умолчанию 1 час), как у сброса пароля Django.
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{timestamp}{user.is_active}"


account_activation_token = AccountActivationTokenGenerator()
