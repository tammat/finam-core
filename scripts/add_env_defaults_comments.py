# -*- coding: utf-8 -*-
from pathlib import Path
import re

env_file = Path("env/.env.example")

lines = env_file.read_text(encoding="utf-8").splitlines()

result = []

pattern = re.compile(r"^([A-Z0-9_]+)=(.*)$")

for line in lines:
    match = pattern.match(line)

    if match:
        key = match.group(1)
        value = match.group(2).strip()

        default_value = value if value else "EMPTY"

        result.append(f"# Значение по умолчанию: {default_value}")

    result.append(line)

env_file.write_text("\n".join(result) + "\n", encoding="utf-8")

print("ENV_DEFAULTS_COMMENTS_ADDED")
