# 미사용 모델 삭제 검증

- 범위. `user/default/workflows`의 저장된 ComfyUI 워크플로 6개와 `extra_model_paths.yaml`의 J:\LTX2.5 모델 경로.
- 삭제 전. 실모델 16개 중 8개가 저장된 워크플로 어느 곳에서도 참조되지 않았다. `python model-cleanup/audit_models.py`로 `inventory-before.json`을 확보하고 `& 'E:\Codex\movies\model-cleanup\remove_unused_models.ps1'`의 실행 전 검사에서 동일한 8개와 65.47GiB를 확인했다.
- 삭제. `& 'E:\Codex\movies\model-cleanup\remove_unused_models.ps1' -Execute` 성공. 정확히 8개, 70,298,775,354바이트를 삭제했다. MiniMax H3 FL2VA 1개, 구형 Qwen 인코더·VAE 2개, LTX 2.5 모델 5개다. `deletion-report.json`에 정확한 경로와 크기를 기록했다. 프로젝트 설치 스크립트·기록과 ComfyUI 설정은 유지했다.
- 삭제 후. 삭제 대상 8개 모두 `Test-Path`가 거짓이고 `python model-cleanup/audit_models.py`의 `unresolved model names`가 `{}`다. 남은 실모델 8개 모두 저장된 워크플로에 참조된다.
- 실행 환경. ComfyUI `/queue`가 실행 0·대기 0을 반환했다. `/object_info`에 남은 8개 파일명이 모두 존재한다. `python -m unittest discover -s character-sheet-comfy -p 'test_*.py' -v`에서 4개 테스트가 통과했다. 실제 이미지·영상 재생성은 수행하지 않았다.
