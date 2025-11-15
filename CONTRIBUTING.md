# Contributing to Cambridge

Thank you for your interest in contributing to Cambridge!

## Commit Message Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes that affect the build system or external dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

### Scope (Optional)

The scope should be the name of the affected component (e.g., `webhook`, `terraform`, `docker`, `ci`).

### Subject

The subject should be a short description of the change:

- Use the imperative, present tense: "change" not "changed" nor "changes"
- Don't capitalize the first letter
- No period (.) at the end

### Examples

#### Good commit messages:

```
feat(webhook): add support for Frame.io V5 webhooks

Implement parsing logic for V5 webhook payloads with new field structure.

Closes #123
```

```
fix(docker): correct app path in Dockerfile

Updated COPY command to reference app/main.py instead of main.py
```

```
docs: add testing section to README

Include instructions for running unit tests with pytest and coverage reporting.
```

```
test: add unit tests for health endpoints

Implement comprehensive tests for / and /health endpoints with 100% coverage.
```

```
ci: add Conventional Commits validation

Add commitlint workflow to enforce commit message format on all PRs.
```

#### Bad commit messages:

```
Update files
```

```
Fixed bug
```

```
WIP
```

```
feat: Added new feature.
```
(Should use present tense: "add new feature" without period)

### Validation

All commits are automatically validated using [commitlint](https://commitlint.js.org/) in the CI pipeline. Commits that don't follow the convention will cause the build to fail.

### Testing Locally

You can test your commit messages locally before pushing:

```bash
# Install commitlint
npm install -g @commitlint/cli @commitlint/config-conventional

# Test the last commit
npx commitlint --from HEAD~1 --to HEAD --verbose

# Test a commit message directly
echo "feat: add new feature" | npx commitlint
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Make your changes
4. Write tests for your changes
5. Ensure all tests pass (`pytest`)
6. Commit your changes following the commit convention
7. Push to your fork
8. Open a Pull Request

## Code Quality

- All code must pass existing tests
- New features should include tests
- Maintain or improve code coverage (currently 90%)
- Follow Python best practices and PEP 8 style guide

## Questions?

If you have questions or need help, please open an issue in the repository.
