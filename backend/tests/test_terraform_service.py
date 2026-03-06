import pytest

from app.services.terraform_service import TerraformService


def test_parse_plan_json_empty():
    result = TerraformService._parse_plan_json("")
    assert result["add_count"] == 0
    assert result["change_count"] == 0
    assert result["destroy_count"] == 0


def test_parse_plan_json_with_changes():
    plan_output = """{"type":"planned_change","change":{"resource":{"resource_type":"google_compute_instance","resource_name":"slurm_controller","addr":"google_compute_instance.slurm_controller[0]"},"action":"create"}}
{"type":"planned_change","change":{"resource":{"resource_type":"google_compute_instance","resource_name":"slurm_login","addr":"google_compute_instance.slurm_login[0]"},"action":"create"}}"""

    result = TerraformService._parse_plan_json(plan_output)
    assert result["add_count"] == 2
    assert result["change_count"] == 0
    assert result["destroy_count"] == 0
    assert result["add"][0]["type"] == "google_compute_instance"


def test_parse_plan_json_with_destroy():
    plan_output = '{"type":"planned_change","change":{"resource":{"resource_type":"google_compute_instance","resource_name":"test","addr":"test"},"action":"delete"}}'

    result = TerraformService._parse_plan_json(plan_output)
    assert result["destroy_count"] == 1


def test_parse_plan_json_invalid_json():
    result = TerraformService._parse_plan_json("not valid json\nalso not json")
    assert result["add_count"] == 0


@pytest.mark.asyncio
async def test_update_tfvars(tmp_path):
    """Test that tfvars file is updated correctly."""
    import app.services.terraform_service as tf_mod

    original_dir = tf_mod.TERRAFORM_DIR
    original_file = tf_mod.TFVARS_FILE
    tf_mod.TERRAFORM_DIR = tmp_path
    tf_mod.TFVARS_FILE = tmp_path / "terraform.tfvars"

    try:
        # Create initial file
        tf_mod.TFVARS_FILE.write_text("enable_slurm = false\n")

        TerraformService._update_tfvars({"enable_slurm": True})

        content = tf_mod.TFVARS_FILE.read_text()
        assert "enable_slurm = true" in content
    finally:
        tf_mod.TERRAFORM_DIR = original_dir
        tf_mod.TFVARS_FILE = original_file


@pytest.mark.asyncio
async def test_update_tfvars_new_key(tmp_path):
    """Test adding a new key to tfvars."""
    import app.services.terraform_service as tf_mod

    original_dir = tf_mod.TERRAFORM_DIR
    original_file = tf_mod.TFVARS_FILE
    tf_mod.TERRAFORM_DIR = tmp_path
    tf_mod.TFVARS_FILE = tmp_path / "terraform.tfvars"

    try:
        tf_mod.TFVARS_FILE.write_text("")
        TerraformService._update_tfvars({"new_key": "value"})

        content = tf_mod.TFVARS_FILE.read_text()
        assert 'new_key = "value"' in content
    finally:
        tf_mod.TERRAFORM_DIR = original_dir
        tf_mod.TFVARS_FILE = original_file
