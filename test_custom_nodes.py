# 범용 ComfyUI 노드의 입력 검사와 프레임 추출 및 H3 연결을 검증한다.
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
import types
import numpy as np
import torch
import av
from custom_nodes.codex_video_tools import ShotSettings, References, LastFrame, H3Inputs


class CustomNodeTests(unittest.TestCase):
    def test_settings_pair_turbo_and_length(self):
        for turbo, steps, strength in ((True, 4, 1.), (False, 20, 0.)):
            result = ShotSettings().run('scene', 864, 480, 5, turbo, 'project', 'shot')
            self.assertEqual((result[3], result[4], result[6]), (124, steps, strength))
        with self.assertRaises(ValueError):
            ShotSettings().run('scene', 864, 480, 5, True, '../escape', 'shot')

    def test_reference_slots_and_batch(self):
        image = torch.zeros((1, 16, 16, 3))
        with self.assertRaises(ValueError):
            References().run('role', image_2=image)
        with self.assertRaises(ValueError):
            References().run('role', image_1=image.repeat(2, 1, 1, 1))
        self.assertEqual(len(References().run('role', image_1=image)[0]['images']), 1)

    def test_last_frame_and_disabled(self):
        self.assertEqual(LastFrame().run(False, 'missing'), (None,))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'clip.mp4'
            with av.open(str(path), 'w') as out:
                stream = out.add_stream('libx264', rate=24)
                stream.width = stream.height = 32
                stream.pix_fmt = 'yuv420p'
                for color in (0, 200):
                    frame = av.VideoFrame.from_ndarray(np.full((32, 32, 3), color, np.uint8), format='rgb24')
                    for packet in stream.encode(frame):
                        out.mux(packet)
                for packet in stream.encode():
                    out.mux(packet)
            result = LastFrame().run(True, str(path))[0]
            self.assertEqual(tuple(result.shape), (1, 32, 32, 3))
            self.assertGreater(float(result.mean()), .7)

    def test_h3_adapter_uses_native_anchor(self):
        module = types.ModuleType('comfy_extras.nodes_minimax_h3')
        module.MiniMaxH3ReferenceToVideo = types.SimpleNamespace(execute=lambda **kw: (kw['prompt'], {'samples': 'latent'}))
        module.MiniMaxH3AddGuide = types.SimpleNamespace(execute=lambda **kw: ('anchored',))
        image = torch.zeros((1, 16, 16, 3))
        with patch.dict(sys.modules, {'comfy_extras': types.ModuleType('comfy_extras'), 'comfy_extras.nodes_minimax_h3': module}):
            args = dict(clip=None, vae=None, audio_vae=None, references={'images': [image], 'roles': ['identity']}, prompt='Walk', width=864, height=480, frames=124)
            result = H3Inputs().run(**args, first_frame=image)
            self.assertEqual(result[0], 'anchored')
            self.assertIn('<Picture 2>', result[2])
            with self.assertRaises(ValueError):
                H3Inputs().run(**{**args, 'prompt': '<Audio 1>'})


if __name__ == '__main__':
    unittest.main()
