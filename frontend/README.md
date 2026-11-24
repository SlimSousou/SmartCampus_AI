# SmartCampus AI — Frontend

Frontend React/Vite du projet SmartCampus AI. Il couvre l’initialisation locale (SA-6, SA-8, SA-9), le catalogue public IIT/ISB et le parcours visiteur (SA-23 à SA-26, SA-29).

## Développement local

Depuis ce dossier :

```powershell
npm ci
npm run dev
```

Vite démarre sur `http://localhost:3000`. Les appels `/api` sont proxifiés vers le backend sur `http://localhost:8000`; démarrez le Compose depuis la racine du projet avant de tester le catalogue.

Pour démarrer toute la stack avec Docker, depuis la racine du projet :

```powershell
cd "C:\Users\USER\Documents\programme_Genie_Info\3eme annee\IA generative\SmartCampus AI"
docker compose up --build -d
docker compose ps
```

Ouvrez ensuite `http://localhost:3000` pour le frontend et `http://localhost:8000/docs` pour la documentation interactive du backend. Le proxy Nginx du frontend transmet `/api/*` au service `api` sur le réseau Compose.

## Vérification et production

```powershell
npm run build
npm run preview
```

Le build utilise TypeScript et Vite. Le `Dockerfile` produit une image Nginx avec le routage SPA et le proxy `/api` vers le service backend.

## Parcours visiteur

Le widget de conversation est disponible sans compte depuis l’accueil. Un identifiant de session et les derniers échanges sont conservés temporairement dans `localStorage`; aucun message visiteur n’est envoyé au backend avant connexion. Après connexion, les messages précédents sont rejoués dans la conversation candidate afin d’associer la mémoire temporaire au compte. Le catalogue et les fiches de formations restent consultables sans compte.
