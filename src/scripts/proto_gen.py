import subprocess
import shutil
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROTO_DIR = ROOT / "infra" / "finam" / "proto"
OUT_DIR = ROOT / "finam_proto"

if OUT_DIR.exists():
    shutil.rmtree(OUT_DIR)

OUT_DIR.mkdir(parents=True)

cmd = [
    "python",
    "-m",
    "grpc_tools.protoc",
    f"-I={PROTO_DIR}",
    f"--python_out={OUT_DIR}",
    f"--grpc_python_out={OUT_DIR}",
]

for proto in PROTO_DIR.rglob("*.proto"):
    cmd.append(str(proto))

subprocess.run(cmd, check=True)
print("Proto generated")