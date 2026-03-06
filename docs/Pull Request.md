## Définition d'une Pull Request (PR)

Une **Pull Request** est une demande formelle soumise par un collaborateur pour fusionner les modifications apportées sur une branche de travail (ex: `feat/`) vers une branche de référence (ex: `dev`). Elle permet :

* **La revue de code** : Un autre membre de l'équipe vérifie la qualité et la logique du code avant son intégration.


* **La validation automatique** : Le lancement des GitHub Actions pour exécuter les tests **Pytest** et vérifier que le code ne crée pas de régressions.


* **La traçabilité** : Chaque modification est documentée et liée à une tâche spécifique, ce qui est essentiel pour l'évaluation de la répartition du travail.



---

## Procédure de création d'une Pull Request

Pour soumettre vos modifications, suivez les étapes structurées ci-dessous sur le dépôt GitHub du groupe:

### 1. Publication de la branche

Une fois votre travail terminé et vos tests locaux validés, poussez votre branche sur le serveur distant :

```bash
git push origin feat/votre-nom-tache

```

### 2. Ouverture de la demande sur GitHub

1. Rendez-vous sur l'onglet **Pull Requests** de votre dépôt GitHub Classroom.


2. Cliquez sur le bouton **New Pull Request**.
3. Sélectionnez la branche de destination (**base: dev**) et votre branche de travail (**compare: feat/votre-nom-tache**).
4. Cliquez sur **Create Pull Request**.

### 3. Documentation et affectation

* **Titre** : Utilisez un titre explicite (ex: `feat: implémentation de la fonction mean`).
* **Description** : Décrivez brièvement ce qui a été fait, les tests effectués et, si possible, liez la PR à une User Story.
* **Reviewers** : Assignez au moins un membre de l'équipe (ex: Mathis pour les stats, Robin pour l'UI) pour relire votre code.

### 4. Validation par l'Intégration Continue (CI)

Après l'ouverture de la PR, le workflow **GitHub Actions** se déclenche automatiquement.

* Consultez le statut des tests en bas de la page de la PR.
* En cas d'échec, corrigez votre code sur votre branche locale, commitez et pushez à nouveau ; la PR se mettra à jour automatiquement.
* Vous pouvez consulter le **Job Summary** dans l'onglet **Actions** pour voir le détail de votre score.



### 5. Fusion (Merge)

Une fois que les tests sont validés ("pass") et que le relecteur a approuvé les modifications, la PR peut être fusionnée dans `dev`. La branche de travail peut alors être supprimée.

---