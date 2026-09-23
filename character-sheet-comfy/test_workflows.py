# 워크플로 참조 역할과 실제 서버 스키마 및 UI 연결 무결성을 검증한다.
import json
import unittest
from urllib.request import urlopen
from build_workflows import graphs, ui_workflow, expanded_inputs


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
                    schema = expanded_inputs(meta, node)
                    inputs = {**schema['required'], **schema['optional']}
                    self.assertTrue(set(schema['required']) <= node['inputs'].keys())
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
        def source_image(graph, link):
            node = graph.api[link[0]]
            while node['class_type'] == 'ImageScaleToMaxDimension':
                node = graph.api[node['inputs']['image'][0]]
            return node['inputs']['image']
        for graph, expected in ((anchor, ['FACE_REFERENCE.png', 'OUTFIT_REFERENCE.png']),
                                (sheet, ['APPROVED_FRONT.png', 'FACE_REFERENCE.png', 'OUTFIT_REFERENCE.png'])):
            encoders = [n for n in graph.api.values() if n['class_type'] == 'TextEncodeQwenImage21']
            self.assertEqual(len(encoders), 1 if graph is anchor else 3)
            for node in encoders:
                canvas = graph.api[node['inputs']['images.image_1'][0]]
                self.assertEqual(canvas['class_type'], 'EmptyImage')
                expected_refs = (['APPROVED_FRONT.png'] if node['_meta']['title'].startswith('back ·')
                                 else expected)
                actual = [source_image(graph, node['inputs'][f'images.image_{i}'])
                          for i in range(2, len(expected_refs) + 2)]
                self.assertEqual(actual, expected_refs)
                self.assertEqual(len([key for key in node['inputs'] if key.startswith('images.image_')]),
                                 len(expected_refs) + 1)
                self.assertNotIn('Picture ', node['inputs']['prompt'])
                self.assertIn('<image1>', node['inputs']['prompt'])
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

    def test_qwen21_latent_and_sampler(self):
        for graph in graphs().values():
            self.assertNotIn('2511', json.dumps(graph.api))
            for node in graph.api.values():
                if node['class_type'] == 'KSampler':
                    self.assertEqual(node['inputs']['cfg'], 1)
                    self.assertEqual(node['inputs']['steps'], 25)
                    latent = node['inputs']['latent_image']
                    self.assertEqual(latent[1], 2)
                    self.assertEqual(graph.api[latent[0]]['class_type'], 'TextEncodeQwenImage21')
                if node['class_type'] == 'SaveImage' and '개별 PNG' in node['_meta']['title']:
                    image = graph.api[node['inputs']['images'][0]]
                    self.assertEqual(image['class_type'], 'SplitImageWithAlpha')


if __name__ == '__main__':
    unittest.main()
