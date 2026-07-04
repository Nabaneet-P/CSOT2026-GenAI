import re
from pathlib import Path

def load_skill(name: str) -> dict:
    safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
    project_root = Path(__file__).parent.parent.absolute()
    skill_file = project_root / "skills" / safe_name / "SKILL.md"
    if not skill_file.exists():
        return {"success": False, "error": f"Requested skill workflow execution '{name}' not found."}
    try:
        content = skill_file.read_text(encoding="utf-8")
        body_only = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL | re.MULTILINE)
        return {
            "success": True,
            "content": f"Skill workflow '{name}' loaded successfully. Execute these steps:\n\n{body_only.strip()}"
        }
    except Exception as e:
        return {"success": False, "error": f"Failed reading execution layer data: {str(e)}"}