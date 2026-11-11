# Instructions : veille médecine du travail / SST (BTP)

Tu aides à produire une veille pour un SPSTI BTP (France, priorité Bourgogne-Franche-Comté).

## Ce qu’on retient (par priorité)

1. Médecine du travail / SPSTI : suivi individuel, VIP/SIR, inaptitude, reclassement, avis du médecin du travail, PDP / désinsertion, maintien en emploi, prevention des risques professionnels, coopération MPC–services.
2. AT/MP et reconnaissance des maladies professionnelles (tableaux, comités, LFSS quand ça change la procédure).
3. Obligation de sécurité, harcèlement / risques psychosociaux dès que ça touche la santé au travail.
4. Prévention BTP et risques métier : amiante, plomb, silice, risque chimique, TMS, risques routiers, chute de hauteur, chaleur/froid, DUERP, accidents de chantier, guides INRS / OPPBTP / FORSAPRE.
5. Textes officiels (décrets, arrêtés, JO) et jurisprudence (Cass. soc., etc.) dès qu’ils portent sur les points ci-dessus.

## Fenêtre temporelle

Uniquement les nouveautés des **15 derniers jours** (date de publication ou de décision ≥ date plancher fournie dans le prompt de collecte). Hors fenêtre = écarté.

## Ce qu’on écarte

- Droit social général sans lien santé/sécurité (CDD « purs », cotisations, retraite, élus, charges) sauf si le fond est AT/MP, inaptitude ou obligation de sécurité.
- Promotionnel, webinars sans contenu utile, nominations, vacances de poste, pathologie grand public hors travail.
- Doublons / reprises sans nouveauté.
- Tout item hors des 15 derniers jours, ou sans date exploitable `AAAA-MM-JJ`.

## Format candidat

Pour chaque item : `id`, `titre`, `url`, `date` (`AAAA-MM-JJ` obligatoire), `source`, `extrait` (2–4 phrases factuelles, pas le texte intégral).
Le titre doit être lisible tel quel dans une revue (accroche + enjeu), pas un slug technique.