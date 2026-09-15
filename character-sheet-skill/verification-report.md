# 검증 결과

## 통과

- 런타임은 `E:/Comfy-Desktop/ComfyUI-Installs/ComfyUI/ComfyUI/.venv/Scripts/python.exe`를 사용했다.
- `python -X utf8 -m unittest discover -s character-sheet-skill -p test_assemble.py -v` — 4개 통과. 4/6칸 크기, 비율 유지, 원본 바이트 보존, 기존 버전 거부, 잘못된 입력, 한 칸 교체 시 나머지 패널 해시 보존을 검증했다.
- `python -X utf8 C:/Users/elmos/.codex/skills/.system/skill-creator/scripts/quick_validate.py character-sheet-skill/character-sheet` — `Skill is valid!`.
- 개인 설치 폴더의 SKILL.md, 프롬프트 문서, 스크립트 SHA256을 원본과 비교해 일치를 확인했다.
- 내장 ImageGen 호출로 가상 성인 캐릭터 기준 이미지 생성. 얼굴·정면 전신·신발·흰 배경을 육안 확인했다.

## 남은 검증

- 사용자 진행 요청으로 기준 이미지 선택 확정. 기본 4칸 생성 및 측면 한 칸 재생성 완료. v001/v002의 패널·참조·시트 총 12개를 디코드하고 실제 크기와 기록 해시를 검증했다. 변경 패널은 3번만이며 1·2·4번은 보존됐다. 2048×2048 합성 결과 육안 확인.
- 사용자 사진은 제공되지 않아 사진 기반 동일성 검증을 수행하지 않았다.
- 여섯 스타일과 네 시트 유형 전체의 실제 생성 품질은 검증하지 않았다.
- 후속 턴의 사용 가능한 스킬 목록에서 character-sheet가 발견됨을 확인했다.

## 환경 문제

초기 샌드박스 테스트는 tempfile 폴더 접근 거부로 실패했다. 정상 권한 재실행은 통과했다. 번들 Python에는 PyYAML이 없어 기존 설치 런타임을 사용했다.

## 실 생성 후 저장 수정

- 최종 폴더가 tempfile의 제한된 Windows 권한을 상속하여 미리보기가 거부되는 문제를 확인했다. 부모 권한을 상속하는 고유 스테이징 폴더로 변경했다.
- 동일 unittest 명령으로 4개 재통과. 수정 스크립트를 개인 스킬에 반영하고 SHA256 일치를 확인했다.
- `assemble_sheet.py request-v002.json --output v003` 실행 성공. v003은 v002와 동일한 선택 이미지를 접근 가능한 폴더에 다시 저장한 버전이다.
- 샌드박스 안에서 v003의 PNG 6개를 디코드하고 크기·해시를 확인했다. `view_image`로 합성 시트 직접 열기 성공. 최종 전달 경로는 `output/character-sheets/TEST_001/v003/sheet.png`다.
