# Event & Ticket Booking API (Django REST Framework)

Backend-only REST API. Organizers publish events, attendees book tickets, admins manage everything.

## Setup
```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env   then edit .env
python manage.py migrate
python manage.py createsuperuser # becomes role=admin automatically
python manage.py runserver
```
Swagger docs: http://127.0.0.1:8000/api/v1/docs/ — Run tests: `python manage.py test`

Put your AI key in `.env` as `GEMINI_API_KEY=...` (`.env` is git-ignored, never commit it).
Authentication: send header `Authorization: Token <your token>`.

## Endpoints (all under /api/v1/)
| Method | URL | Who | Notes |
|---|---|---|---|
| POST | auth/register/ | anyone | role: organizer or attendee |
| POST | auth/login/ | anyone | returns token |
| GET | auth/me/ | logged in | |
| CRUD | venues/ | read: all, write: organizer/admin | search by name/city |
| CRUD | events/ | read: all, write: owner organizer/admin | search, filter, order |
| CRUD | ticket-types/ | read: all, write: event owner/admin | |
| POST | events/{id}/book/ | attendee | body: `{"items":[{"ticket_type":1,"quantity":2}]}` |
| GET | events/{id}/stats/ | event owner/admin | tickets sold, revenue, per ticket type |
| GET | bookings/, bookings/{id}/ | owner/admin | users only see their own |
| POST | bookings/{id}/cancel/ | owner/admin | up to 24h before event, restores inventory |
| POST | chat/ | logged in | `{"message":"...", "conversation_id": optional}` |
| GET | chat/conversations/, chat/conversations/{id}/ | owner | replay chats |
| GET | schema/, docs/ | | OpenAPI + Swagger UI |

Event filters: `?search=jazz` `?city=Delhi` `?category=music` `?date_from=2026-12-01&date_to=2026-12-31`
`?min_price=100&max_price=1000` `?ordering=-start_time` `?page=2`

Errors always look like: `{"error": {"status_code": 400, "code": "...", "message": "...", "details": ...}}`

Throttles: booking 10/min per user, chat 5/min per user, login/register 10/min.

## Design notes (changes vs the suggested models)
- `User.email` is unique; superusers automatically get role `admin`.
- `Event.is_published` defaults to True so you can test quickly.
- Added `Event.category` index and a DB check that `end_time > start_time`.
- SQLite ignores `select_for_update`; with PostgreSQL the row lock is real. The code is the same.

## Write-up: APIView vs GenericAPIView vs ViewSet
- **APIView** is the lowest level: you write `get()`/`post()` yourself. I used it for `ChatView`
  because chat is one custom action, not a model CRUD.
- **GenericAPIView** adds `queryset`, `serializer_class`, filtering and pagination helpers; with mixins
  (`CreateAPIView`, `RetrieveAPIView`) you get one ready-made action. I used these for register and `/auth/me/`.
- **ViewSet** groups several actions (list, retrieve, create...) in one class and a router builds the URLs.
  `ModelViewSet` gives full CRUD for Venue, Event and TicketType with almost no code. For bookings I used
  `GenericViewSet` + List/Retrieve mixins only, because bookings are created through `/events/{id}/book/`
  and not by a plain POST. Rule of thumb: CRUD on a model -> ViewSet; one special endpoint -> APIView;
  in between -> GenericAPIView.
