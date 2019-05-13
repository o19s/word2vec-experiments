import numpy as np

def random_projection(vecs):
    # Random projections
    # Create a random hyperplane into wordvecs,
    # then split into rhs (> 0) and lhs (<= 0)
    # Very naive split
    rand_vect = (np.random.choice(20, vecs.shape[1])/10)-1.0
    dots = np.dot(vecs, rand_vect)
    rhs = vecs[dots > 0]
    lhs = vecs[dots <= 0]
    return rand_vect, lhs, rhs
