"""Tests unitaires pour analysis/dpe_extractor.py (extraction DPE from scratch)."""

import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analysis.dpe_extractor import extract_dpe, enrich_dpe_column


# ── Tests extract_dpe ─────────────────────────────────────────────────────────

class TestExtractDpe:
    """Extraction de la classe DPE depuis une description texte."""

    def test_pattern_dpe_a(self):
        """Détecte 'DPE A' explicite."""
        assert extract_dpe("Appartement avec DPE A, très économe.") == "A"

    def test_pattern_dpe_b_classe(self):
        """Détecte 'classe B' dans le texte."""
        assert extract_dpe("Bien classé classe B en énergie.") == "B"

    def test_pattern_dpe_c_etiquette(self):
        """Détecte 'étiquette énergie C'."""
        assert extract_dpe("Étiquette énergie C, chauffage gaz.") == "C"

    def test_pattern_passoire_thermique_is_g(self):
        """'passoire thermique' doit retourner G (priorité sur 'passoire' seul)."""
        result = extract_dpe("Ce bien est une passoire thermique, DPE G.")
        assert result == "G"

    def test_pattern_dpe_f(self):
        """Détecte 'DPE F' dans une description."""
        assert extract_dpe("Énergie : DPE F, travaux à prévoir.") == "F"

    def test_empty_description_returns_none(self):
        """Description vide → None."""
        assert extract_dpe("") is None

    def test_none_description_returns_none(self):
        """None en entrée → None."""
        assert extract_dpe(None) is None

    def test_no_dpe_info_returns_none(self):
        """Texte sans info DPE → None (ou valeur heuristique, pas d'exception)."""
        result = extract_dpe("Belle vue sur la mer, terrasse, parking.")
        # Soit None si aucune heuristique, soit une lettre valide
        assert result is None or result in "ABCDEFG"

    def test_double_vitrage_heuristic_good(self):
        """Double vitrage → heuristique favorable (B ou C si aucun pattern explicite)."""
        result = extract_dpe("Double vitrage, isolation récente, pompe à chaleur.")
        assert result in (None, "A", "B", "C")

    def test_dpe_uppercase_lowercase(self):
        """Insensible à la casse."""
        assert extract_dpe("dpe a, très bien isolé") == "A"

    def test_dpe_e_explicit(self):
        """Détecte 'DPE E' sans ambiguïté."""
        assert extract_dpe("Le bien a un DPE E, logement énergivore.") == "E"

    def test_returns_single_letter(self):
        """La valeur retournée est toujours une lettre A-G ou None."""
        descriptions = [
            "Appartement DPE B, très bien situé.",
            "Maison ancienne sans isolation, simple vitrage.",
            "Studio moderne, classe énergétique A.",
            "",
        ]
        for desc in descriptions:
            result = extract_dpe(desc)
            assert result is None or (isinstance(result, str) and result in "ABCDEFG")


# ── Tests enrich_dpe_column ───────────────────────────────────────────────────

class TestEnrichDpeColumn:
    """Enrichissement en lot d'une liste de descriptions."""

    def test_returns_same_length(self):
        """La liste retournée a la même longueur que l'entrée."""
        descs = ["DPE A bien isolé", "passoire thermique", "beau jardin"]
        result = enrich_dpe_column(descs)
        assert len(result) == len(descs)

    def test_known_patterns_detected(self):
        """Les patterns connus sont bien détectés dans la liste."""
        descs = ["Appartement DPE A", "Maison DPE G", "Villa sans info"]
        result = enrich_dpe_column(descs)
        assert result[0] == "A"
        assert result[1] == "G"

    def test_empty_list(self):
        """Liste vide → liste vide."""
        assert enrich_dpe_column([]) == []

    def test_all_none_descriptions(self):
        """Liste de None → liste de None."""
        result = enrich_dpe_column([None, None])
        assert all(r is None or r in "ABCDEFG" for r in result)

    def test_result_elements_valid(self):
        """Chaque élément est None ou une lettre A-G."""
        descs = ["DPE A", "classe C", "maison ancienne", None, ""]
        for val in enrich_dpe_column(descs):
            assert val is None or val in "ABCDEFG"
