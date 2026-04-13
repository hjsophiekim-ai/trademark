# trademark project guide

## Start every task this way
- First inspect the repository and summarize the stack, entry points, and run/build/test commands.
- Before changing code, say which files you plan to edit and why.
- Keep changes minimal and local.

## Safety rules
- Ask before adding a new dependency.
- Ask before deleting files, renaming folders, editing environment variables, or changing deployment settings.
- Do not touch secrets, tokens, or production credentials unless explicitly asked.

## Validation
- Detect the existing package manager and use the lockfile already in the repo.
- Prefer existing scripts from package.json, Makefile, pyproject.toml, or other project configs.
- After each code change, run the smallest relevant validation command that already exists.
- If no automated test exists, explain manual verification steps.

## Output format
- Report changed files.
- Report commands run.
- Report test/build/lint results.
- Report remaining risks or follow-up items.

## Language
- Talk to me in Korean.
