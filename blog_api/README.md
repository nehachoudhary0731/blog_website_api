# Blog REST API

A production-ready Django REST Framework blog backend built for freshers learning Python backend development. Every line is commented to explain the *why*, not just the *what*.

## Frontend

A lightweight Vanilla JavaScript frontend is included for:

- Authentication (Login/Register)
- Writing & editing posts
- Categories & tags
- Likes & bookmarks
- Nested comments
- Search & filtering
- Pagination
- Dashboard for managing posts

The frontend communicates with the Django REST API using JWT authentication.

## Features

| Feature | Implementation |
|---|---|
| Auth (register/login/logout) | JWT via `djangorestframework-simplejwt` with token blacklist |
| Posts CRUD | Class-based views, slug-based lookup, UUID primary key |
| Draft/Published state machine | `Post.Status` choices + `publish()` / `unpublish()` methods |
| Search & filtering | `django-filter` + DRF `SearchFilter` + `OrderingFilter` |
| Pagination | `PageNumberPagination` (10 per page) |
| Nested comments | Self-referential FK + recursive serialiser |
| Tags & categories | M2M + FK with auto-slug generation |
| Like / Bookmark | Toggle endpoints, `unique_together` prevents duplicates |
| Author-only access | Custom `IsAuthorOrReadOnly` permission class |
| Admin panel | Fully configured `ModelAdmin` for all models |
| View tracking | Unique view counting using cache/IP |
| Frontend integration | Vanilla JS + Fetch API |

## Project structure

```
blog_api/
├── blog/
│   ├── models.py       # Post, Comment, Category, Tag, Like, Bookmark
│   ├── serializers.py  # List, Detail, Create/Update serialisers
│   ├── views.py        # All blog views (CBVs)
│   ├── permissions.py  # IsAuthorOrReadOnly
│   ├── filters.py      # PostFilter (django-filter)
│   └── urls.py         # /api/posts/* /api/comments/* routes
│
├── users/
│   ├── models.py       # Custom User (email login)
│   ├── serializers.py  # Register, Profile, Token serialisers
│   ├── views.py        # Register, Login, Logout, Profile views
│   └── urls.py         # /api/auth/* routes
│
├── config/
│   ├── settings.py   # All Django + DRF + JWT config
│   └── urls.py       # Root URL router
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── manage.py
├── requirements.txt
├── README.md
```


## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations (creates db.sqlite3)
python manage.py migrate

# 3. Create a superuser (for /admin panel)
python manage.py createsuperuser

# 4. Start the development server
python manage.py runserver
```

Visit http://127.0.0.1:8000/admin to manage data via Django Admin.

## Key API endpoints

```
POST   /api/auth/register/          Register new user
POST   /api/auth/login/             Login → JWT tokens
POST   /api/auth/logout/            Blacklist refresh token
POST   /api/auth/token/refresh/     Get new access token
GET    /api/auth/profile/           My profile
PATCH  /api/auth/profile/           Update profile
GET    /api/auth/users/<username>/  Public profile

GET    /api/posts/                  List posts (search, filter, paginate)
POST   /api/posts/                  Create post  🔒
GET    /api/posts/mine/             My posts (all statuses)  🔒
GET    /api/posts/<slug>/           Post detail
PATCH  /api/posts/<slug>/           Edit post  🔒 author only
DELETE /api/posts/<slug>/           Delete post  🔒 author only

POST   /api/posts/<slug>/like/      Toggle like  🔒
POST   /api/posts/<slug>/bookmark/  Toggle bookmark  🔒
GET    /api/bookmarks/              My bookmarks  🔒

GET    /api/posts/<slug>/comments/  List comments (nested)
POST   /api/posts/<slug>/comments/  Add comment or reply  🔒
PATCH  /api/comments/<id>/          Edit comment  🔒 author only
DELETE /api/comments/<id>/          Soft-delete comment  🔒 author only

GET    /api/categories/             List categories
POST   /api/categories/             Create category  🔒
GET    /api/tags/                   List tags
POST   /api/tags/                   Create tag  🔒
```

## Key concepts to learn from this project

1. **Custom User model** — always set `AUTH_USER_MODEL` before first migration
2. **JWT flow** — access token (short-lived) + refresh token (long-lived) + blacklist on logout
3. **IsAuthorOrReadOnly** — `has_object_permission` vs `has_permission` difference
4. **Serialiser layering** — separate List/Detail/Create serialisers for the same model
5. **Soft delete** — mark `is_deleted=True` instead of deleting to preserve thread structure
6. **State machine** — `Status.choices` + `publish()` method encapsulates business logic in the model
7. **`select_related` & `prefetch_related`** — prevent N+1 query problems in list views
8. **`unique_together`** — DB-level uniqueness for Like/Bookmark (race-condition safe)

## Moving to production

- Set `DEBUG = False` and `SECRET_KEY` via environment variable
- Switch to PostgreSQL (`psycopg2-binary`)
- Use `gunicorn` as WSGI server
- Serve media/static files via Nginx or cloud storage (S3)
