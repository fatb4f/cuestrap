import marimo

__generated_with = "0.23.14"
app = marimo.App(width="full")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo

    from supervisory_hooks.controller import (
        ControllerRequest,
        execute_controller_request,
    )

    return ControllerRequest, Path, execute_controller_request, mo


@app.cell
def _():
    execution_mode = "interactive"
    repository_root = "."
    controller_state_root = "."
    controller_request = {}
    return controller_request, controller_state_root, execution_mode, repository_root


@app.cell
def _(
    ControllerRequest,
    Path,
    controller_request,
    controller_state_root,
    execute_controller_request,
    execution_mode,
    repository_root,
):
    if execution_mode == "execute":
        try:
            request = ControllerRequest.model_validate(controller_request)
            receipt = execute_controller_request(
                request,
                Path(repository_root),
                Path(controller_state_root),
            )
            execution_result = receipt.model_dump(
                by_alias=True,
                mode="json",
                exclude_none=True,
            )
        except Exception as error:
            execution_result = {
                "schema": "cuestrap.operation-controller-result/v0",
                "status": "error",
                "error": f"{type(error).__name__}: {error}",
            }
    else:
        execution_result = {
            "schema": "cuestrap.operation-controller-result/v0",
            "status": "pending",
        }
    return (execution_result,)


@app.cell
def _(controller_request, execution_result, mo):
    mo.vstack(
        [
            mo.md("# Disposable operation controller"),
            mo.md(
                "One fresh reactive runtime validates and executes one bounded general "
                "action. Durable claim and receipt files make reactive reruns inert."
            ),
            mo.md("## Request"),
            mo.json(controller_request),
            mo.md("## Execution receipt"),
            mo.json(execution_result),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
