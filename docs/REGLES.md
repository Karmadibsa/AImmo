# Protocole de Développement et Collaboration Git

Ce document définit les standards de travail pour l'équipe AImmo afin de garantir la stabilité du code et la traçabilité des contributions individuelles.

## Gestion des Branches et Flux de Travail

Le projet suit un flux de travail unidirectionnel centré sur la branche d'intégration pour assurer la stabilité de l'application finale.

### Hiérarchie des Branches

* **main** : Branche de production. Elle contient uniquement le code stable, testé et validé. Aucun commit direct n'est autorisé sur cette branche. Elle est mise à jour par fusion depuis la branche `dev` lors des jalons de livraison.


* **dev** : Branche d'intégration principale. Toutes les fonctionnalités développées doivent converger vers cette branche. Elle sert de point de départ pour toute nouvelle tâche.
* **Branches de fonctionnalités (feat/) et de corrections (fix/)** : Branches temporaires dédiées à une tâche unique et isolée.

### Workflow Opérationnel

Le cycle de développement suit strictement les étapes suivantes :

1. Synchronisation locale avec la branche de référence : `git checkout dev` puis `git pull origin dev`.
2. Création d'une branche de travail spécifique : `git checkout -b type/nom-membre-tache`.
3. Développement et tests locaux.
4. Publication de la branche et ouverture d'une Pull Request (PR) vers `dev` pour revue de code.



---

## Rôles et Responsabilités

La structure du dépôt est organisée pour séparer les livrables techniques des documents de gestion.

* **Gestion de Projet (Julie)** : Responsable de la documentation dans le répertoire `docs/` et des supports de soutenance dans le répertoire `presentation/`. Elle assure la cohérence des User Stories et du planning.
* **Équipe Technique (Axel, Mathis, Benoit, Robin)** : Développement exclusif au sein des répertoires `analysis/`, `app/` et `data/`. Toute intervention doit faire l'objet d'une branche dédiée.



---

## Nomenclature et Standards de Communication

### Convention de Nommage des Branches

Le format standard à appliquer est : `type/prénom-description-succincte`.

* Exemple : `feat/axel-collecte-dvf`
* Exemple : `fix/mathis-regression-error`
* Exemple : `docs/julie-rapport-final`

### Standards de Commits (Conventional Commits)

Chaque commit doit être préfixé pour expliciter la nature de la modification :

* **feat:** Ajout d'une nouvelle fonctionnalité.
* **fix:** Correction d'un bug.
* **docs:** Modification de la documentation ou des supports de présentation.
* **test:** Ajout ou modification de tests unitaires.
* **style:** Amélioration de la mise en forme du code sans modification logique.
* **refactor:** Modification du code n'ajoutant ni fonctionnalité ni correction de bug.

---

## Qualité du Code et Méthodologie

### Approche Test-Driven Development (TDD)

Le projet intègre une validation automatique par intégration continue (CI) via GitHub Actions. L'équipe adopte le cycle suivant :

1. **Red** : Rédaction d'un test unitaire dans le dossier `tests/` qui échoue initialement.
2. **Green** : Implémentation du code minimal pour valider le test.
3. **Refactor** : Optimisation et nettoyage du code sous réserve de validation permanente du test.

### Contraintes de Développement "From Scratch"

Conformément aux exigences du projet, les règles suivantes sont impératives pour les modules de calcul:

* **Interdiction des bibliothèques tierces** : L'utilisation de `numpy`, `pandas` (pour les calculs), `sklearn` ou `statistics` est strictement interdite dans le répertoire `analysis/`.


* **Structures natives** : Seules les listes et types primitifs Python doivent être utilisés pour les algorithmes de statistiques et de régression.


* **Typage et Documentation** : L'utilisation des "type hints" est obligatoire pour chaque fonction. Chaque module doit inclure une Docstring précisant les paramètres, les retours et les formules mathématiques appliquées.


---

