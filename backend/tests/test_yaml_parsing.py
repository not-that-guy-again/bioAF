import pytest

from app.services.environment_service import EnvironmentService


SAMPLE_CONDA_YAML = """name: bioaf-scrna
channels:
  - conda-forge
  - bioconda
  - defaults
dependencies:
  - python=3.11
  - scanpy>=1.10
  - anndata>=0.10
  - matplotlib
  - pip:
    - some-pip-package
    - another-pip==1.0
"""

SAMPLE_R_SCRIPT = """
if (!require("BiocManager", quietly = TRUE))
    install.packages("BiocManager")

BiocManager::install(c(
    "Seurat",
    "DESeq2",
    "SingleCellExperiment"
))

install.packages(c("ggplot2", "tidyverse"))
"""


class TestCondaYamlParsing:
    def test_parse_conda_yaml_basic(self):
        packages = EnvironmentService._parse_conda_yaml(SAMPLE_CONDA_YAML)
        names = [p["name"] for p in packages]
        assert "python" in names
        assert "scanpy" in names
        assert "anndata" in names
        assert "matplotlib" in names

    def test_parse_conda_yaml_versions(self):
        packages = EnvironmentService._parse_conda_yaml(SAMPLE_CONDA_YAML)
        pkg_map = {p["name"]: p for p in packages}
        assert pkg_map["python"]["version"] == "=3.11"
        assert pkg_map["scanpy"]["version"] == ">=1.10"
        assert pkg_map["matplotlib"]["version"] is None

    def test_parse_conda_yaml_pip_packages(self):
        packages = EnvironmentService._parse_conda_yaml(SAMPLE_CONDA_YAML)
        pip_pkgs = [p for p in packages if p["source"] == "pip"]
        assert len(pip_pkgs) == 2
        names = [p["name"] for p in pip_pkgs]
        assert "some-pip-package" in names
        assert "another-pip" in names

    def test_parse_conda_yaml_sources(self):
        packages = EnvironmentService._parse_conda_yaml(SAMPLE_CONDA_YAML)
        conda_pkgs = [p for p in packages if p["source"] == "conda"]
        pip_pkgs = [p for p in packages if p["source"] == "pip"]
        assert len(conda_pkgs) >= 4
        assert len(pip_pkgs) == 2

    def test_parse_empty_yaml(self):
        assert EnvironmentService._parse_conda_yaml("") == []
        assert EnvironmentService._parse_conda_yaml("name: empty\n") == []


class TestRScriptParsing:
    def test_parse_r_script_bioconductor(self):
        packages = EnvironmentService._parse_r_script(SAMPLE_R_SCRIPT)
        bioc_pkgs = [p for p in packages if p["source"] == "bioconductor"]
        names = [p["name"] for p in bioc_pkgs]
        assert "Seurat" in names
        assert "DESeq2" in names
        assert "SingleCellExperiment" in names

    def test_parse_r_script_cran(self):
        packages = EnvironmentService._parse_r_script(SAMPLE_R_SCRIPT)
        cran_pkgs = [p for p in packages if p["source"] == "cran"]
        names = [p["name"] for p in cran_pkgs]
        assert "ggplot2" in names
        assert "tidyverse" in names


class TestCondaYamlUpdate:
    def test_install_conda_package(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "numpy", "1.24.0", "conda", "install")
        assert "numpy==1.24.0" in result

    def test_install_conda_package_no_version(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "numpy", None, "conda", "install")
        assert "numpy" in result
        assert "numpy==" not in result

    def test_remove_conda_package(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "matplotlib", None, "conda", "remove")
        assert "matplotlib" not in result
        # Other packages should still be there
        assert "scanpy" in result

    def test_update_conda_package(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "scanpy", "1.11.0", "conda", "update")
        assert "scanpy==1.11.0" in result
        # Old version spec should be gone
        assert "scanpy>=1.10" not in result

    def test_install_pip_package(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "my-pip-pkg", "2.0", "pip", "install")
        assert "my-pip-pkg==2.0" in result

    def test_remove_pip_package(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "some-pip-package", None, "pip", "remove")
        assert "some-pip-package" not in result
        # Other pip package should remain
        assert "another-pip" in result

    def test_install_preserves_structure(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "new-pkg", None, "conda", "install")
        # Should still have channels
        assert "conda-forge" in result
        assert "bioconda" in result
        # Should still have existing packages
        assert "python" in result

    def test_install_existing_package_replaces(self):
        result = EnvironmentService.update_conda_yaml(SAMPLE_CONDA_YAML, "scanpy", "1.11.0", "conda", "install")
        # Should not have two scanpy entries
        assert result.count("scanpy") == 1
        assert "scanpy==1.11.0" in result
