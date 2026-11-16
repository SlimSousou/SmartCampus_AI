# Document de sprint 1 - SmartCampus AI

## 1. Contexte du projet

Le projet SmartCampus AI vise à développer une plateforme agentique d’orientation universitaire. Les candidats ou futurs étudiants consultent les programmes de l’IIT et de l’ISB, échangent avec l’assistant en français, dialecte tunisien ou Arabizi, puis peuvent effectuer une préinscription et suivre leur parcours jusqu’au rendez-vous.

Le système doit permettre :
- la consultation du catalogue académique,
- une expérience de conversation sans compte,
- la création d’un compte candidat,
- la soumission d’une candidature,
- la supervision des recommandations par les responsables académiques IIT et ISB,
- la préparation et le suivi des entretiens par le responsable entretien,
- le pilotage des conversions par la Direction,
- l’intégration d’un modèle LLM pour le support conversationnel.

## 2. Objectifs du sprint 1

Le sprint 1 vise à poser les fondations techniques et fonctionnelles du projet.

### Objectifs principaux
- définir les acteurs et processus métier,
- concevoir l’architecture technique,
- définir les APIs et les règles d’accès,
- initialiser le backend et le frontend,
- mettre en place la base de données et les migrations,
- préparer le socle pour l’intégration du LLM.

## 3. Backlog du sprint 1

### Epic 1 : Architecture et initialisation
- SA-1 : Architecture et initialisation
- SA-2 : Conception de l’architecture technique et définition des APIs
- SA-3 : Définir les acteurs et les processus métier
- SA-4 : Définir l’architecture technique du système
- SA-5 : Concevoir les API et les règles d’accès

### Epic 2 : Données relationnelles et référentiels
- SA-10 : Données relationnelles et référentiels
- SA-11 : Modèle relationnel métier
- SA-12 : Concevoir les tables du catalogue académique
- SA-13 : Concevoir les tables des utilisateurs et des candidatures
- SA-14 : Concevoir les tables de gestion des documents et de synchronisation
- SA-15 : Base PostgreSQL et migrations
- SA-16 : Installer et configurer PostgreSQL
- SA-17 : Créer les tables et les relations de la base de données
- SA-18 : Alimenter la base avec des données de démonstration

### Epic 3 : Gestion des visiteurs sans compte et de la mémoire conversationnelle
- SA-23 : Gestion des visiteurs sans compte et de la mémoire conversationnelle
- SA-24 : Permettre une conversation sans création de compte
- SA-25 : Développer la gestion des sessions des visiteurs
- SA-26 : Mettre en place la mémoire temporaire des conversations
- SA-27 : Mettre en place l’authentification et la gestion des rôles utilisateurs
- SA-28 : Développer l’authentification et la gestion des rôles
- SA-29 : Associer une conversation invitée à un compte candidat

### Epic 4 : Sélection et intégration du LLM
- SA-30 : Sélection et intégration du LLM
- SA-31 : Évaluer et sélectionner le modèle LLM
- SA-32 : Préparer les questions pour évaluer les LLM
- SA-33 : Comparer les performances des modèles LLM
- SA-34 : Évaluer la compréhension du dialecte tunisien et de l’Arabizi
- SA-35 : Intégrer le LLM au Backend et gérer les conversations
- SA-36 : Connecter le LLM au Backend
- SA-37 : Intégrer la mémoire conversationnelle au LLM
- SA-38 : Tester le fonctionnement du dialogue avec le LLM

## 4. Répartition de l’équipe

### Membre 1 – Architecture et sécurité
- SA-3 : Définir les acteurs et les processus métier
- Acteurs de référence : candidat / futur étudiant, responsable académique IIT, responsable académique ISB, responsable entretien, Direction et administrateur de la plateforme.
- Les composants IA sont des composants internes; « visiteur » décrit un mode de conversation sans compte et non un acteur métier distinct.
- SA-4 : Définir l’architecture technique du système
- SA-5 : Concevoir les API et les règles d’accès
- SA-27 / SA-28 : Authentification et gestion des rôles

### Membre 2 – Base de données et référentiels
- SA-10 à SA-18

### Membre 3 – Backend et APIs métier
- SA-6 / SA-7
- SA-19 à SA-22
- SA-36 / SA-38

### Membre 4 – Frontend et parcours visiteur
- SA-6 / SA-8 / SA-9
- SA-23 à SA-26
- SA-29

### Membre 5 – LLM et conversation intelligente
- SA-30 à SA-38

## 5. Livrables attendus à la fin du sprint

- Architecture technique validée
- Diagramme des cas d’usage
- Matrice des rôles et droits
- Base PostgreSQL initialisée
- Backend et frontend initialisés
- API de base documentées
- Prototype de conversation sans compte
- Sélection ou validation du modèle LLM

## 6. Critères de réussite du sprint

- Les acteurs et les parcours métier sont documentés.
- L’architecture technique est claire et cohérente.
- Les règles d’accès et les rôles sont définis.
- Le backend, le frontend et la base de données sont prêts pour le développement fonctionnel.
- Le système met en place la base nécessaire à l’intégration du LLM.

## 7. Risques et points de vigilance

- Risque de confusion entre visiteur anonyme et candidat connecté.
- Risque de sur-complexité du modèle de permission.
- Risque de mauvaise intégration entre conversation et candidature.
- Risque de mauvaise compréhension du dialecte tunisien / Arabizi dans le LLM.

## 8. Définition de terminé

Le sprint est terminé lorsque :
- les documents de cadrage sont validés,
- les bases de données et architectures sont prêtes,
- les équipes disposent d’un socle technique commun,
- les dépendances entre modules sont clairement définies.

## 9. Conclusion

Le sprint 1 est un sprint d’infrastructure et de cadrage. Il pose les fondations nécessaires pour la réussite du projet SmartCampus AI. L’objectif est de clarifier les responsabilités, la structure technique, les flux fonctionnels et les outils de développement avant le démarrage de la production logicielle.
