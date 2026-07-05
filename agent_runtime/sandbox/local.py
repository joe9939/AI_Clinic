"""LocalSandbox — uses a temporary directory for isolated execution. No Docker needed."""
import os, asyncio, tempfile, shutil
from pathlib import Path
from .base import Sandbox


class LocalSandbox(Sandbox):
    """Sandbox backed by a local temporary directory.
    
    Files are real but isolated — each sandbox gets its own temp dir
    that is destroyed on stop(). Works on any system without Docker.
    """

    def __init__(self):
        self._tmpdir = None
        self.root_dir = ""

    async def start(self):
        self._tmpdir = tempfile.mkdtemp(prefix="ai_clinic_sandbox_")
        self.root_dir = self._tmpdir

    async def stop(self):
        if self._tmpdir and os.path.exists(self._tmpdir):
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
            self.root_dir = ""

    def _resolve(self, path: str) -> str:
        """Resolve a relative path to an absolute path inside the sandbox."""
        # Security: prevent path traversal outside sandbox
        resolved = os.path.normpath(os.path.join(self.root_dir, path))
        if not resolved.startswith(os.path.normpath(self.root_dir)):
            raise PermissionError(f"Path traversal detected: {path}")
        return resolved

    async def read_file(self, path: str) -> str:
        resolved = self._resolve(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"File not found: {path}")
        with open(resolved, "r", encoding="utf-8") as f:
            return f.read()

    async def write_file(self, path: str, content: str):
        resolved = self._resolve(path)
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)

    async def list_files(self, path: str = ".") -> list[str]:
        resolved = self._resolve(path)
        if not os.path.exists(resolved):
            return []
        entries = []
        for entry in os.listdir(resolved):
            if os.path.isfile(os.path.join(resolved, entry)):
                entries.append(entry)
        return sorted(entries)

    async def exec_command(self, command: str) -> tuple[int, str]:
        """Run a shell command inside the sandbox directory."""
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.root_dir,
            shell=True,
        )
        stdout, _ = await proc.communicate()
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace")

    async def state(self) -> dict[str, str]:
        """Return all files and their contents as a flat dict."""
        snapshot = {}
        for root, dirs, files in os.walk(self.root_dir):
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, self.root_dir)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        snapshot[rel] = f.read()
                except (UnicodeDecodeError, IOError):
                    snapshot[rel] = "<binary>"
        return snapshot
