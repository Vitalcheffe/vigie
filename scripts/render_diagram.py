"""Render the Vigie architecture Mermaid diagram to SVG.

Generates docs/architecture-diagram.svg from the Mermaid source in
docs/architecture-diagram.md. The SVG is the file to submit to the
hackathon (vector format, scales perfectly).

Usage:
    python scripts/render_diagram.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Render the Mermaid diagram to SVG."""
    # Extract the mermaid block from the markdown source
    md_path = Path(__file__).resolve().parent.parent / "docs" / "architecture-diagram.md"
    svg_path = Path(__file__).resolve().parent.parent / "docs" / "architecture-diagram.svg"

    if not md_path.exists():
        print(f"ERROR: {md_path} not found", file=sys.stderr)
        sys.exit(1)

    text = md_path.read_text(encoding="utf-8")

    # Extract the mermaid block
    start = text.find("```mermaid\n")
    end = text.find("\n```", start + 11)
    if start < 0 or end < 0:
        print("ERROR: no ```mermaid block found in the markdown", file=sys.stderr)
        sys.exit(1)

    mermaid_code = text[start + 11 : end].strip()

    # Try to render with mermaid-py
    try:
        import mermaid as mermaid_py

        graph = mermaid_py.Mermaid(mermaid_code)
        svg_output = graph.to_svg()
        svg_path.write_bytes(svg_output if isinstance(svg_output, bytes) else svg_output.encode("utf-8"))
        print(f"✓ SVG rendered to {svg_path}")
    except Exception as e:
        print(f"WARNING: mermaid-py rendering failed ({e})", file=sys.stderr)
        print("Falling back to writing the Mermaid source as a .mmd file.", file=sys.stderr)
        mmd_path = svg_path.with_suffix(".mmd")
        mmd_path.write_text(mermaid_code, encoding="utf-8")
        print(f"✓ Mermaid source written to {mmd_path}")
        print("  Render it manually at https://mermaid.live")


if __name__ == "__main__":
    main()
