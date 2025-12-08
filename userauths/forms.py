from django import forms
from django.contrib.auth.forms import UserCreationForm

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

from userauths.models import User

class UserRegisterForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder':'Полное имя'}), required=True)
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control rounded', 'placeholder':'Мобильный телефон'}), required=True)
    email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control rounded' , 'placeholder':'Адрес электронной почты'}), required=True)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control rounded' , 'placeholder':'Пароль'}), required=True)
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={ 'class': 'form-control rounded' , 'placeholder':'Подтвердите пароль'}), required=True)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    class Meta:
        model = User
        fields = ['full_name', 'mobile', 'email', 'password1', 'password2', 'captcha']
       
class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control rounded' , 'name': "email", 'placeholder':'Адрес электронной почты'}), required=False)
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class':'form-control rounded' , 'name': "password", 'placeholder':'Пароль'}), required=False)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    class Meta:
        model = User
        fields = ['email', 'password', 'captcha']


class ManagerLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={'class': 'form-control rounded', 'placeholder': 'Адрес электронной почты'}
        ),
        required=True,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control rounded', 'placeholder': 'Пароль'}
        ),
        required=True,
    )
