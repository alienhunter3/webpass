# Security review

Reviewed the Flask server (`pywebpass/api_*.py`, `pywebpass/ui.py`, `create_app`) and the browser UI (`pywebpass/static/js/webpass.js`, `pywebpass/templates/index.html`) against this rule: the server must not keep the KeePass master password, or a decrypted database, beyond the request that used it. No session, cache, log, or disk copy of the key. The browser may hold the password only in tab memory, and must be able to drop it.

The CLI (`pywebpass/client/`) was inspected where it stores credentials. It was not redesigned in this change.

## Findings

### High

1. **Stored XSS in the web UI could read the master password.** Severity: high. Location: `pywebpass/static/js/webpass.js` (`setGroupList`, `setSecretList`, `setSecretDisplay`, `setDatabaseDisplay`, attachment and group `<option>` labels). Explanation: group names, titles, usernames, URLs, notes, custom property names and values, and the entry password were assigned with `innerHTML`. A KeePass field containing markup would run in the origin that holds `pw`. Status: **fixed**. Those values are inserted with `textContent`.

2. **Decrypted responses could be written to the browser disk cache.** Severity: high. Location: `GET /api/secret/<uuid>`, `GET /api/secret?fetch_all=true`, `GET /api/file`, and the other API GETs. Explanation: responses that contain entry passwords or the database file did not set `Cache-Control`. A browser or an intermediate cache could store them. Status: **fixed**. API blueprints and the UI page send `Cache-Control: no-store`.

3. **The master password is sent on every request as HTTP Basic, and the sample proxy does not require TLS.** Severity: high. Location: `docs/deployment.md` nginx example; `docs/examples/webpass.ini.example` (`http-socket`). Explanation: Basic auth is base64, not encryption. Anyone on the path can read the master password and any decrypted fields. Status: **not fixed in code**. Deployment has to terminate TLS in front of uWSGI and keep any `http-socket` on `127.0.0.1`. The example comment now says so. Do not run `flask run --debug` on a reachable port: the debugger can show request locals, including the password. Getting started no longer passes `--debug`.

### Medium

4. **A tab stayed logged in until it was closed.** Severity: medium. Location: `pywebpass/static/js/webpass.js` (`pw` global). Explanation: the password and the last opened entry stayed in memory with no idle or absolute limit. Logout also called `forefront('login')` after clearing `pw`, and that helper refuses to switch panels when logged out, so the previous screen and its form fields could stay up. Status: **fixed**. Idle default is 15 minutes (`UI_IDLE_TIMEOUT`, 900 seconds). Absolute default is 8 hours (`UI_ABSOLUTE_TIMEOUT`, 28800 seconds). Both are set in `create_app` and can be overridden in instance `config.py`. Logout and expiry clear the password, the tree, the open entry, form fields, and `webpass*` / `pywebpass*` web-storage keys, then show the login screen. A logout control was already in the menu and still is. The UI does not write the password to `localStorage` or `sessionStorage`. Activity listeners call `checkSessionExpiry()` before changing `lastActivityAt`, so the first mousemove after sleep or a throttled background tab cannot revive an idle session. `focus`, `pageshow`, and `visibilitychange` run the same check. The absolute limit is evaluated before the idle timestamp, so a wake-up event cannot extend a session that has already reached 8 hours.

5. **Attachment upload logged the raw body at DEBUG, and the example config used DEBUG.** Severity: medium (high if that example was copied into production). Location: `pywebpass/api_secret.py` `post_secret_attachment`; `docs/examples/config.py`. Explanation: `request.data` can contain the uploaded file. With `LOG_LEVEL = logging.DEBUG` that landed in the journal. Status: **fixed** in code (those debug lines are gone) and in the example (`logging.INFO`). **Existing instance `config.py` files that still set `logging.DEBUG` should be changed to `logging.INFO` or `logging.WARNING`.**

6. **No Content-Security-Policy.** Severity: medium. Location: `pywebpass/templates/index.html`. Explanation: inline `onclick` handlers mean a strict CSP would blank the UI. The KeePass-field XSS above is fixed; a CSP would be defense in depth and needs the handlers moved to `addEventListener` first. Status: **not fixed**.

7. **Search terms are query strings.** Severity: medium. Location: `GET /api/secret?search=` and `pywebpass/static/js/webpass.js` `getSearchSecrets`. Explanation: proxy access logs record the query string. A search can be a username or a fragment of a note. It is not the master password. Moving search to POST would change the CLI. Status: **not fixed**. `Referrer-Policy: no-referrer` is set so the browser does not copy that URL to other sites.

8. **The CLI can store the master password and a second copy of the database on disk.** Severity: medium. Location: `pywebpass/client/config.py`, `pywebpass/client/constants.py`, `pywebpass/client/command.py`. Explanation: `~/.config/webpass/config.ini` may contain `api_password`. The client also caches the still-encrypted `.kdbx` under `~/.local/share/webpass/cache`. That cache is not the web UI, and the server does not write the key. Status: **not fixed**.

### Low

9. **Failed login left the attempted password in `pw`.** Severity: low. Location: `logIn` in `webpass.js`. Explanation: `pw` was set before the request returned, so a rejected password still counted as logged in. Status: **fixed**. `pw` is set only after the tree request succeeds.

10. **The database upload form copied the master password into a hidden input as soon as the form was shown.** Severity: low. Location: `showDatabaseUploadForm` in `webpass.js`. Explanation: the password sat in the DOM for the whole time that panel was open. The multipart endpoint accepts it because a normal form POST cannot set an `Authorization` header. Status: **fixed**. The field is filled in the submit handler. The browser reads the form after that handler returns, and the field is cleared on the next turn, as well as on logout.

11. **PyKeePass holds the password on the open instance for the rest of the request.** Severity: low. Location: `g.db` in each API `before_request`; previously also `g.pw` in `api_datafile.py`. Explanation: opening the file requires the password, and PyKeePass stores it as `_password` so `save()` can encrypt. There is no Flask session and no disk write of the key. The decrypted XML exists only on that object. Status: **partially fixed**. File upload no longer keeps a second copy on `g.pw`; it reads the request again. `teardown_request` drops `g.db`. CPython will not reliably zero the string. This matches "for that request only."

12. **Unexpected open errors log a traceback.** Severity: low. Location: `before_request` in `api_group.py`, `api_secret.py`, `api_datafile.py`. Explanation: Python tracebacks do not include local variable values. `CredentialsError` is handled separately and its message is `Invalid credentials`, without the password. A future library message could theoretically include it. Status: **not fixed**. Operators still get the traceback. Tests check that a wrong password and an uploaded body are not logged.

13. **`btoa` cannot send a master password outside Latin-1.** Severity: low. Location: `basicAuth` in `webpass.js`. Explanation: the header throws for other characters, so those passwords could not log in. Status: **not fixed** (the browser API is unchanged). The UI now reports the failure instead of sitting on the loading panel.

14. **`/test` is unauthenticated.** Severity: low. Location: `create_app` in `pywebpass/__init__.py`. Explanation: it returns the text `Hello, World!` and no secret. Status: **not fixed**.

15. **The entry editor uses a visible text field.** Severity: low. Location: `#edit_pw_field` in `index.html`. Explanation: the entry password is on screen while editing, which is the current editor. `autocomplete="off"` is set so the browser is less likely to save it. Status: **not fixed** beyond `autocomplete="off"`.

16. **Clipboard copy is not a reliable wipe.** Severity: low. Location: `secretPassClip` and `clearClipboard` in `webpass.js`. Explanation: logout and expiry try to clear the clipboard. Browsers often reject that without a gesture, and a copied entry password can remain. Status: **partially fixed**.

17. **A response still in flight could redraw the vault after logout.** Severity: medium. Location: `loadTree`, `authRequest`, attachment upload, and the file/attachment downloads in `webpass.js`. Explanation: logout cleared memory, then the XHR callback could assign `groups`, `entries`, or `current_secret` and show them on the login screen. Status: **fixed**. Each request records `sessionGeneration`. Logout and expiry increment that counter and abort pending XHRs. A callback returns without touching the UI when the generation changed or the user is logged out. The login request may finish while logged out, and it is still dropped if logout bumped the generation while it was in flight.

## Password preload

The UI loads `GET /api/group/tree` once after login and keeps groups and entry summaries (uuid, title, username, group) in memory. Clicking a group or "all secrets" does not make another request. Refresh reloads that tree. Logout and expiry drop it. There is no timer that refreshes it.

Entry passwords, notes, URLs, and custom properties are not part of the tree. Opening or copying a password still calls `GET /api/secret/<uuid>` with the master password. Search still calls the server, because search also matches notes and attachment names, which are not cached.

Keeping every password in the tab would make copy instant and would avoid a second request. It would also put every decrypted secret in the DOM and the JS heap for the whole session, and it would be one response that contains the entire vault. The master password is already in the tab, so script that can read memory can call the API anyway. Leaving passwords out still limits how many plaintext secrets sit in the page, and it keeps the server's use of the key to the request that actually reads a secret. `fetch_all=true` remains for the CLI and is not used by the web UI.
