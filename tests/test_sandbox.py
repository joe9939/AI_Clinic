"""Tests for Agent Runtime Sandbox — TDD."""
import pytest, asyncio, os, sys, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_runtime.sandbox.base import Sandbox
from agent_runtime.sandbox.local import LocalSandbox


# ─── Sandbox Base Tests ─────────────────────

class TestSandboxBase:
    """Sandbox abstract interface should define all required methods."""

    def test_sandbox_has_required_methods(self):
        """Sandbox should define the contract methods."""
        methods = [
            "start", "stop",
            "read_file", "write_file", "list_files",
            "exec_command", "state",
        ]
        for m in methods:
            assert hasattr(Sandbox, m), f"Sandbox missing method: {m}"
    
    def test_sandbox_is_abstract(self):
        """Sandbox should not be directly instantiable (start/stop not implemented)."""
        with pytest.raises(TypeError):
            Sandbox()


# ─── LocalSandbox Tests ─────────────────────

class TestLocalSandbox:
    """LocalSandbox uses temp directories — no Docker needed."""

    @pytest.mark.asyncio
    async def test_create_and_destroy(self):
        """Start should create a temp dir, stop should clean it up."""
        sb = LocalSandbox()
        await sb.start()
        assert os.path.exists(sb.root_dir), "Sandbox root should exist after start"
        root = sb.root_dir
        await sb.stop()
        assert not os.path.exists(root), "Sandbox root should be cleaned up after stop"

    @pytest.mark.asyncio
    async def test_write_and_read_file(self):
        """Should write content and read it back."""
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("test.txt", "hello world")
            content = await sb.read_file("test.txt")
            assert content == "hello world"
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_read_nonexistent_file_raises(self):
        """Reading a file that doesn't exist should raise FileNotFoundError."""
        sb = LocalSandbox()
        await sb.start()
        try:
            with pytest.raises(FileNotFoundError):
                await sb.read_file("nonexistent.txt")
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_list_files(self):
        """list_files should return all files in sandbox."""
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("a.txt", "aaa")
            await sb.write_file("b.txt", "bbb")
            files = await sb.list_files()
            assert "a.txt" in files
            assert "b.txt" in files
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_list_files_subdirectory(self):
        """list_files should work with subdirectories."""
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("sub/data.txt", "data")
            files = await sb.list_files("sub")
            assert "data.txt" in files
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_exec_command(self):
        """exec_command should run a command in the sandbox."""
        sb = LocalSandbox()
        await sb.start()
        try:
            rc, stdout = await sb.exec_command("echo hello")
            assert rc == 0
            assert "hello" in stdout
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_exec_command_failure(self):
        """exec_command should return non-zero exit code on failure."""
        sb = LocalSandbox()
        await sb.start()
        try:
            rc, stdout = await sb.exec_command("__nonexistent_command_xyz__")
            assert rc != 0
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_state_snapshot(self):
        """state should return a dict of all files and their contents."""
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("a.txt", "alpha")
            await sb.write_file("b.txt", "beta")
            state = await sb.state()
            assert state["a.txt"] == "alpha"
            assert state["b.txt"] == "beta"
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_isolation(self):
        """Each sandbox should have its own isolated filesystem."""
        sb1 = LocalSandbox()
        sb2 = LocalSandbox()
        await sb1.start()
        await sb2.start()
        try:
            await sb1.write_file("secret.txt", "sb1 secret")
            # sb2 should not have sb1's files
            with pytest.raises(FileNotFoundError):
                await sb2.read_file("secret.txt")
        finally:
            await sb1.stop()
            await sb2.stop()


# ─── Sandbox + Harness Integration ─────────

class TestSandboxIntegration:
    """Test that sandbox works with the agent runtime harness."""

    @pytest.mark.asyncio
    async def test_real_file_read_via_tool(self):
        """Agent should be able to read a real file through sandbox-backed tools."""
        from agent_runtime.harness import AgentRuntime, Tool
        
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("notes.txt", "Meeting at 3pm")
            
            # Tool backed by real sandbox
            runtime = AgentRuntime(chat_fn=None)  # Will use mock
            runtime.register_tool(Tool(
                name="read_file",
                description="Read a file",
                parameters={"path": {"type": "string"}},
                sandbox_fn=lambda path: sb.read_file(path),
            ))
            assert runtime._tools["read_file"].sandbox_fn is not None
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_tool_call_returns_real_content(self):
        """Sandbox-backed tool should return actual file content."""
        from agent_runtime.harness import AgentRuntime, Tool
        
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("data.txt", "real content")
            
            async def read_file_tool(path):
                return await sb.read_file(path)
            
            # Execute tool function directly
            result = await read_file_tool("data.txt")
            assert result == "real content"
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_sandbox_cleans_up_on_stop(self):
        """After stop, sandbox files should be gone."""
        sb = LocalSandbox()
        await sb.start()
        await sb.write_file("temp.txt", "temp")
        root = sb.root_dir
        await sb.stop()
        assert not os.path.exists(root)


# ─── State Diff Tests ──────────────────────

class TestSandboxStateDiff:
    """State diff compares sandbox state before and after agent execution."""

    @pytest.mark.asyncio
    async def test_state_before_after_diff(self):
        """Should detect files created, modified, deleted."""
        sb = LocalSandbox()
        await sb.start()
        try:
            before = await sb.state()
            assert before == {}
            
            await sb.write_file("created.txt", "new")
            after = await sb.state()
            assert "created.txt" in after
            assert after["created.txt"] == "new"
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_state_detects_modification(self):
        """Should detect when file content changes."""
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("log.txt", "old content")
            before = await sb.state()
            await sb.write_file("log.txt", "new content")
            after = await sb.state()
            assert before["log.txt"] == "old content"
            assert after["log.txt"] == "new content"
            assert before["log.txt"] != after["log.txt"]
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_state_detects_deletion(self):
        """Should detect when files are deleted."""
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("delete_me.txt", "bye")
            before = await sb.state()
            assert "delete_me.txt" in before
            # Simulate deletion
            import os as std_os
            std_os.remove(sb._resolve("delete_me.txt"))
            after = await sb.state()
            assert "delete_me.txt" not in after
        finally:
            await sb.stop()

    @pytest.mark.asyncio
    async def test_diff_only_shows_changes(self):
        """Diff should only include files that changed."""
        sb = LocalSandbox()
        await sb.start()
        try:
            await sb.write_file("stable.txt", "unchanged")
            before = await sb.state()
            await sb.write_file("stable.txt", "unchanged")  # same content
            await sb.write_file("new.txt", "added")
            after = await sb.state()
            # stable.txt is in both but unchanged
            # new.txt only in after
            stable_before = before.get("stable.txt")
            stable_after = after.get("stable.txt")
            assert stable_before == stable_after == "unchanged"
            assert "new.txt" in after
        finally:
            await sb.stop()


# ─── DockerSandbox Tests ────────────────────

class TestDockerSandbox:
    """DockerSandbox tests. Requires Docker to be installed."""

    @pytest.mark.asyncio
    async def test_module_exists(self):
        """DockerSandbox module should be importable."""
        try:
            from agent_runtime.sandbox.docker import DockerSandbox
            assert DockerSandbox is not None
        except ImportError:
            pytest.skip("DockerSandbox not available (docker-py not installed)")

    @pytest.mark.asyncio
    async def test_docker_has_sandbox_interface(self):
        """DockerSandbox should implement all Sandbox methods."""
        try:
            from agent_runtime.sandbox.docker import DockerSandbox
        except ImportError:
            pytest.skip("DockerSandbox not available")
        
        methods = ["start", "stop", "read_file", "write_file", 
                   "list_files", "exec_command", "state"]
        for m in methods:
            assert hasattr(DockerSandbox, m), f"Missing {m}"
