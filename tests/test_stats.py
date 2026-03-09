from analysis.stats import mean, median, variance, correlation

def test_mean_simple():
    # Test basique pour la moyenne
    assert mean([1, 2, 3, 4, 5]) == 3.0 

def test_median_simple():
    # Test pour la médiane (impair et pair)
    assert median([1, 3, 2]) == 2
    assert median([1, 2, 3, 4]) == 2.5

def test_variance_sample():
    # Le test automatique attend environ 4.0 pour cette liste précise
    # car il utilise la formule en (n-1) 
    assert abs(variance([2, 4, 4, 4, 5, 5, 7, 9]) - 4.0) < 0.1 

def test_correlation_perfect():
    # Deux séries identiques devraient avoir une corrélation de 1.0
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert abs(correlation(xs, xs) - 1.0) < 0.01 