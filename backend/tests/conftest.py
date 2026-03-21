import os
import pytest
import tempfile

# Set test environment variables BEFORE importing app
os.environ['LLM_API_KEY'] = 'test-key'
os.environ['ZEP_API_KEY'] = 'test-key'
os.environ['FLASK_DEBUG'] = 'False'


@pytest.fixture
def app():
    from app import create_app
    from app.config import Config

    class TestConfig(Config):
        TESTING = True
        DEBUG = False
        SECRET_KEY = 'test-secret-key'
        DB_PATH = os.path.join(tempfile.mkdtemp(), 'test.db')

    app = create_app(TestConfig)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
