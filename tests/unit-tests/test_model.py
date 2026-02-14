from pycontainer import PyContainer
from pycontainer.pycontainer import Container


def test_model():
    user_data = {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "profile": {"age": 30, "city": "NYC"},
    }

    container = Container(parent=PyContainer(), **user_data)
    assert container.id == 1
    assert container.name == "Alice"
