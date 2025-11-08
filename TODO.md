# TODO

* contextvars middleware:
```
from contextvars import ContextVar
from fastapi import FastAPI, Request

user_id_var: ContextVar[str] = ContextVar('user_id')

app = FastAPI()

@app.middleware("http")
async def add_user_id_to_context(request: Request, call_next):
    user_id = request.headers.get("X-User-ID", "anonymous")
    token = user_id_var.set(user_id)
    response = await call_next(request)
    user_id_var.reset(token)
    return response

@app.get("/profile")
async def get_profile():
    user_id = user_id_var.get()
    return {"user_id": user_id}
```

* For this particular application, use the "deleted" field for domain entities (not relationships). For history, Temporal database: create shadow tables. No foreign keys.

* Return refresh token in cookie

* Don't share the same session with more than one request.
```
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)
```

* Chain exception on usage by default.

* Once python 14 is out (Oct?), use uuid7 (instead of uuid4).

* Use `ExceptionGroup`s for multiple concurrent exceptions.

* CORS Middleware (and other middleware needed for security or logging or context)

* Alembic

* TEST: Practical Flow Summary for SPAs
	1.	On login via JavaScript, the server returns the access token in the JSON response body.
	2.	The server also sets the refresh token as a secure, HTTP-only cookie.
	3.	The SPA stores the access token in memory (or optionally localStorage with risk consideration).
	4.	When the access token expires, the SPA requests a new access token by calling the refresh endpoint; the refresh token is sent automatically via the cookie.
	5.	The server returns a new access token and a new refresh token cookie (rotation).
This approach balances security and usability for SPAs, protecting the refresh token while enabling seamless token renewal without exposing sensitive tokens to JavaScript
