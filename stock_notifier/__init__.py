from pathlib import Path

import yaml

with open(Path(__file__).parent.joinpath("config.yaml"), "r") as stream:
    config = yaml.safe_load(stream)
