from fastapi.testclient import TestClient
from main import app, get_db
from models import User
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

client = TestClient(app)

def fake_get_current_user():
    return User(id=1, email="test@test.com", name="test")

from auth import get_current_user
app.dependency_overrides[get_current_user] = fake_get_current_user

def test_voice_process():
    res = client.post("/api/voice/process", json={"transcript": "I have an exam tomorrow."})
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert data["data"]["intent"] == "add_task"
