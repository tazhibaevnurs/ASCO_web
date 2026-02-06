from django import forms
from django.contrib.auth.forms import UserCreationForm

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

from userauths.models import User

class UserRegisterForm(UserCreationForm):
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder': 'Полное имя'}),
        required=True,
        error_messages={'required': 'Обязательное поле.'},
    )
    mobile = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder': 'Мобильный телефон'}),
        required=True,
        error_messages={'required': 'Обязательное поле.', 'invalid': 'Введите корректный номер телефона.'},
    )
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder': 'Адрес электронной почты'}),
        required=True,
        error_messages={'required': 'Обязательное поле.', 'invalid': 'Введите корректный email.'},
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control rounded', 'placeholder': 'Пароль'}),
        required=True,
        error_messages={'required': 'Обязательное поле.'},
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control rounded', 'placeholder': 'Подтвердите пароль'}),
        required=True,
        error_messages={'required': 'Обязательное поле.'},
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    class Meta:
        model = User
        fields = ['full_name', 'mobile', 'email', 'password1', 'password2', 'captcha']

    error_messages = {'password_mismatch': 'Пароли не совпадают.'}
       
class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'name': 'email', 'placeholder': 'Адрес электронной почты'}),
        required=False,
        error_messages={'invalid': 'Введите корректный email.'},
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control rounded', 'name': 'password', 'placeholder': 'Пароль'}),
        required=False,
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())


class ManagerLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder': 'Адрес электронной почты'}),
        required=True,
        error_messages={'required': 'Обязательное поле.', 'invalid': 'Введите корректный email.'},
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control rounded', 'placeholder': 'Пароль'}),
        required=True,
        error_messages={'required': 'Обязательное поле.'},
    )
