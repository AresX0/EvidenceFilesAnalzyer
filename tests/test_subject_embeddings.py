import numpy as np
from case_agent.pipelines import face_search


def test_compute_subject_embeddings():
    labeled = {
        'A': [{'path':'a1', 'embedding': np.ones(4)*0.1}, {'path':'a2', 'embedding': np.ones(4)*0.1}],
        'B': [{'path':'b1', 'embedding': np.ones(4)*0.9}]
    }
    subj = face_search._compute_subject_embeddings(labeled)
    assert 'A' in subj and 'B' in subj
    # Embeddings should be numpy arrays and normalized
    import numpy as _np
    assert abs(_np.linalg.norm(subj['A']) - 1.0) < 1e-6
    assert subj['A'].shape[0] == 4
