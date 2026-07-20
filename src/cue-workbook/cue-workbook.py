import marimo

__generated_with = "0.23.14"
app = marimo.App(width="full")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo

    from harness import (
        DEFAULT_LT01_INTENT,
        DEFAULT_WORKBOOK_REQUEST,
        DirectSession,
        NativeBindingUnavailable,
        execute_native_probe,
        qualify_lt01_matrix,
        run_architecture_validation,
        summarize_value,
    )

    return (
        DEFAULT_LT01_INTENT,
        DEFAULT_WORKBOOK_REQUEST,
        DirectSession,
        NativeBindingUnavailable,
        Path,
        execute_native_probe,
        mo,
        qualify_lt01_matrix,
        run_architecture_validation,
        summarize_value,
    )


@app.cell
def _(DEFAULT_WORKBOOK_REQUEST, Path):
    execution_mode = "interactive"
    repo_root = str(Path.cwd())
    workbook_request = DEFAULT_WORKBOOK_REQUEST
    return execution_mode, repo_root, workbook_request


@app.cell
def _(DEFAULT_LT01_INTENT):
    lt01_intent = DEFAULT_LT01_INTENT
    return (lt01_intent,)


@app.cell
def _(mo):
    run_environment = mo.ui.run_button(label="Validate locked environment")
    run_probe = mo.ui.run_button(label="Run qualified native probe")
    run_lt01 = mo.ui.run_button(label="Qualify deterministic LT-01 matrix")
    direct_source = mo.ui.text_area(
        label="Interactive CUE source",
        value="x: int & >=0\nx: 2",
        rows=5,
    )
    run_direct = mo.ui.run_button(label="Compile live native value")
    mo.vstack(
        [
            mo.md("# CUE bootstrap workbook"),
            mo.md(
                "Qualified mode compares an isolated gopy worker with the independent "
                "`cueprobe` process. Direct mode retains live Go-backed values and is exploratory only."
            ),
            mo.hstack([run_environment, run_probe, run_lt01]),
            mo.md("## Interactive native surface"),
            direct_source,
            run_direct,
        ]
    )
    return direct_source, run_direct, run_environment, run_lt01, run_probe


@app.cell
def _(
    Path,
    execution_mode,
    repo_root,
    run_architecture_validation,
    run_environment,
):
    if run_environment.value or execution_mode == "validate":
        environment_result = run_architecture_validation(Path(repo_root))
    else:
        environment_result = {"status": "pending"}
    return (environment_result,)


@app.cell
def _(
    Path,
    execute_native_probe,
    execution_mode,
    repo_root,
    run_probe,
    workbook_request,
):
    if run_probe.value or execution_mode == "probe":
        try:
            probe_result = execute_native_probe(Path(repo_root), workbook_request)
        except Exception as error:
            probe_result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
    else:
        probe_result = {"status": "pending"}
    return (probe_result,)


@app.cell
def _(
    Path,
    execution_mode,
    qualify_lt01_matrix,
    repo_root,
    run_lt01,
):
    if run_lt01.value or execution_mode == "lt01":
        try:
            lt01_result = qualify_lt01_matrix(Path(repo_root))
        except Exception as error:
            lt01_result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
    else:
        lt01_result = {"status": "pending"}
    return (lt01_result,)


@app.cell
def _(
    DirectSession,
    NativeBindingUnavailable,
    direct_source,
    run_direct,
    summarize_value,
):
    direct_result = {"status": "pending"}
    direct_value = None
    if run_direct.value:
        try:
            direct_session = DirectSession.open()
            direct_value = direct_session.compile(direct_source.value, "interactive.cue")
            direct_result = {
                "status": "exploratory",
                "identity": direct_session.identity,
                "summary": summarize_value(direct_value),
                "proxyType": type(direct_value).__name__,
            }
        except NativeBindingUnavailable as error:
            direct_result = {"status": "unavailable", "error": str(error)}
        except Exception as error:
            direct_result = {"status": "error", "error": f"{type(error).__name__}: {error}"}
    return direct_result, direct_value


@app.cell
def _(
    direct_result,
    direct_value,
    environment_result,
    execution_mode,
    lt01_intent,
    lt01_result,
    mo,
    probe_result,
    workbook_request,
):
    mo.vstack(
        [
            mo.md(f"**Execution mode:** `{execution_mode}`"),
            mo.md("## Iteration request"),
            mo.json(workbook_request),
            mo.md("## Environment"),
            mo.json(environment_result),
            mo.md("## Qualified observations"),
            mo.json(probe_result),
            mo.md("## Deterministic LT-01 intent"),
            mo.json(lt01_intent),
            mo.md("## LT-01 execution and CUE derivation evidence"),
            mo.json(lt01_result),
            mo.md("## Direct exploratory observation"),
            mo.json(direct_result),
            mo.md(
                f"Live proxy: `{type(direct_value).__name__}`"
                if direct_value is not None
                else "Live proxy: none"
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Code-mode transaction marker

    This durable cell was created through the constrained bootstrap client.
    """)
    return


if __name__ == "__main__":
    app.run()
