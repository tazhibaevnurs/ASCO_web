from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


USER_ROLES = (
    ("guest", "Гость"),
    ("manager", "Менеджер"),
    ("superadmin", "Суперадмин"),
)

class User(AbstractUser):
    username = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @property
    def full_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email

    @full_name.setter
    def full_name(self, value: str):
        if not value:
            self.first_name = ""
            self.last_name = ""
            return
        parts = value.strip().split(" ", 1)
        self.first_name = parts[0]
        self.last_name = parts[1] if len(parts) > 1 else ""

    def __str__(self):
        return self.email

    @property
    def role(self):
        if self.is_superuser:
            return "superadmin"
        try:
            profile = self.profile
        except ObjectDoesNotExist:
            return "guest"
        if profile and profile.user_type:
            return profile.user_type
        return "guest"

    def is_manager(self):
        return self.role in ("manager", "superadmin")

    def save(self, *args, **kwargs):
        email_username, _ = self.email.split('@')
        if self.username == "" or self.username == None:
             self.username = email_username
        super(User, self).save(*args, **kwargs)
    

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='accounts/users', default='default/default-user.jpg', null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    mobile = models.CharField(max_length=255, null=True, blank=True)
    user_type = models.CharField(max_length=50, choices=USER_ROLES, default="guest", null=True, blank=True)

    class Meta:
        ordering = ['-id']
        verbose_name_plural = "Профили"

    def __str__(self):
        return self.user.username
    
    def save(self, *args, **kwargs):
        if self.full_name == "" or self.full_name == None:
             self.full_name = self.user.full_name
        if self.user.is_superuser:
            self.user_type = "superadmin"
        elif not self.user_type:
            self.user_type = "guest"
        super(Profile, self).save(*args, **kwargs)

    

class ContactMessage(models.Model):
    full_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return self.full_name

    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Сообщение или Обращение"
    