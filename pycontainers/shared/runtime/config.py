DOCKER_ENDPOINT = {
    "backends": {
        "command": {"darwin": "container", "default": "docker", "id": "docker"}
    },
    "identifier": "/docker",
    "match": "/docker/**",
    "prefix": "/docker",
    "upstream": {"proxy": {"enabled": True}},
}

PODMAN_ENDPOINT = {
    "backends": {
        "command": {
            "darwin": "podman",
            "linux": "podman",
            "default": "podman",
            "id": "podman",
        }
    },
    "identifier": "/podman",
    "match": "/podman/**",
    "prefix": "/podman",
    "upstream": {"proxy": {"enabled": True}},
}

DOCKER_COMPOSE_ENDPOINT = {
    "backends": {
        "command": {
            "darwin": "docker-compose",
            "linux": "docker-compose",
            "default": "docker-compose",
            "id": "docker-compose",
        }
    },
    "identifier": "/docker-compose",
    "match": "/docker-compose/**",
    "prefix": "/docker-compose",
    "upstream": {"proxy": {"enabled": True}},
}

PODMAN_COMPOSE_ENDPOINT = {
    "backends": {
        "command": {
            "darwin": "podman-compose",
            "linux": "podman-compose",
            "default": "podman-compose",
            "id": "podman-compose",
        }
    },
    "identifier": "/podman-compose",
    "match": "/podman-compose/**",
    "prefix": "/podman-compose",
    "upstream": {"proxy": {"enabled": True}},
}

CONFIGURATION = {
    "version": "1.0",
    "name": "PyContainers",
    "server": {"type": "local"},
    "endpoints": [
        DOCKER_ENDPOINT,
        PODMAN_ENDPOINT,
        DOCKER_COMPOSE_ENDPOINT,
        PODMAN_COMPOSE_ENDPOINT,
    ],
}
