import numpy as np

def take_fractional(X, idx_frac):
    """
        Obtain the value of a numpy nd-array X at given fractional indices.
        -> linear interpolation
    """
    weights = []
    results = []
    grad = np.array(np.gradient(X))
    idx_frac = np.array(idx_frac)
    idx = idx_frac.astype(int)
    x = X[tuple(idx)]
    # dx = [com[i]%1 * grad[i][tuple(idx)] for i in range(len(com))]
    dx = idx_frac%1 * grad[(slice(None),)+tuple(idx)]
    return x + dx.sum()
