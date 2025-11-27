# Agents Guide

1. The primary task description lives in `agent-docs/task.md`. Refer to it to understand the end goal and requirements.
2. `agent-docs/design-doc.md` captures what we aim to achieve and the architectural/technical plan for getting there.
3. `agent-docs/planning.md` is the single source of truth for current progress and the roadmap. 
4. Only execute tasks that appear in `planning.md`. 
5. When new ideas or next steps arise, add them to `planning.md` first—do not start work before it’s tracked there.
6. Keep the implementation details like bash commands out of `planning.md`.
7. All the assumptions are stored in `info.md`.
8. If something was not clear and we needed an assumption to make decision, we write the assumption to `info.md`.
9. Simplicity is prefered at each step. We don't add a requirement or dependecy until we really need it. We don't introduce complexity until the simple solution proves to be not suitable.
