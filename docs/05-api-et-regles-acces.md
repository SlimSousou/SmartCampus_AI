# SA-5 - Conception des API et règles d’accès

## 1. Objectif et périmètre

Ce document définit le contrat initial des API HTTP de SmartCampus AI et les contrôles d’accès associés. Il s’appuie sur l’[architecture SA-4](04-architecture-technique.md), les cas d’utilisation de [SA-3](01-cas-utilisation.md) et la [matrice des rôles](02-matrice-roles-droits.md).

Il s’agit d’une spécification de sprint 1 destinée à guider l’implémentation FastAPI. Les routes d’authentification, de consultation de l’utilisateur courant et d’administration des rôles sont implémentées dans le [backend SA-27/SA-28](../backend/README.md); les autres endpoints restent des contrats à développer.

## 2. Conventions générales

- Préfixe versionné : `/api/v1`.
- Transport : HTTPS en environnement déployé; corps et réponses JSON en UTF-8.
- Dates : ISO 8601 en UTC, par exemple `2026-11-15T10:30:00Z`.
- Identifiants de ressources : UUID; ils ne constituent jamais une preuve d’autorisation.
- Authentification : jeton d’accès `Bearer` pour les routes de compte; session invitée opaque dans un cookie `HttpOnly`, `Secure` et `SameSite` pour les routes anonymes.
- Pagination des listes : paramètres `limit` (défaut 20, maximum 100) et `cursor`; la réponse contient `items` et `next_cursor`.
- Filtrage par établissement, rôle ou statut : le serveur valide les filtres par rapport aux droits de l’utilisateur. Un paramètre fourni par le client ne peut pas élargir son périmètre.
- Les routes de modification valident les champs, les transitions métier et les droits sur l’objet côté backend. Le frontend ne constitue pas une frontière de sécurité.
- Les créations sensibles acceptent `Idempotency-Key`; les commandes de conversation acceptent un `client_message_id` afin d’éviter les doublons lors d’une nouvelle tentative.
- Les erreurs suivent le format `application/problem+json` avec `type`, `title`, `status`, `detail`, `code` et `request_id`. Les erreurs de validation peuvent ajouter `errors` avec les champs concernés.

Exemple d’erreur :

```json
{
  "type": "about:blank",
  "title": "Accès refusé",
  "status": 403,
  "detail": "Cette action n'est pas autorisée pour votre rôle.",
  "code": "permission_denied",
  "request_id": "6b74ce0b-73c5-4486-a980-1c3649110cf6"
}
```

Codes HTTP attendus : `200` lecture ou modification réussie, `201` création, `204` suppression/révocation réussie sans corps, `400` requête invalide, `401` authentification absente ou invalide, `403` permission insuffisante, `404` ressource inexistante ou hors périmètre, `409` conflit d’état ou doublon, `422` données valides en syntaxe mais invalides métier, `429` limite d’usage atteinte.

## 3. Identité, sessions et authentification

### Session invitée

| Méthode et route | Accès | Rôle |
|---|---|---|
| `POST /api/v1/guest-sessions` | Public, limité en débit | Créer une session anonyme et poser le cookie de session |
| `GET /api/v1/guest-sessions/{session_id}` | Cookie de cette session | Reprendre l’état minimal de la session propriétaire |
| `DELETE /api/v1/guest-sessions/{session_id}` | Cookie de cette session | Terminer la session et invalider le cookie |
| `POST /api/v1/guest-sessions/{session_id}/messages` | Cookie de cette session | Envoyer un message texte; réponse avec réponse IA et références de sources éventuelles |
| `POST /api/v1/guest-sessions/{session_id}/audio-messages` | Cookie de cette session | Transmettre un audio validé pour transcription et traitement |

À la création, le serveur génère un secret de session aléatoire, ne renvoie pas ce secret dans le JSON, et enregistre côté serveur son empreinte, son expiration et les quotas associés. Le `session_id` visible dans l’URL n’est pas le secret. Les limites de taille, durée, fréquence et types audio autorisés sont configurées côté serveur.

### Compte candidat et authentification

| Méthode et route | Accès | Rôle |
|---|---|---|
| `POST /api/v1/auth/register` | Public, limité en débit | Créer un compte candidat; attribuer le rôle candidat côté serveur |
| `POST /api/v1/auth/login` | Public, limité en débit | Authentifier un compte |
| `POST /api/v1/auth/refresh` | Cookie de renouvellement valide | Renouveler les jetons selon la politique de session |
| `POST /api/v1/auth/logout` | Authentifié | Révoquer la session et les cookies associés |
| `GET /api/v1/me` | Authentifié | Retourner l’identité et les rôles effectifs de l’utilisateur courant |

Les jetons d’accès sont de courte durée et envoyés dans l’en-tête `Authorization: Bearer`. Le jeton de renouvellement est placé dans un cookie `HttpOnly`, `Secure`, `SameSite` et renouvelé avec rotation. Les endpoints utilisant le cookie de renouvellement appliquent une protection CSRF. Le rôle n’est jamais choisi librement par l’utilisateur lors de l’inscription; l’attribution des rôles internes relève d’une opération administrateur auditée.

## 4. Catalogue et parcours candidat

| Méthode et route | Accès | Rôle |
|---|---|---|
| `GET /api/v1/programs` | Public | Lister les formations publiées; filtre `institution` limité à `IIT` ou `ISB` |
| `GET /api/v1/programs/{program_id}` | Public | Consulter une formation publiée et ses informations publiques |
| `GET /api/v1/me/profile` | Authentifié | Consulter son profil candidat |
| `PATCH /api/v1/me/profile` | Authentifié | Modifier les champs modifiables de son profil |
| `POST /api/v1/me/applications` | Authentifié | Créer une préinscription pour soi |
| `GET /api/v1/me/applications` | Authentifié | Lister uniquement ses candidatures |
| `GET /api/v1/me/applications/{application_id}` | Authentifié, propriétaire | Consulter sa candidature |
| `PATCH /api/v1/me/applications/{application_id}` | Authentifié, propriétaire | Compléter les champs autorisés lorsque le statut le permet |
| `POST /api/v1/me/conversations/attach` | Authentifié candidat | Rattacher une session invitée après confirmation de consentement |
| `GET /api/v1/me/qcm` | Authentifié | Lister ses QCM disponibles et passés |
| `POST /api/v1/me/qcm/{qcm_id}/attempts` | Authentifié | Démarrer une tentative autorisée |
| `PUT /api/v1/me/qcm/attempts/{attempt_id}/answers` | Authentifié, propriétaire | Soumettre ou mettre à jour ses réponses avant clôture |
| `GET /api/v1/me/appointments` | Authentifié | Consulter ses rendez-vous |
| `POST /api/v1/me/appointments/{appointment_id}/confirmation` | Authentifié, propriétaire | Confirmer ou décliner son rendez-vous |

Le rattachement de session exige un corps tel que `{"guest_session_id":"…","consent":true}`. Le backend vérifie que le cookie correspond à cette session, que le candidat est authentifié et que la session n’est pas déjà rattachée à un autre compte. Le transfert s’effectue dans une transaction; en cas d’échec, aucune donnée n’est partiellement associée.

## 5. Espaces professionnels

Les routes professionnelles exigent un jeton d’accès valide et des permissions vérifiées à chaque requête. Le périmètre IIT/ISB vient des rôles et attributs de l’identité authentifiée côté serveur, jamais d’un paramètre d’URL ou du corps de requête.

| Méthode et route | Accès | Rôle |
|---|---|---|
| `GET /api/v1/academic/candidates` | Authentifié, filtré par établissement | Responsable académique IIT ou ISB; ne retourne que son périmètre |
| `GET /api/v1/academic/candidates/{candidate_id}` | Même périmètre | Responsable académique autorisé |
| `POST /api/v1/academic/candidates/{candidate_id}/recommendation-review` | Même périmètre | Confirmer ou ajuster une recommandation avec justification |
| `GET /api/v1/academic/programs` | Authentifié, filtré par établissement | Responsable académique IIT ou ISB |
| `POST /api/v1/academic/programs` | Authentifié, établissement déduit du rôle | Créer une formation dans son périmètre |
| `PATCH /api/v1/academic/programs/{program_id}` | Authentifié, propriétaire du périmètre | Modifier les champs académiques autorisés |
| `GET /api/v1/interviews/candidates` | Authentifié, dossiers prêts pour entretien uniquement | Responsable entretien |
| `GET /api/v1/interviews/candidates/{candidate_id}` | Authentifié, dossier prêt pour entretien | Responsable entretien |
| `POST /api/v1/interviews/candidates/{candidate_id}/appointments` | Authentifié | Proposer ou planifier un rendez-vous |
| `PATCH /api/v1/interviews/appointments/{appointment_id}` | Authentifié, dossier autorisé | Modifier ou annuler un rendez-vous selon son état |
| `POST /api/v1/interviews/candidates/{candidate_id}/outcome` | Authentifié | Enregistrer résultat, observations et prochaine étape permise |
| `POST /api/v1/interviews/candidates/{candidate_id}/request-info` | Authentifié | Demander un complément et tracer la demande |
| `POST /api/v1/interviews/candidates/{candidate_id}/forward` | Authentifié | Transmettre le dossier à l’étape autorisée |
| `GET /api/v1/analytics/overview` | Authentifié, agrégé | Direction; responsables académiques reçoivent uniquement leurs indicateurs de périmètre |

Les espaces IIT et ISB ne peuvent pas lire ni modifier les dossiers de l’autre établissement. L’administrateur ne reçoit pas, du seul fait de son rôle technique, le droit de confirmer une recommandation ou de saisir un résultat d’entretien.

## 6. Administration et intégrations

| Méthode et route | Accès | Rôle |
|---|---|---|
| `GET /api/v1/admin/users` | Authentifié | Administrateur; liste paginée des comptes |
| `PATCH /api/v1/admin/users/{user_id}/roles` | Authentifié | Administrateur; attribution/retrait audité de rôles autorisés |
| `GET /api/v1/admin/documents` | Authentifié | Administrateur; consulter l’état des sources RAG |
| `POST /api/v1/admin/documents` | Authentifié | Administrateur; enregistrer une source documentaire et ses métadonnées |
| `POST /api/v1/admin/documents/{document_id}/publish` | Authentifié | Administrateur; publier et déclencher l’indexation validée |
| `POST /api/v1/admin/documents/{document_id}/withdraw` | Authentifié | Administrateur; retirer la source de l’index de recherche |
| `GET /api/v1/admin/audit-events` | Authentifié | Administrateur; journaux nécessaires à l’exploitation, accès audité |
| `GET /api/v1/health` | Public, sans détail interne | Vérification de disponibilité minimale |

Les secrets, clés LLM, paramètres SMTP et accès base de données ne sont jamais modifiables ou consultables via une API publique d’administration. Les notifications sont déclenchées par le backend après validation de la transition métier; aucune route ne permet à un agent IA d’envoyer arbitrairement un email.

## 7. Modèle de contrôle d’accès

Chaque requête suit ces contrôles dans cet ordre :

1. **Authentification :** identifier l’utilisateur ou valider la session invitée. Répondre `401` si l’identité requise est absente ou invalide.
2. **Autorisation fonctionnelle :** vérifier la permission nécessaire à l’action, indépendamment de l’interface affichée.
3. **Autorisation sur l’objet :** vérifier propriétaire, établissement, statut du dossier et relation avec la ressource demandée. Utiliser `404` pour ne pas révéler l’existence d’un objet hors périmètre.
4. **Validation métier :** contrôler que l’action est permise dans l’état courant et que les champs modifiés sont autorisés.
5. **Traçabilité :** enregistrer l’acteur, l’action, l’objet, l’horodatage et le résultat pour toute opération sensible.

| Capacité | Candidat | Resp. académique IIT/ISB | Resp. entretien | Direction | Admin |
|---|---|---|---|---|---|
| Catalogue public et chat invité | Lecture / session propre | Lecture publique | Lecture publique | Lecture publique | Lecture publique |
| Profil, candidature, QCM, rendez-vous | Lecture/écriture sur ses objets | Lecture des candidats de son établissement selon besoin métier | Lecture des candidats prêts pour entretien | Agrégats uniquement | Support exceptionnel, justifié et audité |
| Recommandation académique | Lecture de sa recommandation | Confirmer/ajuster dans son établissement | Lecture du dossier d’entretien | Agrégats uniquement | Aucun droit de décision |
| Informations de formation | Lecture publique | Gestion dans son établissement | Lecture publique | Agrégats | Administration globale |
| Entretien et résultat | Aucun | Aucun | Gestion des dossiers assignés/prêts | Agrégats de suivi | Aucun droit de décision |
| Comptes, rôles, documents RAG, intégrations | Aucun | Aucun | Aucun | Aucun | Administration, sans décision d’admission |
| Tableau de bord | Aucun | Agrégats du périmètre | Suivi opérationnel des entretiens | Agrégats globaux | Indicateurs techniques |

## 8. Transitions et concurrence

- Le backend possède la machine d’état des candidatures, recommandations, QCM et rendez-vous. Le client ne choisit pas directement un statut arbitraire.
- Les transitions acceptées sont définies par le métier; une action non permise dans l’état courant répond `409` ou `422` avec un code d’erreur stable.
- La confirmation/ajustement d’une recommandation, le résultat d’entretien, la transmission d’un dossier, la gestion des rôles et la publication/retrait d’une source RAG sont auditables.
- Les modifications concurrentes utilisent un champ de version ou un en-tête `If-Match`; une version périmée produit `409` et ne remplace pas silencieusement les changements précédents.
- Les écritures importantes et leurs événements d’audit sont enregistrés atomiquement. Les effets externes (email, calendrier) sont déclenchés après commit et peuvent être retentés sans doublon.
- Les endpoints conversationnels sont soumis à des quotas par session/compte et à des limites de taille; les réponses et erreurs ne renvoient jamais les prompts système, les secrets ou les traces internes du fournisseur IA.

## 9. Exemples de contrats

### Message d’une session invitée

Requête `POST /api/v1/guest-sessions/{session_id}/messages` :

```json
{
  "client_message_id": "5f2bbfaf-86e7-48d3-898c-6e8df39f2cc8",
  "text": "Quelles formations en informatique propose l'IIT ?",
  "language": "auto"
}
```

Réponse `200 OK` :

```json
{
  "message_id": "7f77fdc8-88fb-4ccb-a02a-c12d59a64b35",
  "text": "Voici les parcours publiés qui correspondent à votre question…",
  "sources": [
    {
      "document_id": "b273a3fb-1f30-42ca-b94f-10d29a90526f",
      "title": "Catalogue officiel des formations IIT",
      "section": "Informatique",
      "version": "2026"
    }
  ],
  "created_at": "2026-11-15T10:30:00Z"
}
```

Les citations présentées doivent pointer vers des sources effectivement récupérées. Si aucune source publiée et pertinente n’est disponible, la réponse l’indique clairement au lieu d’inventer une référence.

### Ajustement d’une recommandation

Requête `POST /api/v1/academic/candidates/{candidate_id}/recommendation-review` :

```json
{
  "action": "adjust",
  "program_id": "d8e82bf2-0ae9-4e27-8480-aa0bd19d0032",
  "reason": "Les prérequis du parcours correspondent mieux au dossier vérifié."
}
```

Le serveur déduit l’établissement du rôle connecté, vérifie que le candidat et la formation appartiennent à ce périmètre, valide l’action et conserve l’auteur et la justification. Une `reason` est obligatoire pour un ajustement.

### Diagramme de séquence : contrôle d’accès API

Le diagramme illustre l’ouverture d’une session invitée, l’envoi d’un message, le contrôle du périmètre académique et le rattachement consenti de la session au compte candidat.


## 10. Tests d’acceptation SA-5

- Un appel sans jeton à une route privée répond `401`; un utilisateur authentifié sans permission répond `403`.
- Un candidat ne peut lire ni modifier le profil, la candidature, le QCM ou le rendez-vous d’un autre candidat, même en remplaçant l’UUID dans l’URL.
- Un responsable IIT ne peut lire, modifier ou retrouver par filtre un dossier ISB, et inversement.
- Un responsable entretien ne voit que les dossiers accessibles à cette étape et ne peut pas modifier une recommandation académique.
- La Direction reçoit des indicateurs agrégés et n’accède pas aux données nominatives via les routes analytiques.
- L’administrateur peut gérer les paramètres et les rôles selon ses permissions, mais ne peut pas effectuer une décision réservée à l’académique ou à l’entretien.
- Une session invitée ne peut être lue que par son cookie propriétaire; son rattachement à un compte exige authentification, consentement et transaction atomique.
- Les actions sensibles sont associées à un acteur et inscrites au journal d’audit; les erreurs ne divulguent pas l’existence d’objets hors périmètre.
- Les erreurs suivent le format documenté, les listes sont paginées, et les répétitions de commandes ne créent pas de doublons.