# SA-10 à SA-18 - Modèle relationnel et référentiels

## Périmètre livré

Le schéma SQLAlchemy du backend réutilise la table `users` de SA-27/SA-28. Il ajoute les profils candidats, le catalogue IIT/ISB, les candidatures et recommandations, les sources documentaires, les segments de texte et l’historique de synchronisation.

```mermaid
erDiagram
    USERS ||--o| CANDIDATE_PROFILES : possede
    USERS ||--o{ CANDIDATE_APPLICATIONS : depose
    PROGRAMS ||--o{ CANDIDATE_APPLICATIONS : concerne
    CANDIDATE_APPLICATIONS ||--o{ RECOMMENDATIONS : recoit
    PROGRAMS ||--o{ RECOMMENDATIONS : propose
    USERS o|--o{ RECOMMENDATIONS : valide
    USERS o|--o{ DOCUMENT_SOURCES : depose
    DOCUMENT_SOURCES ||--o{ DOCUMENT_CHUNKS : contient
    DOCUMENT_SOURCES ||--o{ DOCUMENT_SYNC_RUNS : synchronise
    USERS ||--o{ REFRESH_SESSIONS : authentifie
    USERS ||--o{ AUDIT_EVENTS : agit

    USERS {
        uuid id PK
        string email UK
        string role
        boolean is_active
    }
    CANDIDATE_PROFILES {
        uuid id PK
        uuid user_id FK,UK
        string current_education
        int graduation_year
        string target_institution
    }
    PROGRAMS {
        uuid id PK
        string institution
        string name
        string level
        boolean is_published
        boolean is_demo
    }
    CANDIDATE_APPLICATIONS {
        uuid id PK
        uuid candidate_user_id FK
        uuid program_id FK
        string academic_year
        string status
        int version
    }
    RECOMMENDATIONS {
        uuid id PK
        uuid application_id FK
        uuid program_id FK
        decimal score
        string status
        uuid reviewed_by_user_id FK
    }
    DOCUMENT_SOURCES {
        uuid id PK
        string institution
        string storage_key
        string checksum_sha256
        int version
        string status
    }
    DOCUMENT_CHUNKS {
        uuid id PK
        uuid document_source_id FK
        int chunk_index
        text content
        json metadata_json
    }
    DOCUMENT_SYNC_RUNS {
        uuid id PK
        uuid document_source_id FK
        string idempotency_key UK
        string status
        int processed_count
    }
```

## Règles d’intégrité

- Les rôles d’authentification existants restent attachés à `users`; aucun second référentiel de comptes n’est créé.
- Un profil candidat est unique par compte. Une candidature référence un compte candidat et une formation existante.
- Les formations et documents distinguent `IIT` et `ISB`; les statuts et niveaux sont contraints par la base.
- Les recommandations sont rattachées à une candidature et une formation; un score, s’il existe, doit rester entre 0 et 1. La validation humaine est conservée séparément de la recommandation proposée.
- Les sources documentaires gardent leur provenance, version, checksum et état de publication. Les chunks et synchronisations dépendent de la source.
- Les formations de démonstration portent `is_demo=true` et `is_published=false`; elles ne sont jamais destinées aux réponses candidates ni à l’index RAG public.
- Les fichiers originaux ne sont pas stockés dans PostgreSQL : `storage_key` référence un stockage privé. Les embeddings vectoriels sont laissés à l’intégration RAG ultérieure; PostgreSQL est préparé avec pgvector.

## Migrations et données de démonstration

Les migrations Alembic sont dans `backend/migrations`. Pour initialiser le schéma :

```powershell
cd backend
docker compose up -d db
python -m alembic upgrade head
python -m app.seed_demo
```

Le seed peut être relancé sans doublonner les formations. Il n’insère ni compte administrateur ni mot de passe de démonstration. Les intitulés de démonstration sont fictifs et non publiés jusqu’à leur remplacement par des données validées par l’IIT et l’ISB.