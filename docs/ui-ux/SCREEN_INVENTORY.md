# SentinelVault Screen Inventory & Functional Mapping

**Reference**: 16-Screen Master Reference Board (`media_1793200631528_bb8fd096.jpg`)  
**Standard**: Real Backend Connection • Zero Mocks in Production • Authentic State  

---

| # | Screen Name | Component | Backend Route / Contract | Role Access | Real Functional Status |
| :- | :--- | :--- | :--- | :--- | :--- |
| **01** | **Login Page** | `AuthView.tsx` | `POST /api/auth/login` | Anonymous | **VERIFIED WORKING** (PBKDF2-HMAC, 5-attempt lockout banner) |
| **02** | **Dashboard (Home)** | `DashboardHomeView.tsx` | `/api/system/status`, `/api/datasets`, `/api/budget/*` | All Authenticated | **VERIFIED WORKING** (Live KPIs, recent activity ledger) |
| **03** | **Dataset Selection** | `DatasetSelectionView.tsx` | `GET /api/datasets` | `dataset.metadata.read` | **VERIFIED WORKING** (Health & financial cards, metadata) |
| **04** | **Query Builder** | `QueryBuilderView.tsx` | `POST /api/queries/preview` | `dataset.query.execute` | **VERIFIED WORKING** (Live SQL syntax preview, $\Delta f = 1.0$) |
| **05** | **Query Results** | `QueryResultsView.tsx` | `POST /api/queries/run` | `dataset.query.execute` | **VERIFIED WORKING** (Noisy Laplace count, budget deducted) |
| **06** | **Privacy Budget** | `PrivacyBudgetView.tsx` | `GET /api/budget/{id}` | All Authenticated | **VERIFIED WORKING** (Circular ring meter, micro-epsilon ledger) |
| **07** | **Privacy Receipt** | `PrivacyReceiptView.tsx` | `GET /api/receipts/{id}` | `receipt.read.own` / `auth` | **VERIFIED WORKING** (Ed25519 digital signature, JSON export) |
| **08** | **Audit Logs** | `AuditLogsView.tsx` | `GET /api/audit/verify` | `audit.verify` | **VERIFIED WORKING** (SHA-256 hash chain verification) |
| **09** | **Security Events & Alerts** | `SecurityEventsAlertsView.tsx`| `/api/security/events`, `/alerts`| `security.events.read` | **VERIFIED WORKING** (SIEM event table, severity filters) |
| **10** | **User Management** | `UserManagementView.tsx` | `GET /api/users`, `POST /unlock` | `user.manage` (Admin/Steward)| **VERIFIED WORKING** (User list, lockout release) |
| **11** | **Responsive Mobile View** | `MobileNav.tsx`, `AppShell.tsx`| Internal state | All Authenticated | **VERIFIED WORKING** (Bottom navigation bar, drawer) |
| **12** | **Loading & Error Modal** | `LoadingModal.tsx`, `ErrorAlert.tsx`| Async execution hook | All Authenticated | **VERIFIED WORKING** ("Processing your query..." spinner) |
| **13** | **Access Denied** | `AccessDeniedView.tsx` | HTTP 403 response interceptor | Blocked roles | **VERIFIED WORKING** (Shield icon, permission violation notice) |
| **14** | **Settings & Diagnostics** | `SettingsView.tsx` | `/api/system/status`, `/ready` | All Authenticated | **VERIFIED WORKING** (User profile, TOTP MFA, runtime status) |
| **15** | **About / Trust Pillars** | `AboutView.tsx` | Static / system contracts | Public & Authenticated | **VERIFIED WORKING** (Zero-trust gateway architecture overview) |
| **16** | **404 Not Found Page** | `NotFoundView.tsx` | Fallback router | All | **VERIFIED WORKING** (Illustration, "Page Not Found", home action) |

