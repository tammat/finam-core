from pathlib import Path

ROOT = Path("src/finam_proto")

def patch_file(path: Path):
    text = path.read_text()

    text = text.replace(
        "from grpc.tradeapi",
        "from finam_proto.grpc.tradeapi"
    )

    text = text.replace(
        "import grpc.tradeapi",
        "import finam_proto.grpc.tradeapi"
    )

    path.write_text(text)


def main():
    for py in ROOT.rglob("*_pb2*.py"):
        patch_file(py)
    print("PROTO PATCH DONE")


if __name__ == "__main__":
    main()