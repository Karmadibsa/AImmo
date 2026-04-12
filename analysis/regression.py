"""
Regression lineaire simple from scratch.
Reference : Joel Grus, "Data Science From Scratch", chapitre 14.

IMPORTANT : N'importez pas numpy, pandas ou les bibliothèques ML pour ces fonctions.
Implémentez-les avec du Python pur (listes, boucles, math).
"""

import math

from analysis.stats import mean, variance, covariance, correlation, standard_deviation


def predict(alpha: float, beta: float, x_i: float) -> float:
    """
    Prédit y pour une valeur x selon le modèle linéaire y = alpha + beta × x.

    Formule : ŷ = alpha + beta × x_i

    Args:
        alpha (float): Ordonnée à l'origine (intercept).
        beta (float): Pente de la droite de régression.
        x_i (float): Valeur de la variable explicative.

    Returns:
        float: Valeur prédite ŷ.
    """
    return beta * x_i + alpha


def error(alpha: float, beta: float, x_i: float, y_i: float) -> float:
    """
    Calcule l'erreur de prédiction pour un point (résidu).

    Formule : ŷ - y_i  (positif = sur-estimation, négatif = sous-estimation)

    Args:
        alpha (float): Ordonnée à l'origine.
        beta (float): Pente.
        x_i (float): Valeur observée de x.
        y_i (float): Valeur observée de y.

    Returns:
        float: Résidu (predict - y_i).
    """
    return predict(alpha, beta, x_i) - y_i


def sum_of_sqerrors(alpha: float, beta: float, x: list, y: list) -> float:
    """
    Calcule la somme des erreurs au carré (SS_res) sur tous les points.

    Formule : Σ (ŷ_i - y_i)²

    Args:
        alpha (float): Ordonnée à l'origine.
        beta (float): Pente.
        x (list): Valeurs observées de x.
        y (list): Valeurs observées de y.

    Returns:
        float: Somme des carrés des résidus.
    """
    return sum(error(alpha, beta, x_i, y_i) ** 2 for x_i, y_i in zip(x, y))


def least_squares_fit(x: list[float], y: list[float]) -> tuple[float, float]:
    """
    Trouve alpha et beta qui minimisent la somme des erreurs au carré (OLS).

    Formules :
        beta  = corr(x, y) × σ_y / σ_x
        alpha = ȳ − beta × x̄

    Args:
        x (list[float]): Valeurs de la variable explicative (ex. surface).
        y (list[float]): Valeurs de la variable cible (ex. prix).

    Returns:
        tuple[float, float]: (alpha, beta) tels que y ≈ alpha + beta × x.
    """
    beta = correlation(x, y) * standard_deviation(y) / standard_deviation(x)
    alpha = mean(y) - beta * mean(x)
    return alpha, beta


def r_squared(alpha: float, beta: float, x: list, y: list) -> float:
    """
    Coefficient de détermination R².

    Formule : R² = 1 − SS_res / SS_tot
        SS_res = Σ (ŷ_i − y_i)²   (erreur du modèle)
        SS_tot = Σ (y_i − ȳ)²     (erreur de la moyenne)

    Valeurs : 1.0 = ajustement parfait, 0.0 = modèle sans pouvoir explicatif.

    Robuste aux données manquantes : filtre automatiquement les paires
    où x_i ou y_i est None ou NaN.

    Args:
        alpha (float): Ordonnée à l'origine du modèle.
        beta (float): Pente du modèle.
        x (list): Valeurs observées de x (peut contenir None/NaN).
        y (list): Valeurs observées de y (peut contenir None/NaN).

    Returns:
        float: R² ∈ [0, 1]. Retourne 0.0 si moins de 2 points valides.
    """
    # Filtre des paires invalides (None ou NaN)
    pairs = [
        (x_i, y_i) for x_i, y_i in zip(x, y)
        if x_i is not None and y_i is not None
        and not (isinstance(x_i, float) and math.isnan(x_i))
        and not (isinstance(y_i, float) and math.isnan(y_i))
    ]
    if len(pairs) < 2:
        return 0.0

    x_clean = [p[0] for p in pairs]
    y_clean = [p[1] for p in pairs]

    ss_res = sum_of_sqerrors(alpha, beta, x_clean, y_clean)
    mean_y = mean(y_clean)
    ss_tot = sum((y_i - mean_y) ** 2 for y_i in y_clean)

    if ss_tot == 0:
        return 0.0

    return 1.0 - (ss_res / ss_tot)
