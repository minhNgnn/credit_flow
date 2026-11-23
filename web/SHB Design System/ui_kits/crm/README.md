# SHB CRM UI Kit

Original, from-scratch interpretation of SHB's CRM product (no source codebase or Figma was provided — see root readme.md "Substitutions & flags"). Interactive click-through: sign in → dashboard → click a customer row → profile tabs; sidebar → Deals for the pipeline board.

- `index.html` — app shell, mounts everything
- `Sidebar.jsx`, `TopBar.jsx` — navigation chrome
- `LoginScreen.jsx`, `DashboardScreen.jsx`, `DealsScreen.jsx`, `CustomerProfileScreen.jsx` — screens
- `data.js` — fake sample data (customers, deals, activity)

Composes design-system primitives only (`Card`, `Badge`, `Button`, `Input`, `Tabs`) — no re-implemented UI.
