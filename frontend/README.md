# Hoard frontend

Vue 3, TypeScript, Vite, and Vuetify power Hoard's campaign UI.

```sh
npm install
npm run dev
```

Django serves the SPA HTML at `http://localhost:8000`; Vite supplies modules
and HMR from port 5173. Run `npm run build` to create `dist/`; django-vite
discovers Vite's manifest and Django serves the built SPA in production.
