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

CONFIGURATION = {
    "version": "1.0",
    "name": "PyContainers",
    "server": {"type": "local"},
    "endpoints": [DOCKER_ENDPOINT, PODMAN_ENDPOINT],
}
