"""Forms needed for authentication."""

from django import forms
from django.contrib.auth import authenticate, login


class LoginForm(forms.Form):
    """Django-backed login form for normal authentication."""

    username = forms.CharField(label="Username", max_length=30,
                               widget=forms.TextInput())
    password = forms.CharField(label="Password",
                               widget=forms.PasswordInput(render_value=False))
    remember = forms.BooleanField(label="Remember Me", required=False)

    user = None

    def clean(self):
        """Validates the login form."""

        if self._errors:
            return
        user = authenticate(username=self.cleaned_data["username"],
                            password=self.cleaned_data["password"])
        if user:
            if user.is_active:
                self.user = user
            else:
                raise forms.ValidationError("This account is currently inactive.")
        else:
            raise forms.ValidationError("Incorrect username and/or password.")
        return self.cleaned_data

    def login(self, request):
        """Logs the user in."""
        if self.is_valid():
            login(request, self.user)
            request.user.message_set.create(
                message="Successfully logged in as %(username)s." %
                {'username': self.user.username})
            if self.cleaned_data['remember']:
                request.session.set_expiry(60 * 60 * 24 * 7 * 3)
            else:
                request.session.set_expiry(0)
            return True
        return False