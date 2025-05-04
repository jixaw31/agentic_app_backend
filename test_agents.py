from main import app
from sqlmodel import SQLModel, Session
from persistDB import create_engine, get_session
from fastapi.testclient import TestClient


def test_create_agent():
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override

        client = TestClient(app)

        payload = {
            "name": "TestAgent",
            "description": "A test agent for unit testing.",
            "welcomeMessage": "Hello, I am your assistant!",
            "systemPrompt": "You are helpful and concise.",
            "responseSettings": {
                "tone": "friendly",
                "verbosity": "medium",
                "creativity": 0.7
            }
        }

        response = client.post("/agents/", json=payload)
        app.dependency_overrides.clear()
        data = response.json()

        assert response.status_code == 200
        assert data["name"] == "TestAgent"
        assert data["description"] == "A test agent for unit testing."
        assert data["welcomeMessage"] == "Hello, I am your assistant!"
        assert data["systemPrompt"] == "You are helpful and concise."
        assert data["tone"] == "friendly"
        assert data["verbosity"] == "medium"
        assert data["creativity"] == 0.7
        assert "id" in data


def test_list_agents():
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override

        client = TestClient(app)

        # Create two agents
        payload_1 = {
            "name": "Agent One",
            "description": "First test agent.",
            "welcomeMessage": "Welcome, I'm Agent One.",
            "systemPrompt": "Be smart and quick.",
            "responseSettings": {
                "tone": "formal",
                "verbosity": "low",
                "creativity": 0.5
            }
        }

        payload_2 = {
            "name": "Agent Two",
            "description": "Second test agent.",
            "welcomeMessage": "Hi, Agent Two here!",
            "systemPrompt": "Respond humorously.",
            "responseSettings": {
                "tone": "funny",
                "verbosity": "high",
                "creativity": 0.9
            }
        }

        client.post("/agents/", json=payload_1)
        client.post("/agents/", json=payload_2)

        # Get all agents
        response = client.get("/agents/")
        app.dependency_overrides.clear()
        data = response.json()

        assert response.status_code == 200
        assert isinstance(data, list)
        assert len(data) >= 2

        names = [agent["name"] for agent in data]
        assert "Agent One" in names
        assert "Agent Two" in names


def test_get_agent():
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override

        client = TestClient(app)

        # Create an agent
        payload = {
            "name": "Solo Agent",
            "description": "Only one agent in this test.",
            "welcomeMessage": "Hello, Solo Agent at your service.",
            "systemPrompt": "Respond calmly.",
            "responseSettings": {
                "tone": "calm",
                "verbosity": "medium",
                "creativity": 0.7
            }
        }

        create_response = client.post("/agents/", json=payload)
        assert create_response.status_code == 200
        agent_data = create_response.json()
        agent_id = agent_data["id"]

        # Fetch the agent by ID
        get_response = client.get(f"/agents/{agent_id}")
        app.dependency_overrides.clear()
        data = get_response.json()

        assert get_response.status_code == 200
        assert data["name"] == "Solo Agent"
        assert data["description"] == "Only one agent in this test."
        assert data["tone"] == "calm"
        assert data["creativity"] == 0.7


def test_update_response_settings():
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override

        client = TestClient(app)

        # Create an agent
        payload = {
            "name": "Solo Agent",
            "description": "Only one agent in this test.",
            "welcomeMessage": "Hello, Solo Agent at your service.",
            "systemPrompt": "Respond calmly.",
            "responseSettings": {
                "tone": "calm",
                "verbosity": "medium",
                "creativity": 0.7
            }
        }

        create_response = client.post("/agents/", json=payload)
        assert create_response.status_code == 200
        agent_data = create_response.json()
        agent_id = agent_data["id"]

        # Make sure the agent is created properly by checking the response
        get_response = client.get(f"/agents/{agent_id}")
        assert get_response.status_code == 200

        # Update response settings for the created agent
        update_payload = {
            "responseSettings": {
                "tone": "friendly",
                "verbosity": "high",
                "creativity": 0.9
                }
            }
        
        # Update the agent's response settings
        update_response = client.put(f"/agents/{agent_id}/response-settings", json=update_payload)
        # app.dependency_overrides.clear()

        # Check if the response status is correct
        assert update_response.status_code == 200
        updated_agent = update_response.json()
        assert updated_agent["tone"] == "friendly"
        assert updated_agent["verbosity"] == "high"
        assert updated_agent["creativity"] == 0.9

        # Fetch the updated agent to verify changes
        get_response = client.get(f"/agents/{agent_id}")
        # classic fastAPI
        app.dependency_overrides.clear()
        get_agent = get_response.json()

        assert get_response.status_code == 200
        assert get_agent["tone"] == "friendly"
        assert get_agent["verbosity"] == "high"
        assert get_agent["creativity"] == 0.9


def test_update_system_prompt():
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    # Override to use the test database session
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)

    # Create an agent
    payload = {
        "name": "Solo Agent",
        "description": "Only one agent in this test.",
        "welcomeMessage": "Hello, Solo Agent at your service.",
        "systemPrompt": "Respond calmly.",
        "responseSettings": {
            "tone": "calm",
            "verbosity": "medium",
            "creativity": 0.7
        }
    }

    create_response = client.post("/agents/", json=payload)
    assert create_response.status_code == 200
    agent_data = create_response.json()
    agent_id = agent_data["id"]

    # Step 2: Update system prompt
    update_payload = {
        "systemPrompt": "Respond with enthusiasm and energy!"
    }

    update_response = client.put(
        f"/agents/{agent_id}/system-prompt", json=update_payload
    )
    assert update_response.status_code == 200

    updated_agent = update_response.json()
    assert updated_agent["systemPrompt"] == "Respond with enthusiasm and energy!"

    app.dependency_overrides.clear()


def test_delete_agent():
    engine = create_engine(
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)

    # Override to use the test database session
    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)

    # Step 1: Create an agent
    # Create an agent
    payload = {
        "name": "Solo Agent",
        "description": "Only one agent in this test.",
        "welcomeMessage": "Hello, Solo Agent at your service.",
        "systemPrompt": "Respond calmly.",
        "responseSettings": {
            "tone": "calm",
            "verbosity": "medium",
            "creativity": 0.7
        }
    }

    create_response = client.post("/agents/", json=payload)
    assert create_response.status_code == 200
    agent_data = create_response.json()
    agent_id = agent_data["id"]

    # Step 2: Delete the agent
    delete_response = client.delete(f"/agents/{agent_id}")
    assert delete_response.status_code == 200  # or 204 depending on your response

    # Verify the message in the response
    delete_message = delete_response.json()
    assert delete_message["message"] == f"Agent with ID: {agent_id} deleted successfully."

    # Step 3: Try fetching the deleted agent (should return 404)
    get_response = client.get(f"/agents/{agent_id}")
    assert get_response.status_code == 404  # agent should no longer exist

    app.dependency_overrides.clear()






