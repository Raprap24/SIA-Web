from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("movie_verse/", views.dashboard, name="movie_anime"),
    path("movies/", views.movie_list, name="movie_list"),
    path("movies/add/", views.add_movie, name="add_movie"),
    path("movies/<int:pk>/", views.movie_detail, name="movie_detail"),
    path("movies/<int:pk>/edit/", views.edit_movie, name="edit_movie"),
    path("movies/<int:pk>/delete/", views.delete_movie, name="delete_movie"),
    path("my-movies/", views.my_movies, name="my_movies"),
    path("profile/", views.profile, name="profile"),
    path("users/<str:username>/", views.public_profile, name="public_profile"),
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/signup/", views.register, name="register"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path(
        "accounts/password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="MovieVerse/password_change.html",
            success_url="/accounts/password-change/done/",
        ),
        name="password_change",
    ),
    path(
        "accounts/password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="MovieVerse/password_change_done.html",
        ),
        name="password_change_done",
    ),
    path("administration/", views.admin_dashboard, name="admin_dashboard"),
    path("administration/users/", views.admin_users, name="admin_users"),
    path("administration/users/<int:pk>/delete/", views.admin_user_delete, name="admin_user_delete"),
    path("administration/users/<int:pk>/<str:action>/", views.admin_user_action, name="admin_user_action"),
]
