# ADR-003: Email-Based Authentication as Primary Auth Method

**Status:** Accepted
**Date:** 2026-03-05
**Deciders:** Brent (product owner)

## Context

bioAF needs an authentication system for its web UI. Options considered:

1. **Google Cloud IAP (Identity-Aware Proxy):** Zero-config SSO for Google Workspace organizations. Requires users to have Google accounts.
2. **Email + password with verification codes:** Universal. Works for any email address. No external identity provider dependency.
3. **OAuth with third-party providers (Auth0, Clerk, etc.):** Feature-rich but adds a dependency and potential cost for an open-source project.

Our target users are small biotech startups. Not all have Google Workspace. Some use Microsoft 365, some use standalone email. Requiring Google accounts would exclude a meaningful segment.

## Decision

Email-based authentication with password + email verification code is the primary auth method. Google Cloud IAP is available as an optional additional layer for teams that want SSO through Google Workspace.

### Flow

**Admin bootstrap:** Admin creates account with email + password during first-time UI setup. Verifies email via one-time code.

**User invitation:** Admin invites users by email address (individual, bulk paste, or CSV import) with role assignment. Invited user receives email with a link to the bioAF instance. User creates password and verifies via one-time email code.

**Steady state:** Users log in with email + password. Sessions are JWT-based (24-hour expiry, refreshable). Password reset via email verification code.

**Optional IAP:** Admin can enable Google Cloud IAP. When enabled, users authenticate via Google first, then bioAF maps their Google identity to their bioAF account by email match.

## Rationale

- **Universality:** Works for any team regardless of their email/identity provider.
- **Simplicity:** No dependency on external identity providers. The entire auth system is self-contained within bioAF.
- **Open-source friendly:** No paid auth service dependency. The auth system runs entirely on infrastructure the user already has (Cloud SQL for user records, SMTP for email delivery).
- **IAP as progressive enhancement:** Teams that want SSO get it, but it's not required. This avoids the GCP project configuration complexity of IAP being mandatory.
- **SMTP dependency is acceptable:** Email delivery is needed anyway for notifications (pipeline complete, backup failure, etc.), so SMTP configuration is not auth-specific overhead.

## Consequences

- bioAF must implement its own auth system: password hashing (bcrypt), JWT issuance/validation, email verification code generation and validation, password reset flow, session management.
- SMTP configuration is needed during admin bootstrap. If admin doesn't have SMTP credentials available, they should be able to skip and use manual invite links (copy-paste URL) as a fallback.
- Password hashes are stored in the PostgreSQL database. JWT signing key is stored in Google Secret Manager.
- Rate limiting must be implemented on login and verification endpoints to prevent brute force.
- The four-role model (Admin, Comp Bio, Bench, Viewer) is enforced by the bioAF API, not by IAP. IAP only handles the authentication layer when enabled.
