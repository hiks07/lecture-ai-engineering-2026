# 3회차 구현 과제: 내일 확인할 내용

구현은 준비되어 있지만 실제 Gemini 실행과 본인의 답안 확인은 남아 있습니다. PR은 만들지 않았습니다.

## Codespaces에서 코드 가져오기

기존 Codespaces를 사용해도 됩니다. 먼저 저장하지 않은 변경이 있는지 확인하세요.

```bash
git status
git fetch origin
git switch --track origin/codex/lec03
```

`codex/lec03` 로컬 브랜치가 이미 있다면 마지막 명령 대신 `git switch codex/lec03`을 사용합니다.
`git status`에 수정 중인 파일이 있으면 버리거나 강제로 전환하지 말고 먼저 그 변경을 확인하세요.

## API 호출 없이 확인

```bash
uv run pytest -q
uv run python -m app.agent --list-tools
```

개발용 일시 환경에서 저장소의 `uv.lock` 그대로 설치하여 **25 passed**를 확인했습니다.
`TestModel`은 실제 Gemini를 호출하지 않습니다. 도구 목록에는 기존 도구 2개와 `make_quiz`, `save_learning_log`가 나옵니다.

## Gemini로 직접 확인

Codespaces의 `GEMINI_API_KEY` 설정이 필요합니다. 다음 명령은 실제 API를 사용합니다.

```bash
uv run python -m app.agent --trace "LoRAとは何ですか？用語集を確認し、学んだ要点を学習記録に保存してください。"
```

`[承認待ち] save_learning_log`와 저장할 내용이 표시되면 내용을 읽고 `y`를 입력합니다.
그 후 `learning_log/`에 새 `.md` 파일이 생기는지 확인합니다.

```bash
ls -lt learning_log/
```

동일 명령을 다시 실행하고 이번에는 `n` 또는 Enter를 입력하세요. 새 파일이 추가되지 않아야 합니다.
저장을 요청하지 않은 일반 질문에서는 자동으로 저장하지 않도록 지시했습니다.
이 동작의 실제 모델 판단은 직접 확인해야 합니다.

공통 연습도 확인할 수 있습니다.

```bash
uv run python -m app.agent --trace "第2回の内容から確認問題を1問出して"
uv run python -m app.agent --trace "LoRAとQLoRAの違いは？"
uv run python -m app.ask "AIE2026の講座で使う「lecNN-start タグ」とは何ですか？"
uv run python -m app.agent --trace "AIE2026の講座で使う「lecNN-start タグ」とは何ですか？"
```

`[tool call]`의 이름·인수, `[usage]`의 `requests`, 일반 LLM과 에이전트 답변의 차이를 보고 `answer.md`의 미확인 항목을 채우세요.
테스트용 가짜 모델 결과를 실제 Gemini의 응답이나 호출 횟수로 적으면 안 됩니다.

## 코드 흐름

- `app/tools.py`: `make_quiz`는 지정 회차의 첫 용어로 문제와 답을 만듭니다. `save_learning_log`는 새 파일에 UTF-8로 저장하며 기존 파일을 덮어쓰지 않습니다.
- `app/agent.py`: 저장 도구를 `requires_approval=True`로 등록합니다. `run_with_approval`이 `DeferredToolRequests`에서 멈추고 확인을 받은 뒤, 승인 결과와 대화 이력으로 실행을 이어갑니다.
- `tests/test_learning_log.py`: 승인 전·후, 거절, 빈 입력, 입력 중단, 빈 본문, 덮어쓰기 방지를 확인합니다. 파일은 테스트용 임시 폴더에만 생성됩니다.

이번 구현은 기본 실행 모드의 로컬 도구를 대상으로 합니다. `--mcp`는 후속 강의용 기존 경로이며 이번 저장 도구는 등록하지 않았습니다.
`learning_log/`는 기존 `.gitignore`에 포함되어 있으므로 개인 학습 기록은 제출 커밋에 넣지 않습니다.
`answer.md`를 확인·수정한 뒤, 직접 `codex/lec03` → 본인 fork의 `main` PR을 만들면 됩니다.
강의 예시의 `lec03` 대신 작업 브랜치 접두사를 붙인 이름을 썼으며 PR 방향은 동일합니다.
