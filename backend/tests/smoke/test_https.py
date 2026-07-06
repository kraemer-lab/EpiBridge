import httpx2 as httpx


def test_health_endpoint_over_https():
    response = httpx.get(
        "https://localhost/api/health",
        verify=False,
        timeout=10,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
