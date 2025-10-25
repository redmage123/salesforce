#!/usr/bin/env python3
"""
Terraform Manager - Infrastructure as Code build management

Handles Terraform operations:
- terraform init (initialize backend)
- terraform plan (preview changes)
- terraform apply (apply changes)
- terraform validate (syntax check)
- terraform fmt (format code)
"""

from pathlib import Path
from typing import Dict, List, Optional
from build_manager_base import BuildManagerBase, wrap_exception
from build_system_exceptions import BuildException
from build_manager_factory import register_build_manager, BuildSystem


@register_build_manager(BuildSystem.TERRAFORM)
class TerraformManager(BuildManagerBase):
    """Manages Terraform infrastructure operations"""

    @wrap_exception
    def __init__(self, project_dir: Path):
        super().__init__(project_dir)
        self.terraform_files = list(self.project_dir.glob("*.tf"))

    @property
    def name(self) -> str:
        return "terraform"

    @wrap_exception
    def detect(self) -> bool:
        """Detect if Terraform project"""
        return len(self.terraform_files) > 0 or (self.project_dir / "main.tf").exists()

    @wrap_exception
    def install_dependencies(self) -> bool:
        """Initialize Terraform backend and modules"""
        return self._run_command(["terraform", "init"])

    @wrap_exception
    def build(self) -> bool:
        """Validate and format Terraform code"""
        return (
            self._run_command(["terraform", "fmt", "-check"]) and
            self._run_command(["terraform", "validate"])
        )

    @wrap_exception
    def run_tests(self) -> bool:
        """Run Terraform plan (preview changes)"""
        return self._run_command(["terraform", "plan", "-detailed-exitcode"])

    @wrap_exception
    def clean(self) -> bool:
        """Clean Terraform state and cache"""
        import shutil
        terraform_dir = self.project_dir / ".terraform"
        terraform_dir.exists() and shutil.rmtree(terraform_dir)
        return True

    @wrap_exception
    def get_metadata(self) -> Dict:
        """Get Terraform project metadata"""
        return {
            "manager": "terraform",
            "terraform_files": [str(f.relative_to(self.project_dir)) for f in self.terraform_files],
            "has_backend": (self.project_dir / "backend.tf").exists(),
            "has_variables": (self.project_dir / "variables.tf").exists()
        }


if __name__ == "__main__":
    import sys
    manager = TerraformManager(Path.cwd())
    sys.exit(0 if manager.detect() else 1)
