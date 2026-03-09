"""
Fonctions statistiques from scratch.
Reference : Joel Grus, "Data Science From Scratch", chapitre 5.

IMPORTANT : N'importez pas numpy, pandas ou statistics pour ces fonctions.
Implementez-les avec du Python pur (listes, boucles, math).
"""

import math

def dot(v: list[float], w: list[float]) -> float:
    """Multiplie les éléments correspondants et fait la somme : v_1*w_1 + ... + v_n*w_n"""
    return sum(v_i * w_i for v_i, w_i in zip(v, w))


""" MOYENNE """
def mean(xs: list[float]) -> float:
    """Retourne la moyenne d'une liste de nombres."""
    return sum(xs) / len(xs)

""" MEDIANE """
def _median_odd(xs: list[float]) -> float:
    """len(xs) est impair, la médiane est l'élément du milieu de la liste triée."""
    return sorted(xs)[len(xs) // 2]

def _median_even(xs: list[float]) -> float:
    """len(xs) est pair, la médiane est la moyenne des deux éléments du milieu de la liste triée."""
    sorted_xs = sorted(xs)
    mid = len(xs) // 2
    return (sorted_xs[mid - 1] + sorted_xs[mid]) / 2

def median(xs: list[float]) -> float:
    """Retourne la mediane d'une liste de nombres."""
    return _median_even(xs) if len(xs) % 2 == 0 else _median_odd(xs)


""" VARIANCE """
def de_mean(xs: list[float]) -> list[float]:
    x_bar = mean(xs)
    return [x - x_bar for x in xs]

def variance(xs: list[float]) -> float:
    """Retourne la variance d'une liste de nombres."""
    assert len(xs) >= 2, "la variance nécessite au moins deux éléments"
    n = len(xs)
    deviations = de_mean(xs)
    return sum(x ** 2 for x in deviations) / (n)


""" ECART-TYPE, COVARIANCE, CORRELATION """
def standard_deviation(xs: list[float]) -> float:
    """Retourne l'ecart-type d'une liste de nombres."""
    return math.sqrt(variance(xs))


def covariance(xs: list[float], ys: list[float]) -> float:
    """Retourne la covariance entre deux series."""
    assert len(xs) == len(ys), "xs et ys doivent être de même taille"  
    return dot(de_mean(xs), de_mean(ys)) / (len(xs) - 1)
    


def correlation(xs: list[float], ys: list[float]) -> float:
    """
    Retourne le coefficient de correlation de Pearson entre deux series.
    Retourne 0 si l'une des series a un ecart-type nul.
    """
    stdev_x = standard_deviation(xs)  
    stdev_y = standard_deviation(ys)  
    if stdev_x > 0 and stdev_y > 0:    
        return covariance(xs, ys) / stdev_x / stdev_y  
    else:    
        return 0
   
