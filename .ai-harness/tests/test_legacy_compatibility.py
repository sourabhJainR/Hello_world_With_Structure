from pathlib import Path

from runtime.legacy_compatibility import build_compatibility_profile, compatibility_instructions


def test_detects_declared_python_version(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.9,<3.12"\n', encoding="utf-8")
    profile = build_compatibility_profile(tmp_path)
    assert any(item["language"] == "python" and item["version"] == "3.9" for item in profile["evidence"])
    assert "PRESERVE python 3.9" in compatibility_instructions(profile)


def test_detects_dotnet_and_csharp_boundaries(tmp_path: Path):
    (tmp_path / "App.csproj").write_text('<Project><PropertyGroup><TargetFramework>net6.0</TargetFramework><LangVersion>10.0</LangVersion></PropertyGroup></Project>', encoding="utf-8")
    profile = build_compatibility_profile(tmp_path)
    assert {item["version"] for item in profile["evidence"]} >= {"6.0", "10.0"}


def test_unknown_version_is_explicit(tmp_path: Path):
    profile = build_compatibility_profile(tmp_path)
    assert profile["policy"]["unknown_version_marker"] == "UNRESOLVED VERSION"
    assert "UNRESOLVED VERSION" in compatibility_instructions(profile)
