# 시트 배치와 버전 보존을 임시 이미지로 검증한다.
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

module_spec = importlib.util.spec_from_file_location("assembler", Path(__file__).parent / "character-sheet/scripts/assemble_sheet.py")
assembler = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(assembler)


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def request(self, kind, count):
        panels = []
        for i in range(count):
            path = self.root / f"input{i}.png"
            Image.new("RGB", (200, 400) if i % 2 == 0 else (400, 200), "red").save(path)
            panels.append({"label": str(i), "path": path.name, "prompt": "test"})
        spec = {"character": "test", "style": "실사", "type": kind, "panels": panels,
                "references": [{"role": "baseline", "path": "input0.png"}]}
        path = self.root / "request.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path

    def test_four_and_six_panels_preserve_sources_and_ratio(self):
        for kind, count, expected in [("basic", 4, (2048, 2048)), ("expressions", 6, (3072, 2048))]:
            request = self.request(kind, count)
            original = (self.root / "input0.png").read_bytes()
            manifest = assembler.assemble(request, self.root / kind)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["panels"][0]["size"], [200, 400])
            self.assertEqual((manifest.parent / data["panels"][0]["path"]).read_bytes(), original)
            self.assertEqual((self.root / "input0.png").read_bytes(), original)
            with Image.open(manifest.parent / "sheet.png") as sheet:
                self.assertEqual(sheet.size, expected)
                self.assertEqual(sheet.getpixel((271, 512)), (255, 255, 255))
                self.assertEqual(sheet.getpixel((272, 512)), (255, 0, 0))
                self.assertEqual(sheet.getpixel((512, 32)), (255, 0, 0))

    def test_existing_version_refused(self):
        request = self.request("basic", 4)
        output = self.root / "v1"
        assembler.assemble(request, output)
        before = (output / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            assembler.assemble(request, output)
        self.assertEqual((output / "manifest.json").read_bytes(), before)

    def test_bad_count_and_missing_file_leave_no_version(self):
        request = self.request("poses", 4)
        with self.assertRaises(ValueError):
            assembler.assemble(request, self.root / "bad")
        self.assertFalse((self.root / "bad").exists())
        request = self.request("outfits", 4)
        (self.root / "input0.png").unlink()
        with self.assertRaises(FileNotFoundError):
            assembler.assemble(request, self.root / "missing")
        self.assertFalse((self.root / "missing").exists())

    def test_revision_preserves_other_selected_panels(self):
        request = self.request("basic", 4)
        first = assembler.assemble(request, self.root / "v1")
        spec = json.loads(first.read_text(encoding="utf-8"))
        for group in ("panels", "references"):
            for entry in spec[group]:
                entry["path"] = str(first.parent / entry["path"])
        changed = self.root / "new.png"
        Image.new("RGB", (200, 400), "blue").save(changed)
        spec["panels"][2]["path"] = str(changed)
        spec["parent_version"] = "v1"
        request.write_text(json.dumps(spec), encoding="utf-8")
        second = assembler.assemble(request, self.root / "v2")
        old = json.loads(first.read_text(encoding="utf-8"))
        new = json.loads(second.read_text(encoding="utf-8"))
        for index in range(4):
            self.assertEqual(old["panels"][index]["sha256"] == new["panels"][index]["sha256"], index != 2)


if __name__ == "__main__":
    unittest.main()
