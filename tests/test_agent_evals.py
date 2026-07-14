from evals.run_agent_evals import load_cases, run_evals


def test_agent_route_evals_pass():
    cases = load_cases()
    passed, failures = run_evals(cases)
    assert passed == len(cases), failures
