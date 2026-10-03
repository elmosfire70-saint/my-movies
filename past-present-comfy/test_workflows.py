# 두 워크플로의 참조 연결과 현재 ComfyUI 노드 스키마를 검증한다.
import json
import unittest
from urllib.request import urlopen

from build_meeting_workflows import still_graph, video_graph, ui_workflow


class WorkflowTests(unittest.TestCase):
    def test_live_links_and_roles(self):
        with urlopen('http://127.0.0.1:8188/object_info') as response:
            info = json.load(response)
        for graph in (still_graph(), video_graph()):
            for key, node in graph.api.items():
                self.assertIn(node['class_type'], info)
                for value in node['inputs'].values():
                    if isinstance(value, list):
                        self.assertLess(int(value[0]), int(key))
                        self.assertLess(value[1], len(info[graph.api[value[0]]['class_type']]['output']))
            ui = ui_workflow(graph, info)
            self.assertEqual(len(ui['nodes']), len(graph.api))
            self.assertTrue(ui['links'])
        still = still_graph().api
        encoder = next(node for node in still.values() if node['class_type'] == 'TextEncodeQwenImage21')
        self.assertEqual(len([key for key in encoder['inputs'] if key.startswith('images.image_')]), 6)
        video = video_graph().api
        inputs = next(node for node in video.values() if node['class_type'] == 'CodexH3Inputs')
        self.assertEqual(video[inputs['inputs']['first_frame'][0]]['class_type'], 'LoadImage')
        self.assertEqual(video[inputs['inputs']['references'][0]]['inputs']['enabled'], False)
        self.assertEqual(sum(node['class_type'] == 'SaveVideo' for node in video.values()), 1)


if __name__ == '__main__':
    unittest.main()
