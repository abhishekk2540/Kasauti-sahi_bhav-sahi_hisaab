# Kasauti frontend

Next.js 15 (App Router) + TypeScript + Tailwind. Talks to the FastAPI backend over REST and Server-Sent Events.

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
npm run typecheck && npm run build
```

Structure: `app/(app)/*` authenticated pages behind `components/Shell.tsx` (redirects to /login without a session),
`lib/api.ts` fetch wrapper + SSE chat reader, `lib/auth.tsx` session (JWT in localStorage), `components/` shared UI.
The AI assistant never changes data itself: it shows a confirmation card and the change happens only on "Confirm".
