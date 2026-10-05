"""Point the repo registry at the committed example config for every test run,
so the suite never depends on a developer's local (gitignored) orchestrator.yaml.
This must happen before `repos` is first imported (it loads the config at import)."""

import os
from pathlib import Path

os.environ["ORCHESTRATOR_CONFIG"] = str(Path(__file__).parent / "orchestrator.example.yaml")
