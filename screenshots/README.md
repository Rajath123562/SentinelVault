# SentinelVault — Submission Visual Assets & 16-Screen System

This directory contains the visual assets, UI captures, and architectural wireframes for the **SentinelVault: Zero-Trust Privacy-Preserving Analytics Gateway** hackathon submission.

---

## 1. Visual Asset Index

| File | Description | Capture Method |
| :--- | :--- | :--- |
| `01_frontend_dashboard.png` | Live Web Portal (Auth, Zero-Trust Login, Allowlist Rules) | Headless Browser (Edge) |
| `02_backend_swagger_api.png` | FastAPI Interactive Swagger UI (`/docs`) | Headless Browser (Edge) |
| `03_terminal_test_execution.png` | Automated Test Suite Execution (94 pytest + 9 vitest + 11 live) | Pixel-perfect Terminal Render |
| `04_privacy_receipt_card.png` | Verifiable Cryptographic Privacy Receipt Card | Cryptographic Proof Visualizer |

---

## 2. 16-Screen Master Reference Board Mapping

Conforms strictly to the 16-screen master specification (`media_1793200631528_bb8fd096.jpg`):

1. **Login Page** (`AuthView.tsx`): Zero-trust credentials, 5-attempt lockout notification, PBKDF2.
2. **Dashboard (Home)** (`DashboardHomeView.tsx`): 4 KPI cards, Recent Activity ledger, Quick Actions.
3. **Dataset Selection** (`DatasetSelectionView.tsx`): Searchable cards for Health & Financial data with chips.
4. **Query Builder** (`QueryBuilderView.tsx`): Guided parameter controls + live syntax preview box `SELECT COUNT(DISTINCT ...)`.
5. **Query Results** (`QueryResultsView.tsx`): Laplace noisy count card, budget deduction metrics, results table, receipt link.
6. **Privacy Budget** (`PrivacyBudgetView.tsx`): Circular SVG ring meter, micro-epsilon ledger table.
7. **Privacy Receipt** (`PrivacyReceiptViewer.tsx`): Verifiable receipt card with Ed25519 digital signature and JSON export.
8. **Audit Logs** (`AuditEvaluationView.tsx`): SHA-256 hash chain verification, filter dropdown, and log records.
9. **Security Events & Alerts** (`SecurityEventsView.tsx`): SIEM event ledger and alerts tab with severity badges.
10. **Role Management (Admin)** (`UserManagementView.tsx`): Admin user management & lockout release.
11. **Responsive Mobile View** (`Sidebar.tsx`, `App.tsx`): Mobile drawer and bottom quick-tabs.
12. **Loading & Error Modal** (`LoadingModal.tsx`): "Processing your query..." spinner modal.
13. **Unauthorized Access Attempt** (`AccessDeniedView.tsx`): Shield access-denied screen on permission violations.
14. **Settings** (`SettingsView.tsx`): Profile, security, TOTP MFA, and system health status.
15. **About / Info** (`AboutView.tsx`): Brand mission and 3 trust pillars.
16. **404 Page** (`NotFoundView.tsx`): "Page Not Found" fallback screen.
