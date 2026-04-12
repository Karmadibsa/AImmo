"""Tests unitaires pour analysis/scoring.py."""

import pytest

from analysis.scoring import classify, is_opportunity, score_opportunity, top_opportunities


# ── score_opportunity ────────────────────────────────────────────────────────

def test_score_sous_evalue():
    """Un bien à 90 000 € pour un marché à 100 000 € → -10 %."""
    assert score_opportunity(90_000, 100_000) == -10.0


def test_score_surevalue():
    """Un bien à 110 000 € pour un marché à 100 000 € → +10 %."""
    assert score_opportunity(110_000, 100_000) == 10.0


def test_score_prix_marche():
    """Un bien au prix du marché → 0 %."""
    assert score_opportunity(100_000, 100_000) == 0.0


def test_score_prix_predit_nul_raises():
    """Un prix prédit nul doit lever une ValueError."""
    with pytest.raises(ValueError):
        score_opportunity(100_000, 0)


def test_score_prix_predit_negatif_raises():
    """Un prix prédit négatif doit lever une ValueError."""
    with pytest.raises(ValueError):
        score_opportunity(100_000, -50_000)


# ── classify ─────────────────────────────────────────────────────────────────

def test_classify_opportunite():
    assert classify(-15.0) == "Opportunité"


def test_classify_bonne_affaire():
    assert classify(-7.0) == "Bonne affaire"


def test_classify_prix_marche():
    assert classify(0.0) == "Prix marché"


def test_classify_prix_eleve():
    assert classify(20.0) == "Prix élevé"


def test_classify_frontiere_10():
    """Exactement -10 % → Bonne affaire (pas Opportunité)."""
    assert classify(-10.0) == "Bonne affaire"


def test_classify_frontiere_5():
    """Exactement +5 % → Prix marché."""
    assert classify(5.0) == "Prix marché"


# ── is_opportunity ───────────────────────────────────────────────────────────

def test_is_opportunity_true():
    assert is_opportunity(-15.0) is True


def test_is_opportunity_false():
    assert is_opportunity(-5.0) is False


def test_is_opportunity_seuil_custom():
    """Avec un seuil personnalisé à -5 %."""
    assert is_opportunity(-6.0, seuil=-5.0) is True
    assert is_opportunity(-4.0, seuil=-5.0) is False


# ── top_opportunities ────────────────────────────────────────────────────────

def test_top_opportunities_tri_et_seuil():
    """Seuls les biens < -10 % sont retenus, triés par écart croissant."""
    items = [
        {"ecart_pct": -5},
        {"ecart_pct": -20},
        {"ecart_pct": -15},
        {"ecart_pct": 3},
    ]
    result = top_opportunities(items)
    assert len(result) == 2
    assert result[0]["ecart_pct"] == -20
    assert result[1]["ecart_pct"] == -15


def test_top_opportunities_limite_n():
    """Le paramètre n limite le nombre de résultats."""
    items = [{"ecart_pct": -i * 5} for i in range(1, 10)]  # -5, -10, -15, ..., -45
    result = top_opportunities(items, n=3)
    assert len(result) == 3


def test_top_opportunities_vide():
    """Aucune opportunité → liste vide."""
    items = [{"ecart_pct": 0}, {"ecart_pct": 5}]
    assert top_opportunities(items) == []
