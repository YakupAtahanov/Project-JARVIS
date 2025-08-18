import platform
import shutil
import subprocess

class TerminalManager:
    def __init__(self):
        self.system = platform.system().lower()
        self.release = platform.release()
        self.version = platform.version()
        self.machine = platform.machine()

        if self.system == "windows":
            # Pick shell: PowerShell Core → Windows PowerShell → cmd
            if shutil.which("pwsh"):
                self.shell = ["pwsh", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]
            elif shutil.which("powershell"):
                self.shell = ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]
            else:
                self.shell = ["cmd.exe", "/d", "/s", "/c"]
        else:
            # Linux / macOS
            if shutil.which("bash"):
                self.shell = ["bash", "-lc"]
            else:
                self.shell = ["sh", "-lc"]

    def run_command(self, cmd: str):
        result = subprocess.run(
            self.shell + [cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    
    def show_specs(self):
        print("OS Specifications:")
        print(f"\t* System: {self.system}")
        print(f"\t* Release: {self.release}")
        print(f"\t* Version: {self.version}")
        print(f"\t* Machine: {self.machine}")
        print(f"\t* Shell: {self.shell}")