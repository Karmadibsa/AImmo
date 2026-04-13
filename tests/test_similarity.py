"""Tests unitaires pour analysis/similarity.py (k-NN from scratch)."""

import sys
import os
import math
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analysis.similarity import euclidean_distance, normalize_features, knn_similar, find_similar_properties


# ── Tests euclidean_distance ──────────────────────────────────────────────────

class TestEuclideanDistance:
    """Distance euclidienne entre deux vecteurs."""

    def test_identical_vectors_distance_zero(self):
        """Deux vecteurs identiques → distance 0."""
        assert euclidean_distance([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_simple_2d(self):
        """Distance entre (0,0) et (3,4) = 5."""
        assert abs(euclidean_distance([0.0, 0.0], [3.0, 4.0]) - 5.0) < 1e-9

    def test_1d_distance(self):
        """Distance 1D = valeur absolue de la différence."""
        assert abs(euclidean_distance([2.0], [5.0]) - 3.0) < 1e-9

    def test_symmetry(self):
        """La distance est symétrique."""
        a = [1.0, 3.0, 5.0]
        b = [4.0, 7.0, 2.0]
        assert euclidean_distance(a, b) == euclidean_distance(b, a)

    def test_non_negative(self):
        """La distance est toujours positive ou nulle."""
        assert euclidean_distance([-1.0, -2.0], [3.0, 4.0]) >= 0.0


# ── Tests normalize_features ──────────────────────────────────────────────────

class TestNormalizeFeatures:
    """Normalisation min-max des features."""

    def test_output_shape(self):
        """La matrice normalisée a le bon nombre de lignes."""
        items = [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}]
        normed, mins, maxs = normalize_features(items, ["a", "b"])
        assert len(normed) == 3
        assert len(normed[0]) == 2

    def test_values_between_0_and_1(self):
        """Toutes les valeurs normalisées sont dans [0, 1]."""
        items = [{"x": 10, "y": 100}, {"x": 20, "y": 200}, {"x": 30, "y": 300}]
        normed, _, _ = normalize_features(items, ["x", "y"])
        for row in normed:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_min_is_0_max_is_1(self):
        """La valeur minimale est normalisée à 0, la maximale à 1."""
        items = [{"v": 10}, {"v": 20}, {"v": 30}]
        normed, mins, maxs = normalize_features(items, ["v"])
        vals = [row[0] for row in normed]
        assert abs(min(vals) - 0.0) < 1e-9
        assert abs(max(vals) - 1.0) < 1e-9

    def test_missing_values_treated_as_mean(self):
        """Les valeurs None/NaN sont remplacées par la moyenne de la colonne."""
        items = [{"v": 10.0}, {"v": None}, {"v": 30.0}]
        normed, _, _ = normalize_features(items, ["v"])
        # Ne doit pas lever d'exception
        assert len(normed) == 3

    def test_constant_column_no_crash(self):
        """Une colonne constante (min=max) ne doit pas lever d'exception."""
        items = [{"v": 5}, {"v": 5}, {"v": 5}]
        normed, _, _ = normalize_features(items, ["v"])
        # Toutes les valeurs sont identiques (0.5 ou 0.0) — pas d'exception
        assert all(isinstance(row[0], float) for row in normed)


# ── Tests knn_similar ─────────────────────────────────────────────────────────

class TestKnnSimilar:
    """Recherche des k plus proches voisins."""

    def test_returns_k_results(self):
        """Retourne exactement k résultats."""
        matrix = [[0.0, 0.0], [0.1, 0.1], [0.5, 0.5], [0.9, 0.9], [1.0, 1.0]]
        result = knn_similar(0, matrix, k=3)
        assert len(result) == 3

    def test_target_not_in_results(self):
        """L'élément cible lui-même n'est pas dans les résultats."""
        matrix = [[0.0, 0.0], [0.1, 0.1], [0.5, 0.5], [1.0, 1.0]]
        result = knn_similar(0, matrix, k=2)
        indices = [r[0] for r in result]
        assert 0 not in indices

    def test_nearest_first(self):
        """Le voisin le plus proche est en premier."""
        matrix = [
            [0.0, 0.0],   # cible
            [0.1, 0.1],   # très proche
            [0.9, 0.9],   # loin
        ]
        result = knn_similar(0, matrix, k=2)
        assert result[0][0] == 1  # indice 1 = le plus proche

    def test_k_larger_than_available(self):
        """Si k > n-1, retourne tous les voisins disponibles sans erreur."""
        matrix = [[0.0], [0.5], [1.0]]
        result = knn_similar(0, matrix, k=10)
        assert len(result) <= 2  # 3 points - 1 (cible) = 2 max


# ── Tests find_similar_properties ─────────────────────────────────────────────

class TestFindSimilarProperties:
    """Recherche de biens similaires (pipeline complet)."""

    def _make_items(self):
        return [
            {"titre": "Appt A", "surface_reelle_bati": 50, "valeur_fonciere": 150_000, "nombre_pieces_principales": 2},
            {"titre": "Appt B", "surface_reelle_bati": 52, "valeur_fonciere": 155_000, "nombre_pieces_principales": 2},
            {"titre": "Maison C", "surface_reelle_bati": 120, "valeur_fonciere": 350_000, "nombre_pieces_principales": 5},
            {"titre": "Studio D", "surface_reelle_bati": 25, "valeur_fonciere": 90_000, "nombre_pieces_principales": 1},
        ]

    def test_returns_list_of_dicts(self):
        """Le résultat est une liste de dicts."""
        items = self._make_items()
        result = find_similar_properties(items, 0, ["surface_reelle_bati", "valeur_fonciere"], k=2)
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    def test_enriched_with_similarity_pct(self):
        """Chaque résultat a un champ _similarite_pct entre 0 et 100."""
        items = self._make_items()
        result = find_similar_properties(items, 0, ["surface_reelle_bati", "valeur_fonciere"], k=2)
        for r in result:
            assert "_similarite_pct" in r
            assert 0.0 <= r["_similarite_pct"] <= 100.0

    def test_k_results(self):
        """Retourne au plus k biens similaires."""
        items = self._make_items()
        result = find_similar_properties(items, 0, ["surface_reelle_bati", "valeur_fonciere"], k=2)
        assert len(result) <= 2

    def test_closest_item_is_similar(self):
        """L'Appt B (très proche de A) doit apparaître parmi les similaires de A."""
        items = self._make_items()
        result = find_similar_properties(items, 0, ["surface_reelle_bati", "valeur_fonciere"], k=2)
        titres = [r.get("titre") for r in result]
        assert "Appt B" in titres

    def test_target_not_in_results(self):
        """Le bien cible n'apparaît pas dans ses propres similaires."""
        items = self._make_items()
        result = find_similar_properties(items, 0, ["surface_reelle_bati", "valeur_fonciere"], k=3)
        titres = [r.get("titre") for r in result]
        assert "Appt A" not in titres

    def test_few_items_no_crash(self):
        """Fonctionne même avec seulement 2 éléments."""
        items = [
            {"surface_reelle_bati": 50, "valeur_fonciere": 100_000},
            {"surface_reelle_bati": 60, "valeur_fonciere": 120_000},
        ]
        result = find_similar_properties(items, 0, ["surface_reelle_bati", "valeur_fonciere"], k=3)
        assert len(result) <= 1
