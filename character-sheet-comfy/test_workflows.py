# 워크플로 참조 역할과 실제 서버 스키마 및 UI 연결 무결성을 검증한다.
import json
import unittest
from urllib.request import urlopen
from build_workflows import graphs, ui_workflow


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with urlopen('http://127.0.0.1:8188/object_info') as response:
            cls.info = json.load(response)

    def test_live_schema_and_links(self):
        for name, graph in graphs().items():
            with self.subTest(workflow=name):
                for key, node in graph.api.items():
                    meta = self.info[node['class_type']]
                    self.assertFalse(meta.get('api_node', False))
                    inputs = {**meta['input'].get('required', {}), **meta['input'].get('optional', {})}
                    self.assertTrue(set(meta['input'].get('required', {})) <= node['inputs'].keys())
                    for field, value in node['inputs'].items():
                        self.assertIn(field, inputs)
                        kind = inputs[field][0]
                        opts = inputs[field][1] if len(inputs[field]) > 1 else {}
                        if isinstance(value, list):
                            self.assertLess(int(value[0]), int(key), 'Graph must remain acyclic')
                            source = self.info[graph.api[value[0]]['class_type']]
                            self.assertEqual(kind, source['output'][value[1]])
                        elif node['class_type'] not in ('UNETLoader', 'CLIPLoader', 'VAELoader', 'LoadImage'):
                            choices = kind if isinstance(kind, list) else opts.get('options')
                            if choices:
                                self.assertIn(value, choices)
                            if 'min' in opts:
                                self.assertGreaterEqual(value, opts['min'])
                            if 'max' in opts:
                                self.assertLessEqual(value, opts['max'])
                ui = ui_workflow(graph, self.info)
                nodes = {node['id']: node for node in ui['nodes']}
                for link, source, out, target, slot, kind in ui['links']:
                    self.assertIn(link, nodes[source]['outputs'][out]['links'])
                    self.assertEqual(link, nodes[target]['inputs'][slot]['link'])
                    self.assertEqual(kind, nodes[source]['outputs'][out]['type'])

    def test_identity_and_outfit_roles(self):
        anchor, sheet, compose = graphs().values()
        encoders = [n for n in anchor.api.values() if n['class_type'] == 'TextEncodeQwenImageEditPlus']
        self.assertEqual(len(encoders), 2)
        for node in encoders:
            self.assertEqual(node['inputs']['image1'], ['6', 0])
            self.assertEqual(node['inputs']['image2'], ['7', 0])
        for node in sheet.api.values():
            if node['class_type'] == 'TextEncodeQwenImageEditPlus':
                self.assertEqual([node['inputs'][f'image{i}'] for i in (1, 2, 3)],
                                 [['6', 0], ['7', 0], ['8', 0]])
        self.assertEqual(sum(n['class_type'] == 'KSampler' for n in sheet.api.values()), 3)
        self.assertEqual(sum(n['class_type'] == 'SaveImage' for n in sheet.api.values()), 4)
        self.assertFalse(any(n['class_type'] == 'KSampler' for n in compose.api.values()))

    def test_locked_seeds_and_layout(self):
        for graph in graphs().values():
            for node in ui_workflow(graph, self.info)['nodes']:
                if node['type'] == 'KSampler':
                    self.assertEqual(node['widgets_values'][1], 'fixed')
            for node in graph.api.values():
                if node['class_type'] == 'ImageScale':
                    self.assertEqual(node['inputs']['width'], 0)
                    self.assertEqual(node['inputs']['crop'], 'disabled')
                if node['class_type'] == 'ImageStitch':
                    self.assertEqual(node['inputs']['direction'], 'right')
                    self.assertFalse(node['inputs']['match_image_size'])


if __name__ == '__main__':
    unittest.main()
