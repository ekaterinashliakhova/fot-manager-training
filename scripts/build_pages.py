#!/usr/bin/env python3
"""Build the static site for either /repository/ Pages or a root domain."""
import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(base_path: str, output: Path) -> None:
    if not re.fullmatch(r"/(?:[A-Za-z0-9._-]+/)*", base_path):
        raise ValueError("Base path must be / or /repository-name/ (including trailing slash)")
    output = output.resolve()
    if output == ROOT or ROOT / "dist" == output or ROOT / "dist" in output.parents or output in ROOT.parents:
        raise ValueError("Output must be a separate build directory")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(ROOT / "dist", output)

    # Match only local URL prefixes. Do not rewrite SVG markup, external URLs,
    # source-map comments, relative ES imports, or the bundled Three.js library.
    rooted_url = re.compile(
        r'''(["'`])/(?=assets/|cases/|learn/|materials(?:/|["'`])|final(?:/|["'`])|style\.css|fonts\.css|entry\.js|[?#]|["'`])'''
    )
    for file in output.rglob("*"):
        if file.suffix not in {".html", ".js", ".css"} or "assets" in file.relative_to(output).parts:
            continue
        text = file.read_text(encoding="utf-8")
        if file.name == "app.js":
            # Compare canonical routes with a trailing slash, including the
            # repository homepage. Keep the separator outside the URL rewrite.
            old = "const path=location.pathname.replace(/\\/+$/,'')||'/';"
            new = "const path=location.pathname.endsWith(String.fromCharCode(47))?location.pathname:location.pathname+String.fromCharCode(47);"
            if text.count(old) != 1:
                raise ValueError("Route dispatcher changed; review the Pages adaptation")
            text = text.replace(old, new).replace("path==='/materials'", "path==='/materials/'").replace("path==='/final'", "path==='/final/'")
        text = rooted_url.sub(lambda match: match[1] + base_path, text)
        text = text.replace("url(/assets/", "url(" + base_path + "assets/")
        if file.name == "entry.js":
            old = "location.pathname.match("
            if text.count(old) != 1:
                raise ValueError("Segment route detection changed; review the Pages adaptation")
            text = "const pagesBase=" + json.dumps(base_path) + ";\n" + text.replace(old, "location.pathname.slice(pagesBase.length-1).match(")
        file.write_text(text, encoding="utf-8")
    (output / ".nojekyll").touch()
    print(f"Built {output} for base path {base_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-path", default="/", help="/ for root hosting, /repository/ for project Pages")
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    build(args.base_path, args.output)
