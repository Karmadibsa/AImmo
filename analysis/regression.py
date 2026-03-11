"""
Regression lineaire simple from scratch.
Reference : Joel Grus, "Data Science From Scratch", chapitre 14.

IMPORTANT : N'importez pas pour ces fonctions.
"""

# from analysis.stats import mean, variance, covariance, correlation
from analysis.stats import mean, variance, covariance, correlation, standard_deviation




def predict(alpha: float, beta: float, x_i: float) -> float:
    """Predit y pour une valeur x : y = alpha + beta * x."""
    return beta * x_i + alpha


def error(alpha: float, beta: float, x_i: float, y_i: float) -> float:
    """Calcule l'erreur de prediction pour un point."""
    return predict(alpha, beta, x_i) - y_i

# def error(alpha: float, beta: float, x_i: float, y_i: float) -> float:
#     return y_i - predict(alpha, beta, x_i)


def sum_of_sqerrors(alpha: float, beta: float, x: list, y: list) -> float:
    """Somme des erreurs au carre sur tous les points."""
    return sum(error(alpha, beta, x_i, y_i) ** 2 
        for x_i, y_i in zip(x, y))


def least_squares_fit(x: list[float], y: list[float]) -> tuple[float, float]:
    """
    Trouve alpha et beta qui minimisent la somme des erreurs au carre.
    Retourne (alpha, beta) tels que y ≈ alpha + beta * x.
    """

    beta = correlation(x, y) * standard_deviation(y) / standard_deviation(x)
    alpha = mean(y) - beta * mean(x)
    return alpha, beta

    # # Calcule de beta (pente)
    # beta = covariance(x, y) / variance(x)

    # # Calcule d'alpha (ordonnée à l'origine)
    # alpha = mean(y) - beta * mean(x)

    # return alpha, beta

def r_squared(alpha: float, beta: float, x: list, y: list) -> float:
    """
    Coefficient de determination R².
    R² = 1 - (SS_res / SS_tot)
    1.0 = ajustement parfait, 0.0 = le modele n'explique rien.
    """

    # return 1.0 - (sum_of_sqerrors(alpha, beta, x, y)/ total_sum_of_squares(y))

    # Erreur du modèle
    ss_res = sum_of_sqerrors(alpha, beta, x, y)

    # Erreur de la moyenne
    mean_y = mean(y)
    ss_tot = sum((y_i - mean_y) ** 2 for y_i in y)
    
    # R²
    r2 = 1.0 - (ss_res / ss_tot)
    
    return r2