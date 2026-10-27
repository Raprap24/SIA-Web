from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import AdminAuditLog, MovieVerse, UserProfile

User = get_user_model()


class MovieVerseViewsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="moviefan",
            email="fan@example.com",
            password="SecurePass!234",
        )
        self.other_user = User.objects.create_user(
            username="otherfan",
            email="other@example.com",
            password="SecurePass!234",
        )
        self.admin = User.objects.create_user(
            username="curator",
            email="curator@example.com",
            password="SecurePass!234",
            is_staff=True,
        )
        self.movie = MovieVerse.objects.create(
            owner=self.owner,
            title_name="Moonlight",
            type="Movie",
            genre="Drama",
            status="Watched",
            rating=8.5,
            release_year=2016,
        )

    def test_dashboard_and_movie_listing_render_real_data(self):
        dashboard = self.client.get(reverse("dashboard"))
        listing = self.client.get(reverse("movie_list"), {"q": "moon", "genre": "Drama"})

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Movies in the community")
        self.assertContains(dashboard, "Moonlight")
        self.assertContains(listing, "Moonlight")
        self.assertNotContains(
            self.client.get(reverse("movie_list"), {"q": "unmatched"}),
            "Moonlight",
        )

    def test_registration_creates_hashed_standard_user_and_profile(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newfilmfan",
                "full_name": "New Film Fan",
                "email": "new@example.com",
                "password1": "Strong-Unrelated-Password-492!",
                "password2": "Strong-Unrelated-Password-492!",
            },
        )

        user = User.objects.get(username="newfilmfan")
        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(user.check_password("Strong-Unrelated-Password-492!"))
        self.assertFalse(user.is_staff)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(user.get_full_name(), "New Film Fan")

    def test_login_accepts_email_and_logout_is_post_only(self):
        response = self.client.post(
            reverse("login"),
            {"username": "FAN@example.com", "password": "SecurePass!234", "remember_me": "on"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertGreater(self.client.session.get_expiry_age(), 14 * 24 * 60 * 60 - 10)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))

    def test_movie_creation_assigns_owner_and_ignores_forged_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("add_movie"),
            {
                "title_name": "Arrival",
                "type": "Movie",
                "genre": "Sci-fi",
                "status": "Want to watch",
                "rating": "9.2",
                "release_year": "2016",
                "description": "A first-contact story.",
                "owner": self.other_user.pk,
            },
        )

        movie = MovieVerse.objects.get(title_name="Arrival")
        self.assertRedirects(response, reverse("movie_detail", args=[movie.pk]))
        self.assertEqual(movie.owner, self.owner)

    def test_movie_create_requires_authentication_and_rating_validation(self):
        response = self.client.post(
            reverse("add_movie"),
            {
                "title_name": "Invalid rating",
                "type": "Movie",
                "genre": "Drama",
                "status": "Watched",
                "rating": "11",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.owner)
        invalid_response = self.client.post(
            reverse("add_movie"),
            {
                "title_name": "Invalid rating",
                "type": "Movie",
                "genre": "Drama",
                "status": "Watched",
                "rating": "11",
            },
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFalse(MovieVerse.objects.filter(title_name="Invalid rating").exists())

    def test_only_owner_or_staff_can_edit_and_delete_movies(self):
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(reverse("edit_movie", args=[self.movie.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("delete_movie", args=[self.movie.pk])).status_code, 404)
        self.assertTrue(MovieVerse.objects.filter(pk=self.movie.pk).exists())

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("edit_movie", args=[self.movie.pk]),
            {
                "title_name": "Moonlight updated",
                "type": "Movie",
                "genre": "Drama",
                "status": "Watched",
                "rating": "8.8",
                "release_year": "2016",
                "owner": self.other_user.pk,
            },
        )
        self.assertRedirects(response, reverse("movie_detail", args=[self.movie.pk]))
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title_name, "Moonlight updated")
        self.assertEqual(self.movie.owner, self.owner)

        self.assertEqual(self.client.get(reverse("delete_movie", args=[self.movie.pk])).status_code, 200)
        self.assertTrue(MovieVerse.objects.filter(pk=self.movie.pk).exists())
        self.client.post(reverse("delete_movie", args=[self.movie.pk]))
        self.assertFalse(MovieVerse.objects.filter(pk=self.movie.pk).exists())

    def test_staff_can_moderate_and_moderation_is_audited(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("edit_movie", args=[self.movie.pk]),
            {
                "title_name": "Moderated title",
                "type": "Movie",
                "genre": "Drama",
                "status": "Watched",
                "rating": "8",
                "release_year": "2016",
            },
        )
        self.assertRedirects(response, reverse("movie_detail", args=[self.movie.pk]))
        self.assertTrue(AdminAuditLog.objects.filter(actor=self.admin, action="movie_edited").exists())

    def test_user_cannot_access_admin_panel_or_change_own_role(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('login')}?next={reverse('admin_dashboard')}")
        self.assertEqual(
            self.client.post(
                reverse("admin_user_action", args=[self.other_user.pk, "promote"])
            ).status_code,
            302,
        )
        self.other_user.refresh_from_db()
        self.assertFalse(self.other_user.is_staff)

    def test_staff_admin_pages_render_and_account_actions_are_logged(self):
        self.client.force_login(self.admin)
        dashboard = self.client.get(reverse("admin_dashboard"))
        user_list = self.client.get(reverse("admin_users"))

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "MovieVerse control room")
        self.assertEqual(user_list.status_code, 200)
        self.assertContains(user_list, self.owner.username)

        response = self.client.post(
            reverse("admin_user_action", args=[self.other_user.pk, "suspend"])
        )
        self.assertRedirects(response, reverse("admin_users"))
        self.other_user.refresh_from_db()
        self.assertFalse(self.other_user.is_active)
        self.assertTrue(AdminAuditLog.objects.filter(actor=self.admin, action="user_suspend").exists())

    def test_public_profile_does_not_expose_another_users_email(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("public_profile", args=[self.owner.username]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.owner.email)

    def test_profile_update_does_not_accept_privilege_changes(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("profile"),
            {
                "user-first_name": "Updated",
                "user-last_name": "Name",
                "user-email": "updated@example.com",
                "profile-bio": "A fan of thoughtful science fiction.",
                "profile-avatar_url": "",
                "is_staff": "on",
                "is_superuser": "on",
            },
        )

        self.assertRedirects(response, reverse("profile"))
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.get_full_name(), "Updated Name")
        self.assertEqual(self.owner.email, "updated@example.com")
        self.assertFalse(self.owner.is_staff)
        self.assertFalse(self.owner.is_superuser)
        self.assertEqual(self.owner.movieverse_profile.bio, "A fan of thoughtful science fiction.")

    def test_movie_deletion_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)

        response = csrf_client.post(reverse("delete_movie", args=[self.movie.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(MovieVerse.objects.filter(pk=self.movie.pk).exists())

    def test_superuser_cannot_suspend_the_last_active_superuser(self):
        superuser = User.objects.create_superuser(
            username="rootcurator",
            email="root@example.com",
            password="SecurePass!234",
        )
        self.client.force_login(superuser)
        response = self.client.post(
            reverse("admin_user_action", args=[superuser.pk, "suspend"])
        )
        self.assertRedirects(response, reverse("admin_users"))
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_active)


class SampleMovieFixtureTests(TestCase):
    fixtures = ["sample_movies"]

    def test_fixture_loads_standalone_sample_movies(self):
        movies = MovieVerse.objects.filter(title_id__in=[9001, 9002])

        self.assertEqual(movies.count(), 2)
        self.assertTrue(all(movie.owner_id is None for movie in movies))
