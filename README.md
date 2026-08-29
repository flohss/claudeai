# claudeai

Made with Claude

## Navigation par date dans les archives Internet

Clone de la Wayback Machine : on entre une URL, on voit un calendrier des
instantanés archivés par archive.org, et on navigue dans l'historique par
année/mois/jour.

- `server/` — API Express (TypeScript) qui interroge l'API CDX d'archive.org
  et regroupe les instantanés par date.
- `client/` — Interface React (TypeScript, Vite) avec calendrier de
  navigation et visualisation de l'instantané choisi.

### Lancer en local

```bash
# Terminal 1
cd server && npm install && npm run dev

# Terminal 2
cd client && npm install && npm run dev
```

Puis ouvrir http://localhost:5173 et entrer une URL (ex: `example.com`).
