# MovieVerse

MovieVerse is a Django movie-discovery and collection app. It uses Django's built-in account system and the project's existing SQLite database; PHP and MySQL are not required.

## Run locally

Use a Python version supported by the installed Django release, then from the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Sign up for a regular account or use the superuser account to access `/administration/` and Django's `/admin/`.

To load the optional demonstration movies into a fresh database:

```powershell
python manage.py loaddata sample_movies
```

The fixture uses reserved sample IDs `9001` and `9002`; don't load it if those IDs are already in use.

## Features

- Public dashboard, movie discovery, details, title search, genre/year filters, and sorting.
- Account registration, email-or-username sign-in, session logout, password changes, and profile editing.
- Movie posts with poster/trailer URLs, description, release year, genre, status, and a 0–10 rating.
- Users can edit or delete only their own posts. Staff can moderate posts; the server checks permissions on every edit and delete request.
- Staff-only admin dashboard and user management. Only superusers can grant administrator access, and account role fields are never accepted from user profile or movie forms.
- Administrative actions are recorded in an audit log. Movie ownership is cleared rather than deleting a post when its owner account is deleted.
- CSRF protection uses Django middleware and tokens on state-changing forms.

## Data and migrations

Run `python manage.py migrate` after pulling changes. The migration keeps existing movie rows and leaves older posts without an owner; users can still discover them, while staff can moderate them.

## Tests

Run the app tests with:

```powershell
python manage.py test Rafael_app
```
