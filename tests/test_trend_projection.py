"""Tests unitaires pour analysis/trend_projection.py (projection temporelle from scratch)."""

import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analysis.trend_projection import (
    _period_to_index,
    _index_to_period,
    compute_trend,
    project_prices,
)


# ── Tests _period_to_index ────────────────────────────────────────────────────

class TestPeriodToIndex:
    """Conversion période YYYY-MM → index numérique (base : 2024-01 = 1)."""

    def test_first_period_is_1(self):
        """'2024-01' → index 1.0 (base fixe de la fonction)."""
        idx = _period_to_index("2024-01")
        assert idx == 1.0

    def test_second_month_is_2(self):
        """'2024-02' → index 2.0."""
        idx = _period_to_index("2024-02")
        assert idx == 2.0

    def test_twelve_months_later(self):
        """'2025-01' → index 13.0 (12 mois après 2024-01)."""
        idx = _period_to_index("2025-01")
        assert idx == 13.0

    def test_index_strictly_increasing(self):
        """Les index croissent strictement avec le temps."""
        periods = ["2024-01", "2024-06", "2025-01", "2025-06"]
        indices = [_period_to_index(p) for p in periods]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)  # tous distincts


# ── Tests _index_to_period ────────────────────────────────────────────────────

class TestIndexToPeriod:
    """Conversion index numérique → période YYYY-MM."""

    def test_round_trip(self):
        """Aller-retour index → période → index conserve la valeur."""
        for idx in [1.0, 3.0, 12.0, 18.0]:
            period = _index_to_period(idx)
            assert _period_to_index(period) == idx

    def test_returns_string_format(self):
        """Le résultat a le format YYYY-MM."""
        period = _index_to_period(1.0)
        assert len(period) == 7
        assert period[4] == "-"

    def test_index_1_is_jan_2024(self):
        """Index 1 → '2024-01'."""
        assert _index_to_period(1.0) == "2024-01"

    def test_index_13_is_jan_2025(self):
        """Index 13 → '2025-01'."""
        assert _index_to_period(13.0) == "2025-01"


# ── Tests compute_trend ───────────────────────────────────────────────────────

class TestComputeTrend:
    """Calcul de la tendance linéaire (alpha, beta) sur les prix mensuels."""

    def test_returns_alpha_beta(self):
        """Retourne un tuple (alpha, beta)."""
        monthly = {
            "2024-01": 3000, "2024-02": 3050, "2024-03": 3100,
            "2024-04": 3150, "2024-05": 3200,
        }
        alpha, beta = compute_trend(monthly)
        assert isinstance(alpha, float)
        assert isinstance(beta, float)

    def test_increasing_trend_positive_beta(self):
        """Tendance haussière → beta positif."""
        monthly = {
            "2024-01": 3000, "2024-02": 3100, "2024-03": 3200,
            "2024-04": 3300, "2024-05": 3400,
        }
        _, beta = compute_trend(monthly)
        assert beta > 0

    def test_decreasing_trend_negative_beta(self):
        """Tendance baissière → beta négatif."""
        monthly = {
            "2024-01": 4000, "2024-02": 3900, "2024-03": 3800,
            "2024-04": 3700, "2024-05": 3600,
        }
        _, beta = compute_trend(monthly)
        assert beta < 0

    def test_constant_trend_near_zero_beta(self):
        """Prix constant → beta proche de 0."""
        monthly = {f"2024-{m:02d}": 3000 for m in range(1, 7)}
        _, beta = compute_trend(monthly)
        assert abs(beta) < 1.0


# ── Tests project_prices ──────────────────────────────────────────────────────

class TestProjectPrices:
    """Projection des prix sur n mois à venir."""

    def _monthly(self):
        return {
            "2024-01": 3000, "2024-02": 3050, "2024-03": 3100,
            "2024-04": 3150, "2024-05": 3200, "2024-06": 3250,
        }

    def test_result_has_required_keys(self):
        """Le dict résultat contient les clés attendues."""
        result = project_prices(self._monthly(), n_months_ahead=3)
        for key in ["historique", "projection", "alpha", "beta",
                    "tendance", "variation_annuelle_pct"]:
            assert key in result, f"Clé manquante : {key}"

    def test_historique_matches_input(self):
        """L'historique dans le résultat correspond aux données d'entrée."""
        monthly = self._monthly()
        result = project_prices(monthly, n_months_ahead=3)
        for period, val in monthly.items():
            assert period in result["historique"]
            assert abs(result["historique"][period] - val) < 1.0

    def test_projection_has_n_entries(self):
        """La projection contient exactement n_months_ahead entrées."""
        result = project_prices(self._monthly(), n_months_ahead=6)
        assert len(result["projection"]) == 6

    def test_projection_periods_after_history(self):
        """Toutes les périodes projetées sont après la dernière période historique."""
        monthly = self._monthly()
        result = project_prices(monthly, n_months_ahead=3)
        last_hist = max(monthly.keys())
        for period in result["projection"]:
            assert period > last_hist

    def test_projection_values_are_positive(self):
        """Les prix projetés sont positifs."""
        result = project_prices(self._monthly(), n_months_ahead=6)
        for val in result["projection"].values():
            assert val > 0

    def test_tendance_label(self):
        """Le champ 'tendance' est 'hausse', 'baisse' ou 'stable'."""
        result = project_prices(self._monthly(), n_months_ahead=3)
        assert result["tendance"] in ("hausse", "baisse", "stable")

    def test_variation_annuelle_pct_is_float(self):
        """variation_annuelle_pct est un float."""
        result = project_prices(self._monthly(), n_months_ahead=3)
        assert isinstance(result["variation_annuelle_pct"], float)

    def test_zero_months_ahead(self):
        """n_months_ahead=0 → projection vide."""
        result = project_prices(self._monthly(), n_months_ahead=0)
        assert len(result["projection"]) == 0
