import json
from pathlib import Path
from typing import List, Optional
from assessment_engine.core.protocol import AssessmentProtocol


class ProtocolRepository:
    """File-based repository for assessment protocols."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.protocols_dir = self.base_path / "protocols"
        self.protocols_dir.mkdir(parents=True, exist_ok=True)

    def _find_protocol_file(self, protocol_id: str) -> Optional[Path]:
        """Find protocol file by id."""
        for ext in [".json", ".yaml", ".yml"]:
            file_path = self.protocols_dir / f"{protocol_id}{ext}"
            if file_path.exists():
                return file_path
        return None

    def load(self, protocol_id: str) -> Optional[AssessmentProtocol]:
        """Load protocol by id."""
        file_path = self._find_protocol_file(protocol_id)

        if not file_path:
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML required for YAML protocol files")
            else:
                data = json.load(f)

        return AssessmentProtocol.model_validate(data)

    def list_all(self) -> List[AssessmentProtocol]:
        """List all available protocols."""
        protocols = []

        for file_path in self.protocols_dir.iterdir():
            if file_path.suffix in [".json", ".yaml", ".yml"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    if file_path.suffix in [".yaml", ".yml"]:
                        import yaml
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)

                protocols.append(AssessmentProtocol.model_validate(data))

        return protocols

    def save(self, protocol: AssessmentProtocol) -> None:
        """Save protocol to file."""
        file_path = self.protocols_dir / f"{protocol.id}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(protocol.model_dump(), f, indent=2)
