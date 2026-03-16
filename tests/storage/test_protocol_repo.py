import pytest
import tempfile
import shutil
import json
from pathlib import Path
from assessment_engine.core.protocol import (
    AssessmentProtocol,
    Dimension,
    Scale,
    StoppingRules,
)
from assessment_engine.storage.protocol_repo import ProtocolRepository


class TestProtocolRepository:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def repo(self, temp_dir):
        """Create a ProtocolRepository with temp directory."""
        return ProtocolRepository(base_path=temp_dir)

    @pytest.fixture
    def sample_protocol(self):
        """Create a sample protocol for testing."""
        return AssessmentProtocol(
            id="test_protocol",
            name="Test Protocol",
            description="A test protocol for unit tests",
            dimensions=[
                Dimension(
                    id="dim1",
                    name="Dimension 1",
                    description="First dimension",
                    scale=Scale(min=0, max=1, default=0.5),
                ),
                Dimension(
                    id="dim2",
                    name="Dimension 2",
                    description="Second dimension",
                    scale=Scale(min=0, max=1, default=0.5),
                ),
            ],
            coverage_targets=["target1", "target2", "target3"],
            question_strategies=["strategy1", "strategy2"],
            stopping_rules=StoppingRules(
                min_rounds=5,
                max_rounds=12,
                target_confidence=0.75,
                min_coverage_ratio=0.85,
            ),
            report_template="default_template",
        )

    def test_init_creates_directory(self, temp_dir):
        """Test that initialization creates the protocols directory."""
        new_dir = Path(temp_dir) / "new_project"
        repo = ProtocolRepository(base_path=str(new_dir))
        assert repo.protocols_dir.exists()
        assert repo.protocols_dir.is_dir()

    def test_find_protocol_file_json(self, repo, sample_protocol):
        """Test finding a JSON protocol file."""
        repo.save(sample_protocol)

        found_path = repo._find_protocol_file(sample_protocol.id)

        assert found_path is not None
        assert found_path.suffix == ".json"
        assert found_path.stem == sample_protocol.id

    def test_find_protocol_file_nonexistent(self, repo):
        """Test finding a protocol file that doesn't exist."""
        found_path = repo._find_protocol_file("nonexistent_protocol")
        assert found_path is None

    def test_load_json_protocol(self, repo, sample_protocol):
        """Test loading a JSON protocol."""
        repo.save(sample_protocol)

        loaded = repo.load(sample_protocol.id)

        assert loaded is not None
        assert loaded.id == sample_protocol.id
        assert loaded.name == sample_protocol.name
        assert loaded.description == sample_protocol.description
        assert len(loaded.dimensions) == len(sample_protocol.dimensions)
        assert loaded.coverage_targets == sample_protocol.coverage_targets
        assert loaded.question_strategies == sample_protocol.question_strategies
        assert loaded.report_template == sample_protocol.report_template

    def test_load_nonexistent_protocol(self, repo):
        """Test loading a protocol that doesn't exist."""
        loaded = repo.load("nonexistent_protocol")
        assert loaded is None

    def test_save_protocol(self, repo, sample_protocol):
        """Test saving a protocol."""
        repo.save(sample_protocol)

        file_path = repo.protocols_dir / f"{sample_protocol.id}.json"
        assert file_path.exists()

        # Verify JSON content
        with open(file_path, "r") as f:
            data = json.load(f)
            assert data["id"] == sample_protocol.id
            assert data["name"] == sample_protocol.name

    def test_list_all_empty(self, repo):
        """Test listing protocols when none exist."""
        protocols = repo.list_all()
        assert protocols == []

    def test_list_all_multiple_protocols(self, repo):
        """Test listing multiple protocols."""
        protocol1 = AssessmentProtocol(
            id="protocol_1",
            name="Protocol 1",
            description="First protocol",
            dimensions=[],
            coverage_targets=[],
            question_strategies=[],
            stopping_rules=StoppingRules(),
            report_template="template1",
        )
        protocol2 = AssessmentProtocol(
            id="protocol_2",
            name="Protocol 2",
            description="Second protocol",
            dimensions=[],
            coverage_targets=[],
            question_strategies=[],
            stopping_rules=StoppingRules(),
            report_template="template2",
        )

        repo.save(protocol1)
        repo.save(protocol2)

        protocols = repo.list_all()

        assert len(protocols) == 2
        protocol_ids = {p.id for p in protocols}
        assert protocol_ids == {"protocol_1", "protocol_2"}

    def test_list_all_ignores_non_protocol_files(self, repo):
        """Test that list_all ignores files that aren't protocols."""
        # Create a protocol
        protocol = AssessmentProtocol(
            id="valid_protocol",
            name="Valid Protocol",
            description="A valid protocol",
            dimensions=[],
            coverage_targets=[],
            question_strategies=[],
            stopping_rules=StoppingRules(),
            report_template="template",
        )
        repo.save(protocol)

        # Create a non-protocol file
        random_file = repo.protocols_dir / "random.txt"
        random_file.write_text("This is not a protocol")

        protocols = repo.list_all()

        assert len(protocols) == 1
        assert protocols[0].id == "valid_protocol"

    def test_round_trip_complex_protocol(self, repo):
        """Test saving and loading a protocol with complex data."""
        complex_protocol = AssessmentProtocol(
            id="complex_protocol",
            name="Complex Protocol",
            description="A protocol with complex configuration",
            dimensions=[
                Dimension(
                    id="technical_skill",
                    name="Technical Skill",
                    description="Technical proficiency level",
                    scale=Scale(min=0.0, max=1.0, default=0.5),
                ),
                Dimension(
                    id="communication",
                    name="Communication",
                    description="Communication effectiveness",
                    scale=Scale(min=0.0, max=1.0, default=0.5),
                ),
                Dimension(
                    id="leadership",
                    name="Leadership",
                    description="Leadership capabilities",
                    scale=Scale(min=0.0, max=1.0, default=0.5),
                ),
            ],
            coverage_targets=[
                "technical_depth",
                "technical_breadth",
                "verbal_communication",
                "written_communication",
                "team_leadership",
                "strategic_thinking",
            ],
            question_strategies=[
                "behavioral",
                "situational",
                "technical",
                "problem_solving",
            ],
            stopping_rules=StoppingRules(
                min_rounds=8,
                max_rounds=20,
                target_confidence=0.85,
                min_coverage_ratio=0.9,
            ),
            report_template="detailed_assessment",
        )

        repo.save(complex_protocol)
        loaded = repo.load(complex_protocol.id)

        assert loaded is not None
        assert loaded.id == complex_protocol.id
        assert loaded.name == complex_protocol.name
        assert len(loaded.dimensions) == 3
        assert len(loaded.coverage_targets) == 6
        assert len(loaded.question_strategies) == 4
        assert loaded.stopping_rules.min_rounds == 8
        assert loaded.stopping_rules.max_rounds == 20
        assert loaded.stopping_rules.target_confidence == 0.85
        assert loaded.stopping_rules.min_coverage_ratio == 0.9

    def test_load_yaml_protocol(self, repo, temp_dir):
        """Test loading a YAML protocol file."""
        yaml = pytest.importorskip("yaml")

        protocol_data = {
            "id": "yaml_protocol",
            "name": "YAML Protocol",
            "description": "A protocol from YAML",
            "dimensions": [
                {
                    "id": "dim1",
                    "name": "Dimension 1",
                    "description": "First dimension",
                    "scale": {"min": 0.0, "max": 1.0, "default": 0.5},
                }
            ],
            "coverage_targets": ["target1"],
            "question_strategies": ["strategy1"],
            "stopping_rules": {
                "min_rounds": 5,
                "max_rounds": 10,
                "target_confidence": 0.7,
                "min_coverage_ratio": 0.8,
            },
            "report_template": "yaml_template",
        }

        yaml_path = repo.protocols_dir / "yaml_protocol.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(protocol_data, f)

        loaded = repo.load("yaml_protocol")

        assert loaded is not None
        assert loaded.id == "yaml_protocol"
        assert loaded.name == "YAML Protocol"

    def test_load_yml_protocol(self, repo, temp_dir):
        """Test loading a .yml protocol file."""
        yaml = pytest.importorskip("yaml")

        protocol_data = {
            "id": "yml_protocol",
            "name": "YML Protocol",
            "description": "A protocol from YML",
            "dimensions": [],
            "coverage_targets": [],
            "question_strategies": [],
            "stopping_rules": {
                "min_rounds": 6,
                "max_rounds": 15,
                "target_confidence": 0.72,
                "min_coverage_ratio": 0.8,
            },
            "report_template": "yml_template",
        }

        yml_path = repo.protocols_dir / "yml_protocol.yml"
        with open(yml_path, "w") as f:
            yaml.dump(protocol_data, f)

        loaded = repo.load("yml_protocol")

        assert loaded is not None
        assert loaded.id == "yml_protocol"

    def test_yaml_import_error(self, repo, temp_dir, monkeypatch):
        """Test that ImportError is raised when YAML is needed but not installed."""
        # Create a YAML file manually
        yaml_path = repo.protocols_dir / "test.yaml"
        yaml_path.write_text("id: test\nname: Test")

        # Mock yaml import to raise ImportError
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("No module named 'yaml'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with pytest.raises(ImportError, match="PyYAML required"):
            repo.load("test")

    def test_find_protocol_file_preference(self, repo, sample_protocol):
        """Test that _find_protocol_file finds files with different extensions."""
        # Save as JSON first
        repo.save(sample_protocol)

        # Should find the JSON file
        found = repo._find_protocol_file(sample_protocol.id)
        assert found is not None
        assert found.suffix == ".json"
