# Launch the loopback-only Marimo code-mode MCP listener.
marimo-listener:
    direnv exec . uv run --project . --locked --exact -- \
        marimo edit --headless --no-token --host 127.0.0.1 --port 2718 --mcp code-mode \
        src/cue-workbook/cue-workbook.py

# Closed hook transports. Each payload is a versioned, digest-bound request that
# the Python runner revalidates before invoking argv without a shell.
hook-shell-read payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-git-read payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-git-mutation payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-apply-patch payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-workspace-mutation payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-evaluate-cue payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-evaluate-python payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-evaluate-go payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"

hook-just-introspection payload:
    @uv run --project "{{justfile_directory()}}" --locked --exact -- \
        python "{{justfile_directory()}}/src/cue-workbook/supervisory_hooks/recipe_runner.py" \
        --repository-root "{{justfile_directory()}}" "{{payload}}"
