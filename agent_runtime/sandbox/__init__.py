"""Sandbox — isolated execution environments for agent testing."""
from .base import Sandbox
from .local import LocalSandbox

try:
    from .docker import DockerSandbox
    HAS_DOCKER = True
except ImportError:
    DockerSandbox = None  # type: ignore
    HAS_DOCKER = False

__all__ = ["Sandbox", "LocalSandbox", "DockerSandbox"]
