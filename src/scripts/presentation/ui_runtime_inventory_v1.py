from __future__ import annotations

from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
PRESENTATION_ROOT = SRC_ROOT / "marketcore/presentation"

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".css",
    ".scss",
    ".html",
    ".htm",
    ".json",
}

RUNTIME_MARKERS = (
    "fetch(",
    "XMLHttpRequest",
    "axios.",
    "application/json",
    "/api/v1/render-tree/",
    "schema_version",
    "marketcore.render_tree.v1",
    "document.createElement",
    "appendChild(",
    "innerHTML",
    "textContent",
    "addEventListener(",
    "querySelector(",
    "customElements.define",
    "ReactDOM",
    "createRoot(",
    "Vue.createApp",
    "new Vue(",
    "createApp(",
    "Svelte",
)

STATIC_MARKERS = (
    "static",
    "assets",
    "javascript",
    "text/javascript",
    "application/javascript",
    "text/css",
    ".js",
    ".css",
    "send_header",
    "Content-Type",
)

HTML_MARKERS = (
    "<script",
    "<style",
    "<link",
    "<main",
    "<section",
    "<article",
    "<div",
    "<html",
    "<body",
)


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def inventory_files() -> tuple[Path, ...]:
    roots = (
        SRC_ROOT,
        PROJECT_ROOT / "static",
        PROJECT_ROOT / "assets",
        PROJECT_ROOT / "public",
        PROJECT_ROOT / "templates",
    )

    files: set[Path] = set()

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if "__pycache__" in path.parts:
                continue

            if path.suffix.lower() in TEXT_EXTENSIONS:
                files.add(path)

    return tuple(sorted(files))


def scan_markers(
    files: tuple[Path, ...],
    markers: tuple[str, ...],
) -> list[tuple[str, int, str, str]]:
    rows: list[tuple[str, int, str, str]] = []

    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            for marker in markers:
                if marker in line:
                    rows.append(
                        (
                            relative(path),
                            line_number,
                            marker,
                            line.strip(),
                        )
                    )

    return rows


def list_by_suffix(
    files: tuple[Path, ...],
    suffixes: set[str],
) -> tuple[Path, ...]:
    return tuple(
        path
        for path in files
        if path.suffix.lower() in suffixes
    )


def print_rows(
    title: str,
    rows: list[tuple[str, int, str, str]],
) -> None:
    print()
    print(title)

    if not rows:
        print(f"{title}=0")
        return

    for path, line_number, marker, text in rows:
        print(
            "MATCH "
            f"file={path} "
            f"line={line_number} "
            f"marker={marker!r} "
            f"text={text}"
        )


def main() -> None:
    files = inventory_files()

    js_files = list_by_suffix(
        files,
        {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"},
    )
    css_files = list_by_suffix(
        files,
        {".css", ".scss"},
    )
    html_files = list_by_suffix(
        files,
        {".html", ".htm"},
    )

    runtime_rows = scan_markers(files, RUNTIME_MARKERS)
    static_rows = scan_markers(files, STATIC_MARKERS)
    html_rows = scan_markers(files, HTML_MARKERS)

    endpoint_rows = scan_markers(
        files,
        (
            "/api/v1/render-tree/home",
            "/api/v1/render-tree/portfolio",
            "/api/v1/render-tree/portfolio/phone",
        ),
    )

    suffix_counts = Counter(
        path.suffix.lower()
        for path in files
    )

    print("======================================================")
    print("MARKETCORE_UI_RUNTIME_INVENTORY_V1")
    print("======================================================")

    print()
    print("TEXT_FILE_COUNTS")
    for suffix, count in sorted(suffix_counts.items()):
        print(f"FILE_TYPE suffix={suffix or '[none]'} count={count}")

    print()
    print("JAVASCRIPT_TYPESCRIPT_FILES")
    if js_files:
        for path in js_files:
            print(relative(path))
    else:
        print("JAVASCRIPT_TYPESCRIPT_FILES=0")

    print()
    print("CSS_FILES")
    if css_files:
        for path in css_files:
            print(relative(path))
    else:
        print("CSS_FILES=0")

    print()
    print("HTML_TEMPLATE_FILES")
    if html_files:
        for path in html_files:
            print(relative(path))
    else:
        print("HTML_TEMPLATE_FILES=0")

    print()
    print("PRESENTATION_DIRECTORY_TREE")
    if PRESENTATION_ROOT.exists():
        for path in sorted(PRESENTATION_ROOT.rglob("*")):
            if "__pycache__" in path.parts:
                continue
            if path.is_file():
                print(relative(path))
    else:
        print("PRESENTATION_ROOT_NOT_FOUND")

    print_rows("UI_RUNTIME_MARKERS", runtime_rows)
    print_rows("STATIC_DELIVERY_MARKERS", static_rows)
    print_rows("RAW_HTML_MARKERS", html_rows)
    print_rows("RENDER_TREE_ENDPOINT_REFERENCES", endpoint_rows)

    runtime_candidate_files = sorted(
        {
            path
            for path, _, _, _ in runtime_rows
            if Path(path).suffix.lower()
            in {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}
        }
    )

    print()
    print("UI_RUNTIME_CANDIDATE_FILES")
    if runtime_candidate_files:
        for path in runtime_candidate_files:
            print(path)
    else:
        print("UI_RUNTIME_CANDIDATE_FILES=0")

    print()
    print(f"inventory_text_files={len(files)}")
    print(f"javascript_typescript_files={len(js_files)}")
    print(f"css_files={len(css_files)}")
    print(f"html_template_files={len(html_files)}")
    print(f"runtime_marker_rows={len(runtime_rows)}")
    print(f"static_delivery_marker_rows={len(static_rows)}")
    print(f"raw_html_marker_rows={len(html_rows)}")
    print(f"render_tree_endpoint_reference_rows={len(endpoint_rows)}")
    print(f"ui_runtime_candidate_files={len(runtime_candidate_files)}")

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_UI_RUNTIME_INVENTORY_V1_READY")


if __name__ == "__main__":
    main()
