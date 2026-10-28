# Two launchers share Qt and Python in one directory: quiet GUI + stdio MCP console.
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = Path(SPECPATH).parent
windows = __import__("sys").platform == "win32"
options = {"icon": str(root / "packaging" / "tutor.ico"),
           "manifest": str(root / "packaging" / "windows.manifest")} if windows else {}
a = Analysis([str(root / "src" / "computer_tutor" / "__main__.py")],
             pathex=[str(root / "src")],
             hiddenimports=(collect_submodules("computer_tutor")
                            + collect_submodules("mcp.server.fastmcp")),
             datas=copy_metadata("mcp"))
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ComputerTutor",
          console=False, **options)
mcp = EXE(pyz, a.scripts, [], exclude_binaries=True, name="computer-tutor-mcp",
          console=True, **options)
coll = COLLECT(gui, mcp, a.binaries, a.datas, name="ComputerTutor")
