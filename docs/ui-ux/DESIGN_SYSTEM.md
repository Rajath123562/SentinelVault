# SentinelVault Design System Specification

**Product**: SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway  
**Tagline**: Analyze Data. Don't Expose It.  
**Version**: 1.0 (Master Enterprise Edition)  
**Reference Alignment**: 16-Screen Enterprise Cybersecurity Board (`media_1793200631528_bb8fd096.jpg`)  

---

## 1. Visual Architecture & Philosophy

SentinelVault employs a **Hybrid Enterprise Cybersecurity Design Language**:
- **Application Shell**: Deep Midnight Navy (`#0B132B` / `slate-950` to `slate-900`) for the persistent left navigation sidebar and header. High contrast, technical sophistication, authoritative zero-trust feel.
- **Analytical Workspace**: Crisp, readable data surfaces (`slate-900` / `slate-950` dark cards with `slate-800` subtle borders and high-contrast typography) preventing eye fatigue while rendering tabular metrics and mathematical evidence cleanly.
- **Semantic Accents**:
  - **Cyan / Teal (`#06B6D4` / `#14B8A6`)**: Privacy mechanics, Differential Privacy badges, noise parameters, cryptographic verification success.
  - **Blue / Indigo (`#2563EB` / `#4F46E5`)**: Primary navigation, active selections, action buttons.
  - **Emerald (`#10B981`)**: Verified cryptographic receipts, clean audit chains, 200 OK successes.
  - **Amber (`#F59E0B`)**: Budget depletion warnings (>60% spent), temporary lockout notices, sensitive field indicators.
  - **Rose (`#F43F5E`)**: Intercepted queries, SQL injection blocks, rate-limit lockouts (HTTP 423), access denied.

---

## 2. Design Tokens

### Color Palette

| Token | Hex / Class | Semantic Role |
| :--- | :--- | :--- |
| `color-bg-base` | `#020617` (`bg-slate-950`) | Global page background |
| `color-bg-sidebar` | `#0B132B` (`bg-slate-900/95`) | Left persistent navigation sidebar |
| `color-bg-card` | `#0F172A` (`bg-slate-900`) | Standard metric, query, and receipt card surface |
| `color-bg-card-subtle`| `#020617` (`bg-slate-950/60`) | Nested code blocks, parameter grids, result containers |
| `color-border-subtle` | `#1E293B` (`border-slate-800`) | Default card and separator borders |
| `color-border-active` | `#06B6D4` (`border-cyan-500`) | Active dataset/field selection border |
| `color-text-primary` | `#F8FAFC` (`text-white`) | Headings, noisy count metrics, primary labels |
| `color-text-secondary`| `#94A3B8` (`text-slate-400`)| Descriptive labels, secondary properties |
| `color-text-muted` | `#64748B` (`text-slate-500`)| Footers, timestamp details, audit hashes |
| `color-privacy-accent`| `#22D3EE` (`text-cyan-400`)| $\epsilon$ parameter, differential privacy badges |
| `color-badge-verified`| `#065F46` / `#34D399` | Ed25519 signature & hash chain verification badges |
| `color-badge-blocked` | `#881337` / `#FDA4AF` | Blocked injection, lockout, access-denied badges |

### Typography

| Scale | Tailwind Class | Usage |
| :--- | :--- | :--- |
| **Display Metric** | `text-4xl font-extrabold font-mono tracking-tight` | Differentially private released counts |
| **Screen Title** | `text-2xl font-bold tracking-tight text-white` | Primary screen headings |
| **Section Header** | `text-lg font-bold text-white` | Card headers, builder titles |
| **Card Metric** | `text-2xl font-bold font-mono text-cyan-400` | KPI cards (Datasets, Budget, Active Users) |
| **Body Regular** | `text-sm text-slate-300 leading-relaxed` | Descriptions, instructions, helper notes |
| **Technical Code** | `text-xs font-mono text-cyan-300 select-all` | Receipt IDs, fingerprints, SQL queries, hashes |
| **Badge / Label** | `text-[10px] font-mono font-bold uppercase` | Status pills (ACTIVE, LOCKED, VERIFIED) |

### Spacing & Grid System

- Container width: `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- Sidebar width: `w-64` (desktop), `w-full` drawer (mobile)
- Metric Card Grid: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`
- Query Builder Grid: `grid grid-cols-1 lg:grid-cols-12 gap-6` (7 cols form + 5 cols live query preview)

---

## 3. Reusable Component Hierarchy

```
App
 ├── ErrorBoundary
 └── AppShell
      ├── Sidebar (Desktop persistent + Mobile slide-over drawer)
      │    ├── BrandLogo ("SentinelVault")
      │    ├── NavigationItems (16 views mapped)
      │    └── UserSessionCard (Active role, Sign out)
      ├── TopBar
      │    ├── MobileMenuToggle (Hamburger)
      │    ├── SystemHealthBadge ("HEALTHY • CONNECTED")
      │    ├── ActiveScreenBreadcrumb
      │    └── IdentityBadge (e.g., "analyst_user (analyst)")
      ├── MainContentContainer
      │    ├── Screen 1: AuthView (Login + Lockout Feedback)
      │    ├── Screen 2: DashboardHomeView (KPIs + Activity)
      │    ├── Screen 3: DatasetSelectionView (Searchable Cards)
      │    ├── Screen 4: QueryBuilderView (Form + Syntax Preview)
      │    ├── Screen 5: QueryResultsView (Release + Uncertainty)
      │    ├── Screen 6: PrivacyBudgetView (Ring Meter + Breakdown)
      │    ├── Screen 7: PrivacyReceiptView (Ed25519 Card)
      │    ├── Screen 8: AuditLogsView (Ledger + Hash Chain)
      │    ├── Screen 9: SecurityEventsAlertsView (SIEM)
      │    ├── Screen 10: UserManagementView (Admin Accounts)
      │    ├── Screen 11: MobileNav (Bottom Bar on Phone)
      │    ├── Screen 12: LoadingModal ("Processing your query...")
      │    ├── Screen 13: AccessDeniedView (RBAC Intercept)
      │    ├── Screen 14: SettingsView (Profile & Diagnostics)
      │    ├── Screen 15: AboutView (Architecture & Mission)
      │    └── Screen 16: NotFoundView (404 Fallback)
      └── Footer (Team UG 59 • Anti-fakery contract)
```

