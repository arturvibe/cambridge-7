# AI Agent Task Prompts

Self-contained prompts for AI agents to implement features in parallel.

## Task Overview

| # | Task | Prompt File | Dependency |
|---|------|-------------|------------|
| 1 | Firestore Repository | [01-firestore-repository.md](./01-firestore-repository.md) | None |
| 2 | Google Photos Integration | [02-google-photos-integration.md](./02-google-photos-integration.md) | None |
| 3 | Adobe Frame.io Integration | [03-adobe-frameio-integration.md](./03-adobe-frameio-integration.md) | None |
| 4 | Token Encryption | [04-token-encryption.md](./04-token-encryption.md) | None |
| 5 | Dynamic OAuth Scopes | [05-oauth-scopes-expansion.md](./05-oauth-scopes-expansion.md) | None |

## Parallel Execution

All tasks can be started simultaneously. They work on different modules:

```
Task 1 → app/infrastructure/firestore_repository.py
Task 2 → app/integrations/google/
Task 3 → app/integrations/adobe/
Task 4 → app/infrastructure/encryption.py
Task 5 → app/oauth/scopes.py
```

## How to Use

1. Give the prompt file content to an AI agent
2. Agent reads required files from the codebase
3. Agent implements the feature
4. Agent creates tests
5. Merge results

## Integration Points

After parallel tasks complete:

1. **Firestore + Encryption**: Update FirestoreRepository to use TokenEncryption
2. **Google + Scopes**: Update Google service to validate scopes
3. **Adobe + Scopes**: Update Adobe service to validate scopes

## Prerequisites

Each task assumes:
- OAuth foundation is complete (`app/oauth/`, `app/users/`)
- Magic link auth works
- Agent can read AGENTS.md for conventions
