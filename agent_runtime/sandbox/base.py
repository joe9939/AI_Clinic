"""Abstract Sandbox interface — defines the contract for isolated execution environments."""
from abc import ABC, abstractmethod
from typing import Self


class Sandbox(ABC):
    """Isolated execution environment for agent testing.
    
    A sandbox provides a controlled filesystem and command execution
    environment. Tools operate on the sandbox instead of the real system.
    """

    root_dir: str = ""

    @abstractmethod
    async def start(self):
        """Create and start the sandbox environment."""
        ...

    @abstractmethod
    async def stop(self):
        """Stop and destroy the sandbox, cleaning up all resources."""
        ...

    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read a file's contents. Raises FileNotFoundError if missing."""
        ...

    @abstractmethod
    async def write_file(self, path: str, content: str):
        """Write content to a file, creating parent directories as needed."""
        ...

    @abstractmethod
    async def list_files(self, path: str = ".") -> list[str]:
        """List files in a directory. Returns filenames only (no full paths)."""
        ...

    @abstractmethod
    async def exec_command(self, command: str) -> tuple[int, str]:
        """Execute a shell command. Returns (exit_code, stdout)."""
        ...

    @abstractmethod
    async def state(self) -> dict[str, str]:
        """Return a snapshot of all files and their contents.
        
        Used for diff-based verification: compare state before and after.
        """
        ...

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()
