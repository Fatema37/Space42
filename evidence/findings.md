| # | Sev | OWASP | Area | Test | Finding (secure behaviour not met) |
|---|---|---|---|---|---|
| 1 | low | API8 | auth | `TestLogin::test_invalid_expiry_rejected_with_400` | invalid expiresInMins returns 500 instead of a 400 validation error |
| 2 | low | API8 | auth | `TestMe::test_invalid_token_rejected_with_401` | invalid token returns 500 'invalid token' instead of 401 |
| 3 | medium | API2 | auth | `TestMe::test_refresh_token_not_accepted_as_access_token` | a refresh token is accepted as an access token |
| 4 | medium | API2 | auth | `TestRefresh::test_access_token_not_accepted_as_refresh_token` | an access token is accepted as a refresh token |
| 5 | medium | API2 | auth | `TestCookieSession::test_cookie_has_samesite_attribute` | session cookies have no SameSite attribute |
| 6 | medium | API2 | auth | `TestCookieSession::test_cookie_alone_cannot_change_data` | the session cookie alone authorizes state-changing requests (no CSRF protection) |
| 7 | medium | API8 | auth | `TestCookieSession::test_cors_does_not_allow_credentials_from_any_origin` | CORS reflects any origin with Access-Control-Allow-Credentials: true |
| 8 | high | API3 | exposure | `TestUserResponses::test_public_user_list_has_no_sensitive_fields` | public user list exposes password/ssn/ein/bank/crypto |
| 9 | high | API3 | exposure | `TestUserResponses::test_public_single_user_has_no_sensitive_fields` | public single-user record exposes password/ssn/ein/bank/crypto |
| 10 | high | API3 | exposure | `TestUserResponses::test_me_has_no_password_even_for_owner` | /auth/me returns the caller's own password |
| 11 | medium | API5 | auth | `test_security_matrix[R03]` | writes must require authentication |
| 12 | medium | API5 | auth | `test_security_matrix[R04]` | deletes must require authentication |
| 13 | high | API1 | ownership | `test_security_matrix[R06]` | a user must not read another user's record |
| 14 | high | API1 | ownership | `test_security_matrix[R08]` | a user must not modify another user's record |
| 15 | high | API1 | ownership | `test_security_matrix[R09]` | a user must not delete another user's record |
| 16 | high | API1 | ownership | `test_security_matrix[R11]` | a user must not read another user's carts |
| 17 | high | API3 | rbac | `test_security_matrix[R12]` | a user must not escalate their own role |
| 18 | high | API5 | auth | `test_security_matrix[R19]` | account creation must require authentication (anyone can create an admin) |
| 19 | high | API1 | ownership | `test_security_matrix[R20]` | a user's carts must not be readable without authentication |
| 20 | medium | API3 | rbac | `test_security_matrix[R21]` | identity fields such as id must be immutable |
| 21 | medium | API3 | rbac | `test_security_matrix[R22]` | a user must not take another user's username |
