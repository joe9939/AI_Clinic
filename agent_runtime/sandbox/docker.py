"""DockerSandbox — fully isolated execution via Docker containers.
Requires Docker and the 'docker' Python package (pip install docker).
"""
import os as _os
from .base import Sandbox

try:
    import docker
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False


class DockerSandbox(Sandbox):
    """Sandbox backed by a Docker container for full filesystem isolation.

    Each sandbox creates a lightweight container. All file operations
    run inside the container via exec. State can be diffed before/after.

    Requires: Docker daemon running, 'docker' Python package installed.
    """

    def __init__(self, image: str = "python:3.12-slim"):
        if not HAS_DOCKER:
            raise ImportError(
                "DockerSandbox requires the 'docker' package. "
                "Install with: pip install docker"
            )
        self._image = image
        self._container = None
        self.root_dir = "/workspace"

    async def start(self):
        client = docker.from_env()
        self._container = client.containers.run(
            image=self._image,
            command="tail -f /dev/null",
            detach=True,
            remove=True,
            working_dir=self.root_dir,
            stdin_open=True,
            tty=True,
        )
        self._container.exec_run(f"mkdir -p {self.root_dir}")

    async def stop(self):
        if self._container:
            try:
                self._container.kill()
            except Exception:
                pass
            self._container = None

    async def read_file(self, path: str) -> str:
        fpath = self._resolve(path)
        rc, output = self._container.exec_run(f"cat {fpath}")
        if rc != 0:
            raise FileNotFoundError(f"File not found: {path}")
        return output.decode("utf-8")

    async def write_file(self, path: str, content: str):
        fpath = self._resolve(path)
        parent = _os.path.dirname(fpath)
        self._container.exec_run(f"mkdir -p {parent}")
        import base64
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        self._container.exec_run(f"echo {encoded} | base64 -d > {fpath}")

    async def list_files(self, path: str = ".") -> list[str]:
        fpath = self._resolve(path)
        rc, output = self._container.exec_run(f"ls -1 {fpath}")
        if rc != 0:
            return []
        files = output.decode("utf-8").strip().split("\n")
        return sorted([f for f in files if f])

    async def exec_command(self, command: str) -> tuple[int, str]:
        rc, output = self._container.exec_run(
            ["sh", "-c", command],
            workdir=self.root_dir,
        )
        return rc, output.decode("utf-8", errors="replace")

    async def state(self) -> dict[str, str]:
        snapshot = {}
        rc, output = self._container.exec_run(
            f"find {self.root_dir} -type f 2>/dev/null"
        )
        if rc != 0:
            return snapshot
        raw = output.decode("utf-8").strip()
        if not raw:
            return snapshot
        for fpath in raw.split("\n"):
            fpath = fpath.strip()
            if not fpath:
                continue
            try:
                _, content = self._container.exec_run(f"cat {fpath}")
                rel = _os.path.relpath(fpath, self.root_dir)
                snapshot[rel] = content.decode("utf-8", errors="replace")
            except Exception:
                pass
        return snapshot

    def _resolve(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return _os.path.join(self.root_dir, path)
