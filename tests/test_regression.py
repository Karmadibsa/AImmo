from analysis.regression import predict, least_squares_fit, r_squared


def test_predict():
    """predict() calcule correctement y = alpha + beta*x."""
    alpha = 1
    beta = 2

    assert predict(alpha, beta, 3) == 7
    assert predict(alpha, beta, 0) == 1


def test_least_squares_fit():
    """least_squares_fit() retrouve la droite y = 2x + 1."""
    x = [1, 2, 3, 4, 5]
    y = [3, 5, 7, 9, 11]

    alpha, beta = least_squares_fit(x, y)

    assert abs(beta - 2.0) < 0.01
    assert abs(alpha - 1.0) < 0.01


def test_r_squared():
    """R² vaut 1 pour une relation parfaitement lineaire."""
    x = [1, 2, 3, 4, 5]
    y = [3, 5, 7, 9, 11]

    alpha, beta = least_squares_fit(x, y)

    r2 = r_squared(alpha, beta, x, y)

    assert abs(r2 - 1.0) < 0.01