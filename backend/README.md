# Backend SmartCampus AI

Socle SA-27/SA-28 et SA-10 à SA-18 : authentification et rôles, catalogue académique, profils et candidatures, recommandations, sources documentaires et synchronisations.

## Démarrage local

Depuis le dossier `backend` :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.bootstrap_admin
uvicorn app.main:app --reload
```

L’API est disponible sur `http://127.0.0.1:8000`; sa documentation OpenAPI se trouve sur `/docs`. L’inscription publique crée uniquement des comptes `candidate`. Le premier administrateur est créé par la commande locale de bootstrap, qui demande le mot de passe sans l’afficher. Les rôles internes ne peuvent ensuite être attribués que par un administrateur authentifié.

Pour lancer les tests : `python -m pytest` depuis `backend`.

## Configuration et limites

Les paramètres sont lus depuis les variables préfixées `SMARTCAMPUS_`; `.env.example` cible le PostgreSQL local. `docker compose up -d db` démarre PostgreSQL 16 avec pgvector. Pour le développement sans Docker, utiliser `SMARTCAMPUS_DATABASE_URL=sqlite:///./smartcampus.db`. Le schéma automatique n’est destiné qu’au développement : en production, désactiver `SMARTCAMPUS_AUTO_CREATE_TABLES` et appliquer `alembic upgrade head`. Activer `SMARTCAMPUS_COOKIE_SECURE` et définir un secret JWT aléatoire d’au moins 32 caractères en production.

Les access tokens JWT expirent après 15 minutes. Les refresh tokens aléatoires sont stockés sous forme d’empreinte, placés en cookie HttpOnly, renouvelés à chaque utilisation et révoqués à la déconnexion. Le renouvellement exige le jeton CSRF dans `X-CSRF-Token`. Les rôles et l’état du compte sont relus en base à chaque requête protégée; un rôle modifié prend donc effet immédiatement.

## Données, migrations et démo

Le modèle SQLAlchemy est dans `app/models.py`. Il comprend les utilisateurs existants, les profils candidats, programmes IIT/ISB, candidatures, recommandations, sources et chunks documentaires, exécutions de synchronisation, sessions de renouvellement et audit. Les sources documentaires ne sont pas publiées par défaut; seules les sources validées doivent être exposées au RAG.

Après avoir démarré PostgreSQL, depuis le dossier `backend` :

```powershell
python -m alembic upgrade head
python -m app.seed_demo
```

Les formations créées par `seed_demo` sont fictives, marquées `is_demo=true` et non publiées; elles ne représentent pas le catalogue officiel. Le script est idempotent et ne crée aucun compte ni mot de passe de démonstration.

Ce socle n’implémente pas encore la vérification d’adresse email, la récupération de mot de passe, les limites distribuées de connexion, ni les rôles académiques cloisonnés par attribut d’établissement. En production, protéger l’API contre les tentatives répétées au reverse proxy ou avec un service de limitation partagé.