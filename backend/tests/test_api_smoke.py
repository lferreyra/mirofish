"""Smoke tests for API endpoints."""


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['service'] == 'MiroFish Backend'


def test_list_projects_empty(client):
    response = client.get('/api/graph/project/list')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True


def test_list_tasks_empty(client):
    response = client.get('/api/graph/tasks')
    assert response.status_code == 200


def test_nonexistent_project(client):
    response = client.get('/api/graph/project/nonexistent_id')
    assert response.status_code in (404, 200)  # May return 200 with success=false


def test_auth_required_when_configured(app):
    import os
    os.environ['MIROFISH_API_KEY'] = 'test-api-key-12345'
    try:
        client = app.test_client()
        # Without auth header - should get 401
        response = client.get('/api/graph/project/list')
        assert response.status_code == 401

        # With correct auth header - should work
        response = client.get(
            '/api/graph/project/list',
            headers={'Authorization': 'Bearer test-api-key-12345'}
        )
        assert response.status_code == 200

        # Health check should bypass auth
        response = client.get('/health')
        assert response.status_code == 200
    finally:
        del os.environ['MIROFISH_API_KEY']
