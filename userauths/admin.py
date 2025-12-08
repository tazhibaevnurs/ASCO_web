from django.contrib import admin
from userauths import models as userauths_models

class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email']

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name']

class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'subject', 'date']

admin.site.register(userauths_models.User, UserAdmin)
admin.site.register(userauths_models.Profile, ProfileAdmin)
admin.site.register(userauths_models.ContactMessage, ContactMessageAdmin)
    