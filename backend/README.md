# Backend SmartCampus AI

Socle SA-27/SA-28 et SA-10 à SA-18 : authentification et rôles, catalogue académique, profils et candidatures, recommandations, sources documentaires et synchronisations.

## Démarrage Docker autonome

Depuis la racine du projet :

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

L’API est disponible sur `http://127.0.0.1:8000`, la documentation sur `/docs` et l’état sur `/api/v1/health`. Compose construit le backend, attend PostgreSQL, applique `alembic upgrade head`, puis démarre Uvicorn. La base PostgreSQL reste dans un volume Docker persistant.

Pour voir les migrations ou appliquer le seed de démonstration :

```powershell
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m app.seed_demo
docker compose down
```

Pour supprimer aussi les données PostgreSQL locales :

```powershell
docker compose down -v
```

## Démarrage local sans Docker

Depuis le dossier `backend` :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
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

Ce socle n’implémente pas encore la vérification d’adresse email, la récupération de mot de passe ni les limites distribuées de connexion. En production, protéger l’API contre les tentatives répétées au reverse proxy ou avec un service de limitation partagé.

## Catalogue et informations officielles (SA-19 à SA-22)

La documentation interactive `/docs` décrit les paramètres et les réponses. Les routes suivantes sont préfixées par `/api/v1` :

- `/programs` : formations, recherche, filtres par établissement et niveau, pagination et publication ;
- `/specialties`, `/curricula` et `/subjects` : spécialités, programmes pédagogiques et matières ;
- `/fees`, `/payment-terms` et `/admission-conditions` : tarifs, modalités de paiement et conditions d’admission ;
- `/programs/{program_id}/official-info` : synthèse des informations officielles actuellement valides.

Les lectures publiques n’exposent que les formations publiées et non fictives, ainsi que les informations officielles publiées, actives et dans leur période de validité. Les informations officielles sont créées en brouillon ; utilisez `POST /fees/{id}/publish`, `POST /payment-terms/{id}/publish` ou `POST /admission-conditions/{id}/publish` pour les publier. Une modification de contenu publié le remet en brouillon. Les actions `draft` et `archive` sont également disponibles. Une formation doit elle-même être publiée via `POST /programs/{id}/publish` avant la publication de ses informations officielles.

Les écritures sont réservées à l’administrateur ou au responsable académique de l’établissement concerné (`academic_iit` ou `academic_isb`). Les responsables peuvent consulter leurs brouillons avec `include_inactive=true`. Les données de démonstration ne constituent pas des tarifs officiels ; elles nécessitent une validation et une publication par les responsables compétents.
