# 12_CONTRIBUTING - ColonyOS

Thank you for your interest in contributing to **ColonyOS**! As an open-source project designed to model high-quality system engineering, we maintain strict standards for code architecture, formatting, and unit testing.

---

## 🛠️ Setting Up the Development Environment

### 1. Prerequisites
* **Python 3.13+** (ensuring access to typing and queue additions)
* **Poetry** (package manager and dependency manager)

### 2. Install Project Dependencies
```bash
# Clone the repository
git clone https://github.com/ashmitt/ColonyOS.git
cd SpaceCLIGame

# Install virtualenv and dependencies
poetry install

# Spawn a shell within the project virtual environment
poetry shell
```

---

## 🎨 Coding Standards & Quality Tools

We use automated checkers to maintain readability and catch bugs before commit. Run these tools locally before pushing code:

### 1. Code Formatting (Black)
All code must conform to the Black style standard (line length 100).
```bash
# Check code formatting
poetry run black --check src/ tests/

# Auto-format files
poetry run black src/ tests/
```

### 2. Linting (Ruff)
Ruff enforces PEP8 conventions, clean imports, and checks for common code smells.
```bash
# Run the linter
poetry run ruff check src/ tests/
```

### 3. Static Type Checking (Mypy)
We enforce strict type hinting across all modules.
```bash
# Validate static typing
poetry run mypy src/
```

---

## 📝 Commit Message Conventions

We follow the **Conventional Commits** specification for commit logs:

```text
<type>(<scope>): <short description>

[Optional Body]
```

### Types:
* `feat`: A new user-facing feature (e.g., adding Round Robin scheduler).
* `fix`: A bug fix (e.g., resolving SQLite lock exception).
* `docs`: Documentation modifications only.
* `test`: Adding or correcting tests.
* `refactor`: Code changes that neither fix bugs nor add features.

### Examples:
* `feat(scheduler): implement Shortest Job First selection logic`
* `fix(worker): release DB lock when worker energy is depleted`
* `docs(readme): add installation guide for Poetry environment`

---

## 📋 Pull Request (PR) Checklist

Before submitting a PR for review, ensure you have ticked all items below:

1. [ ] **Passes all checks**: `ruff`, `black`, and `mypy` run with zero errors.
2. [ ] **Test Coverage**: All new functionality has corresponding unit or integration tests. Total coverage remains $\ge 90\%$.
3. [ ] **All tests pass**: `poetry run pytest` returns 100% success.
4. [ ] **Documentation**: Any changes to APIs, config structures, or CLI commands have been documented in the appropriate `docs/` files.
5. [ ] **Branch Naming**: Branch follows naming schema `feature/feature-name` or `bugfix/issue-name`.
