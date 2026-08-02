# Universeaty Dashboard — Frontend

React 19 + TypeScript admin frontend for the Universeaty scraper, built with Vite 8,
Tailwind CSS v4, shadcn/ui components, recharts, and sonner. Designed to match the main
universeaty.ca app's dark, monochrome, glassy look (Montserrat, `#0a0a0a` base, OKLCH tokens).

## Scripts

```bash
npm run dev          # Vite dev server
npm run build        # tsc type-check + build → ../backend/static (served by Flask)
npm run lint         # ESLint
npm run lint:fix
npm run format       # Prettier --write
npm run format:check
```

## Conventions

- All shadcn/ui primitives live in `src/components/ui/` (copy from `frontend/src/components/ui/`
  in the main app) and are ignored by ESLint (generated code).
- Tailwind tokens in `src/index.css` mirror the main app's `:root`/`.dark` blocks — keep them in
  sync when the main app's theme changes.
- The API base is `''` (same origin) in production builds and `http://192.168.0.43:8085` in dev
  (override with `VITE_DASHBOARD_API_URL`).
- Log lines are parsed client-side by `src/lib/logs.ts` against the scraper's
  `LOG_FORMAT` (`asctime - level - logger:lineno - thread - message`).

## Dependencies

| Purpose       | Packages                                                            |
| ------------- | ------------------------------------------------------------------- |
| UI primitives | `@radix-ui/*`, `class-variance-authority`, `clsx`, `tailwind-merge` |
| Icons         | `lucide-react`                                                      |
| Charts        | `recharts`                                                          |
| Toasts        | `sonner`                                                            |
| Styling       | `tailwindcss`, `@tailwindcss/vite`, `tw-animate-css`                |
| Tooling       | `typescript`, `eslint`, `prettier`, `lint-staged`                   |
