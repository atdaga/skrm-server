# TODO

* Directory of hierarchy of exception classes, categorized, with usage examples.
  Chain exception on usage by default.

* Use `ExceptionGroup`s for multiple concurrent exceptions.

* Besides exception attributes, might want to also make use of exception notes.

* API Patterns
	* Input is different from output. Start with BaseModelNameIn and BaseModelNameOut.
	* Post = new, Put = new | full replacement, Patch = update
	* Dirs:
		* src/api (use routing when endpoints grow), sr
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
