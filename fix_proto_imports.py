import os
import re

ROOT = "src/finam_proto"

def patch_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # === FIX OPENAPI IMPORTS ===
    content = re.sub(
        r"from protoc_gen_openapiv2\.options import",
        "from finam_proto.protoc_gen_openapiv2.options import",
        content
    )

    # === FIX grpc.tradeapi → finam_proto.grpc.tradeapi ===
    content = re.sub(
        r"from grpc\.tradeapi",
        "from finam_proto.grpc.tradeapi",
        content
    )

    # === FIX google.api (если есть) ===
    content = re.sub(
        r"from google\.api",
        "from finam_proto.google.api",
        content
    )

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"PATCHED: {path}")

def main():
    for root, _, files in os.walk(ROOT):
        for file in files:
            if file.endswith(".py"):
                patch_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
