# Intake Console (dashboard)

Admin dashboard for the Voice AI Patient Registration backend. Next.js 15 (App Router)
static export, served by FastAPI at `/dashboard`.

## Production

```bash
npm ci
npm run build        # writes the static site to out/
```

Copy `out/` to `backend/dashboard_build/` (the Dockerfile does this). FastAPI mounts it at
`/dashboard`, and the dashboard calls the API on the same origin with relative URLs
(`/patients`, `/calls`, `/stats`, …) and the HttpOnly session cookie from `POST /auth/login`.
No secrets are compiled into the bundle.

## Local development

1. Run the backend on port 8000 with CORS enabled for the Next dev server:

   ```bash
   CORS_ORIGINS=http://localhost:3000 uvicorn app.main:app --port 8000
   ```

2. Point the dashboard at it and start the dev server:

   ```bash
   cp .env.example .env.local   # NEXT_PUBLIC_API_BASE=http://localhost:8000
   npm install
   npm run dev
   ```

3. Open http://localhost:3000/dashboard/ and sign in with the backend's `API_KEY`.

`NEXT_PUBLIC_API_BASE` defaults to `""` (same origin). When it is set, requests use
`credentials: "include"` so the session cookie is sent cross-origin in development.

## Routes

Static export has no dynamic segments, so detail pages take query params:

| Route | Page |
| --- | --- |
| `/dashboard/` | Overview |
| `/dashboard/login/` | Sign in |
| `/dashboard/patients/` | Patient list (filters synced to the URL) |
| `/dashboard/patients/new/` | New patient |
| `/dashboard/patients/view/?id=<uuid>` | Patient detail |
| `/dashboard/patients/edit/?id=<uuid>` | Edit patient |
| `/dashboard/calls/` | Call log |
| `/dashboard/calls/view/?id=<uuid>` | Call detail and transcript |

## Scripts

- `npm run dev`: dev server on :3000
- `npm run build`: static export to `out/`
- `npm run lint`: ESLint
- `npm run typecheck`: TypeScript without emitting
