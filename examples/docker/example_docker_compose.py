"""Compose project lifecycle and service-level accessors."""

from pycontainers import docker


def main() -> None:
    project = docker.compose(file="docker-compose.yml", project_name="demo")

    project.up(detach=True, build=True)
    for service in project.ps():
        print(service)

    web = project.service("web")
    print(web.logs(tail=20))
    print(web.exec("echo hello from compose"))

    project.down(volumes=True)


if __name__ == "__main__":
    main()
