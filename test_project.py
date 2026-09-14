# 자산 누락 검출과 승인되지 않은 결과의 최종 편집 차단을 검증한다.
import tempfile
import unittest
from pathlib import Path
import project
import pipeline as p


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=p.ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / 'sheet.png'
        self.image.write_bytes(b'asset')
        p.save(self.root / 'project.json', {'shots': ['shots/s1/shot.json'], 'assets': {}})
        p.save(self.root / 'shots/s1/shot.json', dict(id='s1', images=[str(self.image)],
               prompt='<Picture 1> identity', width=864, height=480, seconds=5, seed=42,
               assets=[{'id': 'CHAR_001', 'version': 'v1'}]))

    def test_missing_asset_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing asset'):
            project.validate_project(self.root / 'project.json')

    def test_registered_asset_and_tampering(self):
        project.register(self.root / 'project.json', 'CHAR_001', 'character', self.image, 'v1', 'test')
        self.assertTrue(project.validate_project(self.root / 'project.json')['valid'])
        (self.root / 'assets/CHAR_001/v1/sheet.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'modified'):
            project.validate_project(self.root / 'project.json')

    def test_sheet_split_rejects_out_of_bounds_without_writing_views(self):
        from PIL import Image
        Image.new('RGB', (20, 20)).save(self.image)
        project.register(self.root / 'project.json', 'CHAR_001', 'character', self.image, 'v1', 'test')
        p.save(self.root / 'boxes.json', {'front': [0, 0, 30, 20]})
        with self.assertRaisesRegex(ValueError, 'crop'):
            project.split_sheet(self.root / 'project.json', 'CHAR_001', 'v1', self.root / 'boxes.json')
        self.assertFalse((self.root / 'assets/CHAR_001/v1/front.png').exists())

    def test_assembly_requires_review(self):
        p.save(self.root / 'shots/s1/job.json', {'status': 'review_required'})
        with self.assertRaisesRegex(ValueError, 'review'):
            project.assemble(self.root / 'project.json', self.root / 'out.mp4')

    def test_two_clip_assembly_decodes_and_preserves_frames(self):
        import av
        import numpy as np
        from fractions import Fraction
        source = self.root / 'clip.mp4'
        with av.open(str(source), 'w') as container:
            video = container.add_stream('libx264', rate=24)
            video.width = video.height = 32
            video.pix_fmt = 'yuv420p'
            audio = container.add_stream('aac', rate=48000)
            audio.layout = 'stereo'
            for n in range(2):
                frame = av.VideoFrame.from_ndarray(np.zeros((32, 32, 3), dtype=np.uint8), format='rgb24')
                frame.pts, frame.time_base = n, Fraction(1, 24)
                for packet in video.encode(frame):
                    container.mux(packet)
            frame = av.AudioFrame.from_ndarray(np.zeros((2, 4000), dtype=np.float32), format='fltp', layout='stereo')
            frame.sample_rate = 48000
            for packet in audio.encode(frame):
                container.mux(packet)
            for stream in (video, audio):
                for packet in stream.encode(None):
                    container.mux(packet)
        for name in ('s1', 's2'):
            p.save(self.root / 'shots' / name / 'job.json', {'status': 'approved', 'outputs': [{'path': str(source)}]})
        p.save(self.root / 'project.json', {'shots': ['shots/s1/shot.json', 'shots/s2/shot.json']})
        result = project.assemble(self.root / 'project.json', self.root / 'joined.mp4')
        self.assertEqual(result['decoded_frames'], 4)
        self.assertEqual(result['audio_streams'], 1)
        for name in ('s1', 's2'):
            p.save(self.root / 'shots' / name / 'job.json', {'status': 'review_required', 'outputs': [{'path': str(source)}]})
        project.assemble(self.root / 'project.json', self.root / 'preview.mp4', preview=True)
        self.assertEqual(p.read(self.root / 'preview.json')['mode'], 'preview')


if __name__ == '__main__':
    unittest.main()
