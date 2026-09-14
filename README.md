# Codex 로컬 H3 제작 실행기

현재 설치된 ComfyUI Python의 PyAV·aiohttp와 Blender 5.2를 사용한다. 새 모델이나 패키지를 설치하지 않는다. 서버 주소는 `http://127.0.0.1:8188`이며 실제 제출 전에 서버가 실행 중이어야 한다.

## 빠른 사용

PowerShell에서 `E:\Codex\movies`로 이동한 뒤 실행한다.

```powershell
.\movies.ps1 test
.\movies.ps1 pipeline validate projects/h3_baseline/shots/shot01/shot.json
.\movies.ps1 pipeline submit projects/h3_baseline/shots/shot01/shot.json
.\movies.ps1 pipeline watch projects/h3_baseline/shots/shot01
.\movies.ps1 pipeline status projects/h3_baseline/shots/shot01
.\movies.ps1 project validate projects/h3_baseline/project.json
```

`submit`은 이미 job.json이 있으면 기존 작업을 조회한다. 생성 요청의 응답이 유실되면 job_id를 이용해 서버 이력과 큐에서 복구한다. 서버를 재시작해 이력이 사라졌다면 자동 재제출하지 않으며, 결과 확인 후 새 숏 폴더에서 재시도한다. 입력 변경·재생성·Turbo 비교는 각각 새로운 숏 폴더에서 실행한다. 실행 중 shot.json을 수정하지 않는다.

`watch`는 기본 45초 동안 WebSocket 진행 이벤트를 읽고 상태를 갱신한다. `--seconds 1200`을 붙이면 최대 20분까지 현재 작업을 기다린다. 실제 대기는 로컬 Python이 처리하므로 Codex가 매번 재조회할 필요가 없다. 별도 예약 작업은 생성하지 않는다. `status`는 완료 시 MP4를 해당 숏 폴더로 회수하고 PyAV로 전체 영상·오디오를 디코드한다. 파일 길이·fps·해상도·프레임 수·오디오 검증을 통과해도 상태는 `review_required`다. 시각 품질은 별도 검토한다.

## 프로젝트와 시트

`project.json`에 전체 스토리와 순서대로 실행할 `shots` 목록을 기록한다. `register`는 제공된 시트를 프로젝트로 복사하고 자산 ID·버전·설명·SHA256을 기록한다. 동일 버전 덮어쓰기는 거부한다.

```powershell
.\movies.ps1 project init projects/demo/project.json "자동차 탑승" "여성이 차에 다가가 탑승한다."
.\movies.ps1 project register projects/demo/project.json CHAR_001 character C:/images/person.png v1 "단발, 베이지 상의"
.\movies.ps1 project register projects/demo/project.json PROP_001 prop C:/images/car.png v1 "파란 자동차"
```

`split-sheet`는 지정된 픽셀 영역을 잘라 개별 시점을 등록한다. 제공된 800×533 시트의 영역은 `character-sheet-boxes.json`에 있다. 다른 시트에서는 영역을 새로 지정해야 한다. `register-view`로 별도 이미지를 추가할 수도 있다. 신규 정지 이미지 AI 생성기는 계획상 별도 검증 항목이다.

```powershell
.\movies.ps1 project split-sheet projects/demo/project.json CHAR_001 v1 character-sheet-boxes.json
```

## Blender 프리비즈

```powershell
.\movies.ps1 project previz projects/h3_baseline/shots/shot01/previz.json projects/h3_baseline/shots/shot01/previz-v2
```

기존 출력 폴더 대신 새 버전 폴더를 지정한다. 별도 백그라운드 Blender에서 기본 도형·카메라·키프레임을 만들고 `.blend`, 장면 보고서, 시작·중간·끝 PNG를 저장한다. `--animation`을 추가하면 모든 프레임을 렌더한다. 실행 중인 사용자의 Blender에는 연결하거나 저장하지 않는다. 라이브 장면 읽기는 Higgsfield 패널 연결 후 Codex 브리지 도구로 수행한다.

오브젝트 종류는 person, car, helicopter, cube, sphere, cylinder, cone이다. 위치와 크기는 미터, 회전은 라디안이다. 세부 얼굴·옷·표면은 만들지 않는다. 현재 위치·회전 키프레임은 오브젝트 전체에 적용하며 관절 리그는 아직 없다.

## 프리비즈를 H3 참조로 연결

```powershell
.\movies.ps1 project bind projects/demo/project.json projects/demo/renders/previz shot01 "Use <Picture 1> for character identity. Use <Picture 2> only for composition. Photorealistic, one person." projects/demo/shots/shot01/shot.json --asset CHAR_001@v1
.\movies.ps1 project advance projects/demo/project.json
```

`bind`는 인물의 정면 시점과 사물의 3/4 시점이 등록되어 있으면 이를 우선 선택하고, 없으면 합성 시트를 사용한다. 마지막에 Blender 대표 프레임을 연결한다. 여러 `--asset`을 쓰면 Picture 번호도 그 순서대로 지정해야 한다. 현재 구현은 대표 RGB 이미지 경로다. 프리비즈 영상·Depth·Pose 제어와 fl2va 경로는 후속 검증 대상이다.

`advance`는 프로젝트를 검사하고 첫 미완료 숏 하나만 제출한다. 결과가 검토 필요·실패 상태이면 멈추므로 불필요한 다음 생성이 이어지지 않는다.

숏의 `anchor_first`에 0부터 시작하는 참조 이미지 번호를 지정하면 `MiniMaxH3AddGuide`로 그 이미지를 첫 프레임에 연결한다. 예를 들어 네 번째 참조인 이전 숏 마지막 프레임을 사용하려면 `"anchor_first": 3`으로 지정한다. 기존 작업을 바꿀 때는 새로운 숏 폴더에 복사하여 원래 결과를 유지한다.

`pipeline cancel <숏 폴더>`는 그 숏의 대기 항목만 제거하거나 그 숏이 유일한 실행 작업일 때 중단 요청을 보낸다. 다른 사람의 작업이 실행 중이면 중단하지 않는다.

## 검토와 편집

얼굴·의상·등장 수·사물 외형·카메라·깜빡임·오디오를 확인한 뒤 판단을 기록한다.

```powershell
.\movies.ps1 project approve projects/demo/shots/shot01 "사용자 확인. 인물과 동작 및 음향 적합."
.\movies.ps1 project assemble projects/demo/project.json projects/demo/deliverables/final.mp4
```

승인 전 연결 검사용 영상은 `assemble`에 `--preview`를 붙여 만든다. 해당 출력 보고서에는 `mode: preview`가 기록된다. 최종 사용자 승인으로 처리되지 않는다. `link-previous <이전 숏 폴더> <다음 shot.json>`으로 앞 숏의 마지막 프레임과 연속성 지시를 다음 숏의 참조에 추가할 수 있다.

승인된 숏만 명세 순서대로 이어 붙인다. 모든 입력의 해상도·fps가 같아야 한다. H.264/AAC로 출력하며 기존 결과 덮어쓰기를 거부한다. 복잡한 믹싱·자막·전환 효과는 구현 범위에 포함되지 않는다.

## 구현과 검증 상태

`checklist.md`와 `context-notes.md`에 실제 검증 결과를 기록한다. 코드가 있다는 사실과 실 생성·품질 검증 통과를 구분한다. 최초 인물 기준 생성의 합격 전에는 본편 3개 숏의 품질을 보장하지 않는다.
