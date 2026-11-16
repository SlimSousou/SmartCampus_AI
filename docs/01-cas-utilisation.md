# Diagramme des cas d’usage

## Vue d’ensemble

Le diagramme reprend les cinq acteurs métier définis dans le document officiel du projet. Le système agentique et ses agents sont des composants internes, pas des rôles humains.

```plantuml
@startuml
skinparam defaultFontSize 14
skinparam defaultFontColor #333333
!include https://static.visual-paradigm.com/web/resources/plantuml-stdlib/themes/vp.puml
skinparam vpDiagramType UseCaseDiagram
left to right direction

actor "Candidat / futur étudiant\n(Primary)" as candidate
actor "Responsable académique IIT\n(Primary)" as acadIIT
actor "Responsable académique ISB\n(Primary)" as acadISB
actor "Responsable entretien\n(Primary)" as interviewer
actor "Direction\n(Primary)" as direction
actor "Administrateur de la plateforme\n(Primary)" as admin

rectangle "Plateforme d'orientation agentique IIT / ISB" {
  usecase "Dialoguer en français,\ntunisien ou Arabizi\n(texte ou audio)" as UC1
  usecase "Découvrir et comparer\nles formations IIT / ISB" as UC2
  usecase "Recevoir une orientation\njustifiée" as UC3
  usecase "Effectuer une préinscription" as UC4
  usecase "Passer un QCM personnalisé" as UC5
  usecase "Consulter rendez-vous\net notifications" as UC6
  usecase "S'authentifier" as UC0

  usecase "Consulter les candidats\norientés vers l'IIT" as UC7
  usecase "Vérifier ou ajuster\nune recommandation IIT" as UC8
  usecase "Gérer les informations\ndes formations IIT" as UC9
  usecase "Consulter les statistiques IIT" as UC10

  usecase "Consulter les candidats\norientés vers l'ISB" as UC11
  usecase "Vérifier ou ajuster\nune recommandation ISB" as UC12
  usecase "Gérer les informations\ndes formations ISB" as UC13
  usecase "Consulter les statistiques ISB" as UC14

  usecase "Consulter le dossier\net la synthèse du candidat" as UC15
  usecase "Consulter les réponses\net résultats du QCM" as UC16
  usecase "Définir un rendez-vous\net envoyer une invitation" as UC17
  usecase "Saisir le résultat et les\nobservations de l'entretien" as UC18
  usecase "Demander un complément ou\ntransmettre le dossier" as UC19

  usecase "Consulter le tableau\nde bord global" as UC20
  usecase "Analyser les conversions\net indicateurs" as UC21
  usecase "Identifier les dossiers\nen attente ou abandonnés" as UC22

  usecase "Gérer les comptes,\nrôles et droits" as UC23
  usecase "Configurer formations\net campagnes" as UC24
  usecase "Administrer les sources RAG\net règles d'orientation" as UC25
  usecase "Configurer QCM, emails,\nagents IA et intégrations" as UC26
  usecase "Consulter les journaux\net erreurs" as UC27
}

candidate -[#black]- UC1
candidate -[#black]- UC2
candidate -[#black]- UC3
candidate -[#black]- UC4
candidate -[#black]- UC5
candidate -[#black]- UC6

acadIIT -[#crimson]- UC7
acadIIT -[#crimson]- UC8
acadIIT -[#crimson]- UC9
acadIIT -[#crimson]- UC10

acadISB -[#goldenrod]- UC11
acadISB -[#goldenrod]- UC12
acadISB -[#goldenrod]- UC13
acadISB -[#goldenrod]- UC14

interviewer -[#green]- UC15
interviewer -[#green]- UC16
interviewer -[#green]- UC17
interviewer -[#green]- UC18
interviewer -[#green]- UC19

direction -[#darkturquoise]- UC20
direction -[#darkturquoise]- UC21
direction -[#darkturquoise]- UC22

admin -[#violet]- UC23
admin -[#violet]- UC24
admin -[#violet]- UC25
admin -[#violet]- UC26
admin -[#violet]- UC27

UC4 ..> UC0 : <<include>>
UC5 ..> UC0 : <<include>>
UC6 ..> UC0 : <<include>>
UC10 ..> UC0 : <<include>>
UC14 ..> UC0 : <<include>>
UC15 ..> UC0 : <<include>>
UC20 ..> UC0 : <<include>>
UC23 ..> UC0 : <<include>>

UC3 ..> UC2 : <<include>>

UC4 <.. UC5 : <<extend>>
UC17 <.. UC18 : <<extend>>
UC19 <.. UC18 : <<extend>>

@enduml
```

## Cas d’usage principaux

### 1. Candidat / futur étudiant
- Échanger avec la plateforme en français, dialecte tunisien ou Arabizi, par texte ou audio.
- Découvrir et comparer les formations de l’IIT et de l’ISB, puis recevoir des recommandations expliquées.
- Construire progressivement son profil, effectuer une préinscription et passer un QCM ciblé.
- Consulter son rendez-vous et recevoir les notifications de suivi.

Le candidat peut commencer une conversation sans compte. Cette possibilité est un mode d’accès, pas un acteur métier distinct dans le document officiel. La création de compte et les informations requises interviennent avant les actions de préinscription qui les nécessitent.

### 2. Responsable académique IIT
- Consulter les candidats orientés vers l’IIT, leur profil, leurs recommandations et les résultats du QCM.
- Vérifier ou ajuster une recommandation et gérer les informations des formations IIT.
- Consulter les statistiques d’intérêt et d’orientation vers les parcours IIT.

### 3. Responsable académique ISB
- Consulter les candidats orientés vers l’ISB, leur profil, leurs recommandations et les résultats du QCM.
- Vérifier ou ajuster une recommandation et gérer les informations des formations ISB.
- Consulter les statistiques d’intérêt et d’orientation vers les formations ISB.

### 4. Responsable entretien
- Consulter les candidats prêts pour un entretien, leur profil, leur parcours conversationnel et la formation recommandée.
- Consulter le QCM, ses réponses et la synthèse des points à approfondir.
- Définir ou valider un rendez-vous, envoyer une invitation et saisir le résultat de l’entretien.
- Demander un complément ou transmettre le dossier à l’étape suivante.

### 5. Direction
- Suivre les volumes de conversations, orientations, préinscriptions, entretiens et inscriptions.
- Analyser les formations demandées, les orientations IIT/ISB et les taux de conversion.
- Identifier les dossiers en attente ou abandonnés et consulter les indicateurs du système agentique.

### 6. Administrateur de la plateforme
- Gérer les comptes, rôles, droits, formations, campagnes et paramètres du workflow.
- Administrer les sources documentaires RAG, les règles d’orientation, les modèles de QCM et les notifications.
- Superviser les agents IA, les intégrations, les paramètres techniques, les journaux et les erreurs.

## Composants internes (non-acteurs)

Le superviseur agentique, le LLM, le RAG, la transcription audio et les outils de notification sont des composants du système. Ils assistent les acteurs, mais ne remplacent pas les responsables humains pour la validation des recommandations, les entretiens ou les décisions officielles.

## Règles métier dérivées

- Un candidat peut démarrer une conversation sans compte; les données personnelles ne sont conservées et rattachées qu’en respectant les règles de consentement et de sécurité.
- Un candidat ne peut accéder qu’à son propre profil, ses réponses et son dossier.
- Les responsables académiques consultent les candidats et les données de formation dans leur périmètre IIT ou ISB.
- Le responsable entretien accède aux dossiers prêts pour entretien et saisit les résultats et observations associés.
- La Direction consulte des indicateurs de pilotage; l’accès aux données individuelles doit être limité au besoin métier.
- L’administrateur configure la plateforme, mais les validations académiques et les décisions officielles restent humaines.
- Les actions sensibles et les changements de statut sont traçables.

## Livrable attendu

Ce document permet de formaliser les interactions fonctionnelles avant la conception technique et le développement.
