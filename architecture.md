# Refactor Architecture Plan

## 1. Project Overview
Refactor the AlphaG project into a modern, decoupled web application stored under `./refactor`.
- **Goal**: Create a clean, well-structured, and easy-to-maintain React application backed by a Python API.
- **Languages**: TypeScript (Frontend), Python (Backend).
- **Core Stacks**: React + Vite + Shadcn UI (Frontend), Flask (Backend), Supabase (Auth/DB).

## 2. Directory Structure (`./refactor`)
We will not modify existing files outside `./refactor`.
```
refactor/
├── backend/                # Python Flask API
│   ├── app/
│   │   ├── __init__.py     # App Factory
│   │   ├── api/            # API Blueprints
│   │   │   ├── auth.py     # Auth Middleware wrappers
│   │   │   ├── stock.py    # Stock Analysis endpoints
│   │   │   ├── options.py  # Option Research endpoints
│   │   │   ├── payment.py  # Stripe Payment endpoints
│   │   │   └── user.py     # Profile & History endpoints
│   │   ├── services/       # Business Logic Layer
│   │   │   ├── analysis.py
│   │   │   ├── tiger.py    # Tiger OpenAPI Integration
│   │   │   └── ...
│   │   ├── models/         # SQLAlchemy Models (Shared/Ported)
│   │   └── config.py       # Configuration Class
│   ├── run.py              # Entry Point
│   ├── requirements.txt
│   └── .env                # Copy of credentials
│
├── frontend/               # React + Vite + TypeScript
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/         # Shadcn UI Primitives
│   │   │   ├── layouts/    # MainLayout (Navbar, Footer)
│   │   │   └── features/   # Feature-specific components
│   │   ├── pages/
│   │   │   ├── Home.tsx    # WAS: templates/index.html (Stock Analysis)
│   │   │   ├── Options.tsx # WAS: templates/options.html
│   │   │   ├── Pricing.tsx # Pricing & Subscription
│   │   │   └── Profile.tsx # User Profile, Sub Status, Payment History
│   │   ├── lib/
│   │   │   ├── api.ts      # Axios wrapper with Auth interceptors
│   │   │   └── utils.ts
│   │   ├── locales/        # i18n JSONs (en.json, zh.json)
│   │   ├── theme/
│   │   │   └── colors.ts   # Configurable Main/Secondary colors
│   │   ├── App.tsx         # Routing Logic
│   │   └── main.tsx
│   ├── index.html
│   ├── tailwind.config.js  # Theme Configuration
│   └── vite.config.ts
└── README.md
```

## 3. Detailed Requirements

### A. Frontend (React + TS)
1.  **Framework**: Uses Vite for fast build.
2.  **UI/UX**:
    -   **Library**: **Shadcn UI** for modern, accessible components.
    -   **Theming**: **Configurable Colors** (Main, Secondary, Background, Text) defined in `tailwind.config.js` or CSS variables, accessible via `lib/theme`.
    -   **Respnsiveness**: Mobile-adaptive design.
3.  **Routing** (React Router):
    -   `/` or `/stock` -> **Home** (Stock Analysis).
    -   `/options` -> **Options Research** (Real-time data via Backend).
    -   `/pricing` -> **Pricing** (Subscription Plans).
    -   `/profile` -> **Profile** (User Info, **Subscription Management**, **Payment History**).
4.  **Internationalization (i18n)**:
    -   Support **Chinese / English**.
    -   Use `react-i18next`.
    -   Maintain locale files in `src/locales/`.

### B. Backend (Python Flask)
1.  **Design**: Clean separation of Concerns (Blueprints, Services, Models).
2.  **Auth**:
    -   Trust **Supabase** for user management.
    -   Use `auth_middleware` to verify JWTs from frontend.
    -   **Lazy Sync**: Ensure local user record creation on critical actions (Analysis/Payment).
3.  **Integrations**:
    -   **Stripe**: Handle Checkout & Webhooks.
    -   **Tiger OpenAPI**: Port `new_options_module` logic. Use `tiger_openapi_config.properties` for credentials.

### C. Missing Features to Complete
1.  **Payment History**: Add endpoint `/api/user/transactions` and display table in Profile.
2.  **Subscription Status**: Complete UI in Profile to show Active Plan, Expiry Date, and "Manage Subscription" link (Stripe Portal).
3.  **Consistent Styling**: specific focus on matching the current "Premium" aesthetic but more user-friendly.

## 4. Implementation Steps
1.  **Backend Init**: Setup Flask structure, port models, setup Auth middleware.
2.  **Frontend Init**: `npm create vite@latest`, install `tailwindcss`, `shadcn-ui`.
3.  **Configuration**: Setup `tailwind.config.js` with project colors. Setup i18n.
4.  **Migration**:
    -   Port `home/index.html` logic -> `Home.tsx` + `useStockAnalysis` hook.
    -   Port `options.html` logic -> `Options.tsx` + `useOptionsData` hook.
    -   Implement `Pricing` and `Profile` (with new History feature).
5.  **Verification**: Test full flow (Login -> Analysis -> Subscription -> Upgrade).
