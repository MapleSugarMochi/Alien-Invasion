"""制作可移植源码候选包，不包含虚拟环境、Git 元数据或临时文件。"""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Alien-Invasion-candidate.zip")
    args = parser.parse_args()
    files = list(ROOT.glob("*.py")) + list(ROOT.glob("*.md")) + list(ROOT.glob("*.pdf")) + list(ROOT.glob("*.docx"))
    files += [ROOT / "requirements.txt"]
    for directory in ("assets", "tests", "tools", "docs"):
        files += [p for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    files = sorted(set(files))
    required = ("main.py", "game.py", "requirements.txt", "assets/images/sprite-atlas.png")
    relative_paths = {p.relative_to(ROOT).as_posix() for p in files}
    if not set(required) <= relative_paths:
        raise RuntimeError("候选包缺少必要源码或资源")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "Alien Invasion/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        assert not any("/.venv/" in p or "/.git/" in p for p in archive.namelist())
    checksum = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".sha256").write_text(checksum + "  " + args.output.name + "\n", encoding="utf-8")
    print(f"PASS: {args.output}, {len(files)} files, {args.output.stat().st_size} bytes, SHA256 {checksum}")


if __name__ == "__main__":
    main()
