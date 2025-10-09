# TODO

* DONE
```
postgres=# create database skrm_local;
CREATE DATABASE
postgres=# create user skrm_user with encrypted password 'P@ssword12';
CREATE ROLE
postgres=# grant all privileges on database skrm_local to skrm_user;
GRANT
```

* from pydantic import BaseModel

class ModelA(BaseModel):
    id: int
    name: str
    email: str

class ModelB(BaseModel):
    id: int
    name: str

a = ModelA(id=1, name='Alice', email='alice@example.com')

# Create an instance of ModelB from ModelA by filtering
data = a.dict()
filtered_data = {k: v for k, v in data.items() if k in ModelB.__fields__}
b = ModelB(**filtered_data)


* Return refresh token in cookie

* Verify JWT contents (don't worry about claims for now)

* Don't share the same session with more than one request.
```
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)
```

* Use the response_model to tell FastAPI the schema of the data you want to send back and have awesome data APIs.

* Directory of hierarchy of exception classes, categorized, with usage examples.
  Chain exception on usage by default.

* Once python 14 is out (Oct?), use uuid7 (instead of uuid4).

* Move models.py classes to a models directory, separating classes.
```
from typing import List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.item import Item  # avoid circular import at runtime

class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    items: List["Item"] = Relationship(back_populates="owner")
```

* Change api directory to routers directory

* Use `ExceptionGroup`s for multiple concurrent exceptions.

* Besides exception attributes, might want to also make use of exception notes.

* Add the token dependency to the router itself, so we don't have to add it to each endpoint.

* CORS Middleware (and other middleware needed for security or logging or context)

* [SQLModel](https://sqlmodel.tiangolo.com), SQLAlchemy, Alembic

* API Patterns
	* Input is different from output. Start with BaseModelNameIn and BaseModelNameOut.
	* Post = new, Put = new | full replacement, Patch = update
	* Dirs:
		* src/api (soon to be src/routers) (use routing when endpoints grow), sr
		* src/schemas (FastAPI models)
		* src/models (SQLAlchemy ORM models)
		* src/db (SQLAlchemy base.py, session.py, etc.)
	* Versioning
```
app/
  services/
    user_service.py  # core functions
  schemas/
    v1/user.py
    v2/user.py
  api/
    v1/users.py
    v2/users.py
```

* Practical Flow Summary for SPAs
	1.	On login via JavaScript, the server returns the access token in the JSON response body.
	2.	The server also sets the refresh token as a secure, HTTP-only cookie.
	3.	The SPA stores the access token in memory (or optionally localStorage with risk consideration).
	4.	When the access token expires, the SPA requests a new access token by calling the refresh endpoint; the refresh token is sent automatically via the cookie.
	5.	The server returns a new access token and a new refresh token cookie (rotation).
This approach balances security and usability for SPAs, protecting the refresh token while enabling seamless token renewal without exposing sensitive tokens to JavaScript
