from pycontainers import PyContainers
from pycontainers.features.docker import Container


def test_model():
    user_data = {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "profile": {"age": 30, "city": "NYC"},
    }

    container = Container(parent=PyContainers(), **user_data)
    assert container.id == 1
    assert container.name == "Alice"


def test_model_config_env_is_dict():
    container = Container(
        parent=PyContainers(),
        config={"env": ["var1=one", "var2=two", "empty"]},
    )

    assert isinstance(container.config.env, dict)
    assert container.config.env == {
        "var1": "one",
        "var2": "two",
        "empty": "",
    }
