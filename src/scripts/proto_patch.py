import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "finam_proto"

count = 0

for path in TARGET.rglob("*.py"):
    text = path.read_text()
    if "from grpc." in text:
        text = text.replace("from grpc.", "from finam_proto.grpc.")
        path.write_text(text)
        count += 1

print(f"Patched {count} files")