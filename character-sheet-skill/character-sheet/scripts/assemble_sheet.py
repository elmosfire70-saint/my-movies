# 선택된 캐릭터 PNG를 원본 보존 방식으로 배치하고 버전 기록을 저장한다.
import argparse
import hashlib
import json
import shutil
import uuid
from pathlib import Path

from PIL import Image, ImageOps


LAYOUTS = {"basic": (2, 2), "expressions": (3, 2), "poses": (3, 2), "outfits": (2, 2)}


def assemble(spec_path, output):
    spec_path, output = Path(spec_path).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    cols, rows = LAYOUTS[spec["type"]]
    if len(spec["panels"]) != cols * rows:
        raise ValueError(f"Expected {cols * rows} panels")
    if not spec.get("character") or not spec.get("style"):
        raise ValueError("character and style are required")
    loaded = []
    for group in ("panels", "references"):
        for item in spec.get(group, []):
            source = (spec_path.parent / item["path"]).resolve()
            with Image.open(source) as im:
                im.load()
                if group == "panels" and im.format != "PNG":
                    raise ValueError(f"Panel must be PNG: {source}")
                size = list(im.size)
            loaded.append((group, item, source, size))
    output.parent.mkdir(parents=True, exist_ok=True)
    # 완성된 폴더만 공개하며 오류가 나면 이번 임시 결과만 정리한다.
    stage = output.parent / f".sheet-{uuid.uuid4().hex}"
    stage.mkdir()
    try:
        canvas = Image.new("RGB", (cols * 1024, rows * 1024), "white")
        counters = {"panels": 0, "references": 0}
        for group, item, source, size in loaded:
            index = counters[group]
            counters[group] += 1
            relative = Path(group) / f"{index + 1:02d}{source.suffix.lower()}"
            target = stage / relative
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            item["path"] = relative.as_posix()
            item["size"] = size
            item["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            if group == "panels":
                with Image.open(target) as im:
                    fitted = ImageOps.contain(im.convert("RGBA"), (960, 960), Image.Resampling.LANCZOS)
                    x = (index % cols) * 1024 + (1024 - fitted.width) // 2
                    y = (index // cols) * 1024 + (1024 - fitted.height) // 2
                    canvas.paste(fitted, (x, y), fitted)
        canvas.save(stage / "sheet.png")
        spec["sheet"] = {"path": "sheet.png", "size": list(canvas.size), "columns": cols, "rows": rows}
        (stage / "manifest.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        if output.exists():
            raise FileExistsError(f"Output already exists: {output}")
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return output / "manifest.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble selected character PNGs without overwriting versions")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(assemble(args.spec, args.output))
