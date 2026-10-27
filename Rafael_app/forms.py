from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import MovieVerse, UserProfile

User = get_user_model()


class MovieVerseForm(forms.ModelForm):
    class Meta:
        model = MovieVerse
        fields = [
            "title_name",
            "type",
            "genre",
            "status",
            "rating",
            "release_year",
            "description",
            "poster_url",
            "trailer_url",
        ]
        widgets = {
            "title_name": forms.TextInput(attrs={"placeholder": "e.g. The Grand Budapest Hotel"}),
            "type": forms.TextInput(attrs={"placeholder": "Movie, series, documentary..."}),
            "genre": forms.TextInput(attrs={"placeholder": "e.g. Drama, sci-fi"}),
            "status": forms.TextInput(attrs={"placeholder": "Want to watch, watching, watched..."}),
            "rating": forms.NumberInput(attrs={"min": "0", "max": "10", "step": "0.1", "placeholder": "0–10"}),
            "release_year": forms.NumberInput(attrs={"min": "1888", "max": "2100", "placeholder": "e.g. 2024"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "What makes this one worth watching?"}),
            "poster_url": forms.URLInput(attrs={"placeholder": "https://example.com/poster.jpg"}),
            "trailer_url": forms.URLInput(attrs={"placeholder": "https://youtube.com/..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, label="Full name")
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "full_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["full_name"].strip().split(maxsplit=1)
        user.first_name = full_name[0]
        user.last_name = full_name[1] if len(full_name) > 1 else ""
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            UserProfile.objects.create(user=user)
        return user


class MovieVerseAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    remember_me = forms.BooleanField(required=False, initial=True)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["remember_me"].widget.attrs["class"] = "form-check-input"

    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        if "@" in identifier:
            match = User.objects.filter(email__iexact=identifier).only("username").first()
            if match:
                self.cleaned_data["username"] = match.username
        return super().clean()


class ProfileForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["email"].initial = self.user.email
        self.fields["email"].widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("bio", "avatar_url")
        widgets = {
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3, "maxlength": 280}),
            "avatar_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://example.com/avatar.jpg"}),
        }
