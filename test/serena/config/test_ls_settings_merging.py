import shutil
import tempfile
from pathlib import Path

from serena.config.serena_config import ProjectConfig, SerenaConfig
from serena.project import Project
from solidlsp.ls_config import Language


class TestLSSettingsMerging:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.tmp_dir)
        (self.project_root / ".serena").mkdir()

        # Create a dummy python file for indexing
        (self.project_root / "test.py").write_text("print('hello')")

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_settings_merging(self):
        # 1. Global config with some settings
        global_config = SerenaConfig()
        global_config.ls_specific_settings = {
            Language.PYTHON: {"global_key": "global_val", "override_key": "global_val"},
            Language.CPP: {"cpp_global": "val"},
        }

        # 2. Project config with overrides
        project_yaml = """
project_name: test_project
languages: [python]
ls_specific_settings:
  python:
    override_key: project_val
    project_key: project_val
"""
        yaml_path = self.project_root / ".serena" / "project.yml"
        yaml_path.write_text(project_yaml)

        project_config = ProjectConfig.load(self.project_root)
        project = Project(project_root=str(self.project_root), project_config=project_config, serena_config=global_config)

        # 3. Create LS manager and check merged settings
        # We need to mock LanguageServerFactory or check the factory created by the project
        project.create_language_server_manager()

        # Internal check: project.language_server_manager has the factory
        # which has ls_specific_settings
        merged_settings = project.language_server_manager._language_server_factory.ls_specific_settings

        # Check Python settings
        python_settings = merged_settings.get(Language.PYTHON, {})
        assert python_settings.get("global_key") == "global_val"
        assert python_settings.get("override_key") == "project_val"
        assert python_settings.get("project_key") == "project_val"

        # Check CPP settings (should persist from global)
        cpp_settings = merged_settings.get(Language.CPP, {})
        assert cpp_settings.get("cpp_global") == "val"

    def test_ls_path_config_case_insensitivity(self):
        # Verify that 'CPP' or 'cpp' in YAML both map to Language.CPP
        project_yaml = """
project_name: test_project
languages: [cpp]
ls_specific_settings:
  CPP:
    ls_path: /custom/path
"""
        yaml_path = self.project_root / ".serena" / "project.yml"
        yaml_path.write_text(project_yaml)

        project_config = ProjectConfig.load(self.project_root)
        assert Language.CPP in project_config.ls_specific_settings
        assert project_config.ls_specific_settings[Language.CPP]["ls_path"] == "/custom/path"
