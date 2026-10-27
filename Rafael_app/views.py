from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    MovieVerseAuthenticationForm,
    MovieVerseForm,
    ProfileForm,
    RegistrationForm,
    UserProfileForm,
)
from .models import AdminAuditLog, MovieVerse, UserProfile

User = get_user_model()


def _movie_edit_queryset(user):
    queryset = MovieVerse.objects.all()
    if not user.is_staff:
        queryset = queryset.filter(owner=user)
    return queryset


def _is_admin(user):
    return user.is_authenticated and user.is_staff


def dashboard(request):
    movies = MovieVerse.objects.all()
    context = {
        "movie_count": movies.count(),
        "user_movie_count": movies.filter(owner=request.user).count() if request.user.is_authenticated else 0,
        "genre_count": movies.exclude(genre="").values("genre").distinct().count(),
        "average_rating": movies.aggregate(value=Avg("rating"))["value"],
        "recent_movies": movies.select_related("owner")[:6],
        "top_movies": movies.select_related("owner").order_by("-rating", "-date_added")[:4],
        "my_movies": movies.filter(owner=request.user)[:4] if request.user.is_authenticated else [],
    }
    return render(request, "MovieVerse/dashboard.html", context)


def movie_list(request):
    movies = MovieVerse.objects.select_related("owner")
    query = request.GET.get("q", "").strip()
    genre = request.GET.get("genre", "").strip()
    year = request.GET.get("year", "").strip()
    sort = request.GET.get("sort", "newest")
    if query:
        movies = movies.filter(title_name__icontains=query)
    if genre:
        movies = movies.filter(genre__iexact=genre)
    if year.isdigit():
        movies = movies.filter(release_year=year)
    sort_fields = {
        "newest": ("-date_added",),
        "oldest": ("date_added",),
        "title": ("title_name",),
        "rating": ("-rating", "-date_added"),
    }
    movies = movies.order_by(*sort_fields.get(sort, sort_fields["newest"]))
    genres = MovieVerse.objects.exclude(genre="").values_list("genre", flat=True).distinct().order_by("genre")
    return render(
        request,
        "MovieVerse/movie_list.html",
        {"movies": movies, "genres": genres, "query": query, "selected_genre": genre, "selected_year": year, "sort": sort},
    )


def movie_detail(request, pk):
    movie = get_object_or_404(MovieVerse.objects.select_related("owner"), pk=pk)
    return render(request, "MovieVerse/movie_detail.html", {"movie": movie})


@login_required
def add_movie(request):
    form = MovieVerseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        movie = form.save(commit=False)
        movie.owner = request.user
        movie.save()
        messages.success(request, "Your movie was added to the collection.")
        return redirect("movie_detail", pk=movie.pk)
    return render(request, "MovieVerse/movie_form.html", {"form": form, "is_edit": False})


@login_required
def edit_movie(request, pk):
    movie = get_object_or_404(_movie_edit_queryset(request.user), pk=pk)
    form = MovieVerseForm(request.POST or None, instance=movie)
    if request.method == "POST" and form.is_valid():
        movie = form.save()
        if request.user.is_staff and movie.owner_id != request.user.id:
            AdminAuditLog.objects.create(
                actor=request.user,
                action="movie_edited",
                target=f"Movie #{movie.pk}: {movie.title_name}",
            )
            messages.success(request, "The movie was updated.")
        else:
            messages.success(request, "Your movie was updated.")
        return redirect("movie_detail", pk=movie.pk)
    return render(request, "MovieVerse/movie_form.html", {"form": form, "movie": movie, "is_edit": True})


@login_required
def delete_movie(request, pk):
    movie = get_object_or_404(_movie_edit_queryset(request.user), pk=pk)
    if request.method == "POST":
        title = movie.title_name
        if request.user.is_staff and movie.owner_id != request.user.id:
            AdminAuditLog.objects.create(
                actor=request.user,
                action="movie_deleted",
                target=f"Movie #{movie.pk}: {title}",
            )
        movie.delete()
        messages.success(request, f'"{title}" was removed from the collection.')
        return redirect("movie_list")
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "MovieVerse/movie_confirm_delete.html", {"movie": movie})


@login_required
def my_movies(request):
    movies = MovieVerse.objects.filter(owner=request.user).select_related("owner")
    return render(request, "MovieVerse/my_movies.html", {"movies": movies})


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    user_form = ProfileForm(request.POST or None, instance=request.user, prefix="user")
    profile_form = UserProfileForm(request.POST or None, instance=profile_obj, prefix="profile")
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, "Your profile was updated.")
        return redirect("profile")
    return render(
        request,
        "MovieVerse/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "profile_user": request.user,
            "movie_count": MovieVerse.objects.filter(owner=request.user).count(),
            "recent_movies": MovieVerse.objects.filter(owner=request.user)[:4],
        },
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to MovieVerse. Your account is ready.")
        return redirect("dashboard")
    return render(request, "MovieVerse/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = MovieVerseAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None:
            login(request, user)
            request.session.set_expiry(0 if not form.cleaned_data["remember_me"] else 60 * 60 * 24 * 14)
            destination = request.POST.get("next", "")
            if not url_has_allowed_host_and_scheme(destination, allowed_hosts={request.get_host()}):
                destination = reverse("dashboard")
            return redirect(destination)
        form.add_error(None, "The email/username or password was not recognized.")
    return render(request, "MovieVerse/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("login")


@user_passes_test(_is_admin, login_url="login")
def admin_dashboard(request):
    context = {
        "user_count": User.objects.count(),
        "movie_count": MovieVerse.objects.count(),
        "admin_count": User.objects.filter(is_staff=True, is_active=True).count(),
        "recent_users": User.objects.order_by("-date_joined")[:8],
        "recent_movies": MovieVerse.objects.select_related("owner")[:8],
        "genre_count": MovieVerse.objects.exclude(genre="").values("genre").distinct().count(),
    }
    return render(request, "MovieVerse/admin_dashboard.html", context)


@user_passes_test(_is_admin, login_url="login")
def admin_users(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.annotate(movie_count=Count("movie_posts")).order_by("-date_joined")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    return render(request, "MovieVerse/admin_users.html", {"users": users, "query": query})


@user_passes_test(_is_admin, login_url="login")
@require_POST
def admin_user_action(request, pk, action):
    user = get_object_or_404(User, pk=pk)
    if action in {"promote", "demote"} and not request.user.is_superuser:
        messages.error(request, "Only a superuser can change administrator access.")
        return redirect("admin_users")
    if action in {"suspend", "activate"}:
        if user.is_staff and not request.user.is_superuser:
            messages.error(request, "Only a superuser can change an administrator's account status.")
            return redirect("admin_users")
        if user.pk == request.user.pk and action == "suspend":
            messages.error(request, "You cannot suspend your own account.")
            return redirect("admin_users")
        if (
            user.is_superuser
            and action == "suspend"
            and User.objects.filter(is_superuser=True, is_active=True).count() <= 1
        ):
            messages.error(request, "The last active superuser account cannot be suspended.")
            return redirect("admin_users")
        user.is_active = action == "activate"
    elif action == "promote":
        user.is_staff = True
    elif action == "demote":
        if user.is_superuser:
            messages.error(request, "A superuser account cannot be demoted here.")
            return redirect("admin_users")
        if user.is_staff and User.objects.filter(is_staff=True, is_active=True).count() <= 1:
            messages.error(request, "The last active administrator cannot be demoted.")
            return redirect("admin_users")
        if user.pk == request.user.pk:
            messages.error(request, "You cannot remove your own administrator access.")
            return redirect("admin_users")
        user.is_staff = False
    else:
        messages.error(request, "That account action is not available.")
        return redirect("admin_users")
    user.save(update_fields=["is_active", "is_staff"])
    AdminAuditLog.objects.create(actor=request.user, action=f"user_{action}", target=user.username)
    messages.success(request, f"{user.username}'s account was updated.")
    return redirect("admin_users")


@user_passes_test(_is_admin, login_url="login")
def admin_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if user.pk == request.user.pk:
            messages.error(request, "You cannot delete your own account from the admin panel.")
            return redirect("admin_users")
        if user.is_staff and not request.user.is_superuser:
            messages.error(request, "Only a superuser can delete an administrator account.")
            return redirect("admin_users")
        if user.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
            messages.error(request, "The last active superuser account cannot be deleted.")
            return redirect("admin_users")
        username = user.username
        AdminAuditLog.objects.create(actor=request.user, action="user_deleted", target=username)
        user.delete()
        messages.success(request, f"{username}'s account was deleted.")
        return redirect("admin_users")
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET", "POST"])
    return render(request, "MovieVerse/admin_confirm_user_delete.html", {"target_user": user})


@login_required
def public_profile(request, username):
    profile_user = get_object_or_404(User, username=username, is_active=True)
    profile_obj, _ = UserProfile.objects.get_or_create(user=profile_user)
    return render(
        request,
        "MovieVerse/public_profile.html",
        {
            "profile_user": profile_user,
            "profile_obj": profile_obj,
            "movie_count": MovieVerse.objects.filter(owner=profile_user).count(),
            "recent_movies": MovieVerse.objects.filter(owner=profile_user)[:8],
            "show_email": request.user.is_staff or request.user.pk == profile_user.pk,
        },
    )
