## Commit Message Convention

We follow Conventional Commits with a small rule for readability in Korean teams.

Format

type(scope): subject
Rules
type must be in English (feat, fix, refactor, chore, docs, test)
scope must be in English (module, domain, or component name)
subject should be written in Korean
Body (optional) can be written in Korean
Examples
feat(auth): JWT 로그인 기능 추가
fix(redis): Redis 클라이언트 초기화 위치 수정
refactor(chat): 서비스 레이어 분리
docs(readme): 실행 방법 문서화
Why
Keeps compatibility with Conventional Commits tools
Git logs are easy to read for Korean developers
Works well with changelog, semantic versioning, and LLM-based tools