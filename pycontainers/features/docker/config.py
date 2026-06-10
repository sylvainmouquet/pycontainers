CONFIGURATION = {
    "version": "1.0",
    "name": "PyContainers",
    "server": {"type": "local"},
    "endpoints": [
        {
            "backends": {
                "command": {"darwin": "docker", "default": "docker", "id": "docker"}
            },
            "identifier": "/docker",
            "match": "/docker/**",
            "prefix": "/docker",
            "upstream": {"proxy": {"enabled": True}},
        }
    ],
}
