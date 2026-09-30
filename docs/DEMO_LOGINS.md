# Demo Officer Accounts — Uttarkashi Pilot

> [!WARNING]
> **CRITICAL SECURITY NOTICE FOR PRODUCTION DEPLOYMENT**  
> The credentials documented below are **DEMO / PILOT PASSWORDS ONLY** used for evaluation, testing, and Hackathon demonstration (SIH 2026, PS 26192).
> **These accounts and passwords MUST be changed or rotated immediately before any staging or production deployment.**
>
> In production environments:
> - Passwords must comply with Indian CERT-In guidelines (minimum 12 alphanumeric characters with special symbols).
> - Production passwords are encrypted using **bcrypt** with a minimum work factor of 12 rounds.
> - Multi-Factor Authentication (MFA / OTP via SMS / Sandes / Gov NIC email) should be enabled.
> - Secrets like `JWT_SECRET` must be rotated through AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault.

---

## 1. Seeded Officer Accounts (Uttarkashi District Pilot)

| Name | Role | District / Unit | Official Email / Identifier | Phone Number | Demo Password | System Privileges |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dr. Rajesh Sharma** | `admin` | Uttarkashi | `ddmo.uttarkashi@uk.gov.in` | `+919412000001` | `Uttarkashi@2026` | Full administrative control, threshold adjustments, emergency alerts, user management, audit logs. |
| **Maj. Vikram Negi** | `officer` | Uttarkashi (14th Bn NDRF) | `ndrf.uttarkashi@gov.in` | `+919412000002` | `NDRF#Rescue2026` | Emergency alert dispatch, citizen report verification, evacuation routing approval. |
| **Pooja Rawat** | `officer` | Bhatwari Block | `bdo.bhatwari@uk.gov.in` | `+919412000003` | `Bhatwari@2026` | Citizen report ground-truthing, village threshold calibration, local warning dispatch. |

---

## 2. Authentication Architecture

- **Hashing Algorithm:** `bcrypt` with salt rounds (plain text passwords are never stored or logged).
- **Authentication Endpoints:**
  - `POST /api/v1/auth/login`: Accepts either official email or phone number + password. Returns JWT access token (15-minute expiry) and httpOnly refresh token cookie.
  - `POST /api/v1/auth/refresh`: Silently refreshes access token using the httpOnly cookie without user disruption.
  - `POST /api/v1/auth/logout`: Invalidates session and clears cookies.
  - `GET /api/v1/auth/me`: Retrieves current officer profile and RBAC role.
- **Brute Force Protection:** In-memory rate limiter enforces maximum 5 failed attempts per 10 minutes per IP before lockout.
- **Token Security:** Frontend stores JWT access token strictly in-memory (never in plain `localStorage`) with automatic silent refresh.

---

## 3. How to Log In via the Web Interface

1. Open the Hyper-Local FlashFlood Prediction Command Center.
2. In the top navigation header, click the **"Officer Login"** button (or trigger any protected action such as "DISPATCH ALERT" or "VET GROUND TRUTH").
3. In the authentication modal:
   - Click one of the **Quick Demo Profile** buttons (DDMO Uttarkashi, NDRF Commander, or BDO Bhatwari) to auto-fill credentials, OR manually enter the email and password from the table above.
   - Click **"Authenticate Officer"**.
4. Upon authentication:
   - The header displays the officer's name, role, and district with an active status badge.
   - A dedicated **"Logout"** button is made available.
   - All gated officer functions (Dispatch Alert, Verify/Reject Reports, Calibrate Thresholds) become immediately accessible.
