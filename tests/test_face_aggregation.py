from case_agent.pipelines import face_search


def test_aggregate_subject_summary():
    res = {
        'source': 'probe.jpg',
        'subject_matches': [
            {'subject': 'Alice', 'matches': [{'path': 'a1.jpg', 'distance': 0.3}, {'path': 'a2.jpg', 'distance': 0.4}]},
            {'subject': 'Bob', 'matches': [{'path': 'b1.jpg', 'distance': 0.6}]}
        ]
    }
    summary = face_search.aggregate_subject_summary(res)
    assert len(summary) == 2
    s = {x['subject']: x for x in summary}
    assert s['Alice']['best_distance'] == 0.3
    assert s['Alice']['best_path'] == 'a1.jpg'