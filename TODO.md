# TODO

* CORS Middleware (and other middleware needed for security or logging or context)

* Return refresh token in cookie

* Alembic

* TEST: Practical Flow Summary for SPAs
	1.	On login via JavaScript, the server returns the access token in the JSON response body.
	2.	The server also sets the refresh token as a secure, HTTP-only cookie.
	3.	The SPA stores the access token in memory (or optionally localStorage with risk consideration).
	4.	When the access token expires, the SPA requests a new access token by calling the refresh endpoint; the refresh token is sent automatically via the cookie.
	5.	The server returns a new access token and a new refresh token cookie (rotation).
This approach balances security and usability for SPAs, protecting the refresh token while enabling seamless token renewal without exposing sensitive tokens to JavaScript

* Use `ExceptionGroup`s for multiple concurrent exceptions.

* Use all-mpnet-base-v2 for local embeddings model. (Right now, there's no wheels for python 3.13, so using remote model to create embeddings for now).

* Upgrade library versions.

* Not needed for this app, but for history, Temporal database: create shadow tables. No foreign keys.
