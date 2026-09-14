# H3 입력 오류와 그래프 연결 및 제출 중복 방지를 검증한다.
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pipeline as p


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=p.ROOT)
        self.addCleanup(self.tmp.cleanup)
        image = Path(self.tmp.name) / 'image.png'
        image.write_bytes(b'reference')
        self.spec = dict(id='shot01', images=[str(image)], prompt='<Picture 1> identity',
                         width=864, height=480, seconds=5, seed=42)

    def test_missing_audio_rejected(self):
        self.spec['prompt'] += ' <Audio 1>'
        with self.assertRaises(ValueError):
            p.validate(self.spec)

    def test_duplicate_reference_rejected(self):
        self.spec['images'] *= 2
        with self.assertRaises(ValueError):
            p.validate(self.spec)

    def test_graph_links_resolve(self):
        for turbo in (False, True):
            self.spec['turbo'] = turbo
            g = p.graph(self.spec, ['reference.png'])
            for node in g.values():
                for value in node['inputs'].values():
                    if isinstance(value, list):
                        self.assertIn(value[0], g)
            self.assertEqual(g['124']['inputs']['steps'], 4 if turbo else 20)
            self.assertNotIn('ref_image_1', g['136']['inputs'])

    def test_existing_job_never_submitted_again(self):
        directory = Path(self.tmp.name)
        p.save(directory / 'shot.json', self.spec)
        p.save(directory / 'job.json', {'job_id': 'existing'})
        with patch.object(p, 'refresh', return_value={'status': 'running'}) as refresh, patch.object(p, 'api') as api:
            p.submit(directory / 'shot.json')
            refresh.assert_called_once()
            api.assert_not_called()

    def test_recover_lost_submission_response(self):
        directory = Path(self.tmp.name)
        p.save(directory / 'job.json', {'job_id': 'ours', 'status': 'submitting'})
        queue = {'queue_running': [[1, 'prompt123', {}, {'codex_job_id': 'ours'}]], 'queue_pending': []}
        with patch.object(p, 'api', side_effect=[{}, queue, {}]):
            result = p.refresh(directory)
        self.assertEqual(result['prompt_id'], 'prompt123')
        self.assertEqual(result['status'], 'running')

    def test_cancel_does_not_interrupt_someone_else(self):
        directory = Path(self.tmp.name)
        p.save(directory / 'job.json', {'prompt_id': 'ours'})
        queue = {'queue_running': [[1, 'someone_else']], 'queue_pending': []}
        with patch.object(p, 'api', return_value=queue) as api:
            with self.assertRaises(ValueError):
                p.cancel(directory)
            api.assert_called_once_with('/queue')


if __name__ == '__main__':
    unittest.main()
