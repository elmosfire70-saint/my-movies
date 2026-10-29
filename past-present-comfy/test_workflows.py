# 두 워크플로의 참조 연결과 현재 ComfyUI 노드 스키마를 검증한다.
import json
import unittest
from urllib.request import urlopen

from build_meeting_workflows import still_graph, video_graph, meeting_graph, ui_workflow


class WorkflowTests(unittest.TestCase):
    def test_live_links_and_roles(self):
        with urlopen('http://127.0.0.1:8188/object_info') as response:
            info = json.load(response)
        for graph in (still_graph(), video_graph(), meeting_graph()):
            for key, node in graph.api.items():
                self.assertIn(node['class_type'], info)
                for value in node['inputs'].values():
                    if isinstance(value, list):
                        self.assertIn(value[0], graph.api)
                        self.assertLess(value[1], len(info[graph.api[value[0]]['class_type']]['output']))
            def visit(key, path):
                self.assertNotIn(key, path, 'Graph must not contain cycles')
                for value in graph.api[key]['inputs'].values():
                    if isinstance(value, list):
                        visit(value[0], path | {key})
            for key in graph.api:
                visit(key, set())
            ui = ui_workflow(graph, info)
            self.assertEqual(len(ui['nodes']), len(graph.api))
            self.assertTrue(ui['links'])
        still = still_graph().api
        encoder = next(node for node in still.values() if node['class_type'] == 'TextEncodeQwenImage21')
        self.assertEqual(len([key for key in encoder['inputs'] if key.startswith('images.image_')]), 4)
        for slot, filename in [('images.image_2', 'child-face.jpg'),
                               ('images.image_3', 'adult-face-new.png')]:
            scale = still[encoder['inputs'][slot][0]]
            self.assertEqual(scale['class_type'], 'ImageScaleToMaxDimension')
            photo = still[scale['inputs']['image'][0]]
            self.assertEqual(photo['class_type'], 'LoadImage')
            self.assertEqual(photo['inputs']['image'], filename)
        video = video_graph().api
        inputs = next(node for node in video.values() if node['class_type'] == 'CodexH3Inputs')
        self.assertEqual(video[inputs['inputs']['first_frame'][0]]['class_type'], 'LoadImage')
        self.assertEqual(video[inputs['inputs']['references'][0]]['inputs']['enabled'], False)
        self.assertEqual(sum(node['class_type'] == 'SaveVideo' for node in video.values()), 1)
        create = next(node for node in video.values() if node['class_type'] == 'CreateVideo')
        self.assertNotIn('audio', create['inputs'])

    def test_two_photos_to_silent_video(self):
        graph = meeting_graph().api
        self.assertEqual(sum(n['class_type'] == 'LoadImage' for n in graph.values()), 3)
        self.assertFalse(any(n['class_type'] == 'ImageCrop' for n in graph.values()))
        inputs = next(n['inputs'] for n in graph.values() if n['class_type'] == 'CodexH3Inputs')
        saved = next(n['inputs'] for n in graph.values() if n['class_type'] == 'SaveImage')
        self.assertEqual(inputs['first_frame'], saved['images'])
        self.assertEqual(graph[inputs['first_frame'][0]]['class_type'], 'SplitImageWithAlpha')
        self.assertFalse(any(n['class_type'] == 'VAEDecodeAudio' for n in graph.values()))
        create = next(n['inputs'] for n in graph.values() if n['class_type'] == 'CreateVideo')
        self.assertNotIn('audio', create)
        save = next(n['inputs'] for n in graph.values() if n['class_type'] == 'SaveVideo')
        self.assertEqual(graph[save['video'][0]]['class_type'], 'CreateVideo')

    def test_optional_background(self):
        for graph in (still_graph(), meeting_graph()):
            encoder = next(n['inputs'] for n in graph.api.values()
                           if n['class_type'] == 'TextEncodeQwenImage21')
            switch = graph.api[encoder['images.image_4'][0]]
            self.assertEqual(switch['class_type'], 'ComfySwitchNode')
            enable = graph.api[switch['inputs']['switch'][0]]
            self.assertEqual(enable['class_type'], 'PrimitiveBoolean')
            self.assertIs(enable['inputs']['value'], False)
            self.assertNotIn('on_false', switch['inputs'])
            scale = graph.api[switch['inputs']['on_true'][0]]
            self.assertEqual(scale['class_type'], 'ImageScaleToMaxDimension')
            loader = graph.api[scale['inputs']['image'][0]]
            self.assertEqual(loader['inputs']['image'], 'meeting-background-neutral.png')
            self.assertNotEqual(encoder['images.image_4'], encoder['images.image_2'])
            self.assertNotEqual(encoder['images.image_4'], encoder['images.image_3'])
            prompt_switch = graph.api[encoder['prompt'][0]]
            self.assertEqual(prompt_switch['inputs']['switch'], switch['inputs']['switch'])
            on_text = graph.api[prompt_switch['inputs']['on_true'][0]]['inputs']['value']
            self.assertIn('BACKGROUND REPLACEMENT IS ENABLED', on_text)


if __name__ == '__main__':
    unittest.main()
