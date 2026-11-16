# Matrice des rôles et droits

## Rôles du système

- Candidat / futur étudiant
- Responsable académique IIT
- Responsable académique ISB
- Responsable entretien
- Direction
- Administrateur de la plateforme

## Matrice des permissions

| Fonctionnalité | Candidat | Responsable académique IIT | Responsable académique ISB | Responsable entretien | Direction | Administrateur |
|---|---:|---:|---:|---:|---:|---:|
| Consulter les formations IIT et ISB | Oui | Oui | Oui | Oui | Oui | Oui |
| Démarrer une conversation anonyme | Oui, sans compte | Non | Non | Non | Non | Non |
| Consulter et gérer son propre profil | Oui | Non | Non | Non | Non | Selon besoin de support |
| Recevoir et comparer des recommandations | Oui | Oui, périmètre IIT | Oui, périmètre ISB | Oui, dossiers d’entretien | Statistiques agrégées | Configuration des règles |
| Consulter les candidats orientés | Non | Oui, IIT | Oui, ISB | Oui, prêts pour entretien | Indicateurs globaux | Selon besoin d’administration |
| Confirmer ou ajuster une recommandation | Non | Oui, IIT | Oui, ISB | Non | Non | Non |
| Gérer les informations des formations | Non | Oui, IIT | Oui, ISB | Non | Non | Oui, administration |
| Effectuer et compléter une préinscription | Oui, son dossier | Non | Non | Non | Non | Non |
| Passer un QCM et consulter ses réponses | Oui, son QCM | Oui, candidats de son périmètre | Oui, candidats de son périmètre | Oui, candidats prêts pour entretien | Statistiques agrégées | Configurer les modèles |
| Gérer un rendez-vous et une invitation | Consulter / confirmer le sien | Non | Non | Oui | Non | Configuration technique |
| Saisir le résultat d’un entretien | Non | Non | Non | Oui | Non | Non |
| Demander un complément ou transmettre un dossier | Non | Non | Non | Oui | Non | Non |
| Consulter le tableau de bord et les conversions | Non | Statistiques de son périmètre | Statistiques de son périmètre | Suivi des entretiens | Oui, global | Indicateurs techniques |
| Gérer comptes, rôles et droits | Non | Non | Non | Non | Non | Oui |
| Gérer campagnes, workflow, sources RAG et intégrations | Non | Non | Non | Non | Non | Oui |
| Consulter journaux et erreurs techniques | Non | Non | Non | Non | Indicateurs agrégés | Oui |

## Règles de sécurité et d’accès

### Candidat / futur étudiant
- Peut consulter les informations publiques et dialoguer sans compte.
- Une fois identifié, peut consulter et modifier uniquement son profil, sa préinscription, son QCM et son rendez-vous.
- Ne peut pas accéder aux dossiers des autres candidats ni aux outils internes.

### Responsables académiques IIT et ISB
- L’accès aux candidats, recommandations, QCM et statistiques est limité au périmètre de leur établissement.
- Peuvent confirmer ou ajuster les recommandations et gérer les informations des formations de leur périmètre.
- Ne peuvent pas administrer les comptes et paramètres globaux.

### Responsable entretien
- Accède aux dossiers préparés pour entretien, au résumé pertinent, au QCM et à ses réponses.
- Peut gérer le rendez-vous, saisir le résultat et demander un complément ou transmettre le dossier.
- Ne dispose pas des droits d’administration globale.

### Direction
- Accède aux indicateurs de pilotage et aux statistiques de conversion globales.
- L’accès aux détails personnels des candidats n’est pas présumé; il doit être explicitement justifié par les besoins métier.

### Administrateur de la plateforme
- Gère les comptes, rôles, droits, campagnes, paramètres du workflow, sources RAG et intégrations.
- Consulte les journaux et erreurs nécessaires à l’exploitation.
- Les droits techniques ne confèrent pas automatiquement le pouvoir de prendre les décisions académiques ou d’admission.

### Composants IA
- Le LLM, le RAG et les outils agentiques ne sont pas des rôles utilisateurs.
- Ils n’accèdent qu’aux données nécessaires à leur tâche et ne prennent pas de décision officielle à la place des acteurs humains.

## Critères de validation

- Aucun acteur ne doit avoir accès aux données d’un autre utilisateur sans autorisation explicite.
- Les actions sur un dossier personnel et les fonctions internes doivent être protégées par authentification et contrôle d’accès.
- L’accès des responsables académiques est cloisonné entre les périmètres IIT et ISB.
- Une conversation commencée sans compte est traitée comme un mode d’accès du candidat et reste temporaire tant qu’elle n’est pas rattachée selon les règles de consentement.
- Les changements de recommandation, de résultat d’entretien et d’étape du dossier sont attribuables et traçables.
- Les décisions officielles restent soumises à une validation humaine.

## Livrable attendu

Cette matrice sert de référence pour la conception des APIs, le système d’authentification et la gestion des rôles dans le backend.
