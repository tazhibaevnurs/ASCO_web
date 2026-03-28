from django import forms
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox


class ContactForm(forms.Form):
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control rounded", "placeholder": "Ваше имя"}
        ),
    )
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(
            attrs={"class": "form-control rounded", "placeholder": "Email"}
        ),
    )
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control rounded", "placeholder": "Тема"}
        ),
    )
    message = forms.CharField(
        max_length=5000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control rounded",
                "rows": 5,
                "placeholder": "Сообщение",
            }
        ),
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())
