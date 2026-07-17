import marimo

__generated_with = "0.23.14"
app = marimo.App(width="full")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from supervisory_hooks.controller import (
        ControllerRequest,
        execute_controller_request,
        read_controller_receipt,
    )

    return (
        ControllerRequest,
        Path,
        execute_controller_request,
        mo,
        os,
        read_controller_receipt,
    )


@app.cell
def _(ControllerRequest, os):
    configured_request = os.environ.get("CUESTRAP_CONTROLLER_REQUEST")
    if configured_request is None:
        controller_request_model = None
        controller_request = {}
        repository_root = "."
        controller_state_root = "."
    else:
        controller_request_model = ControllerRequest.model_validate_json(configured_request)
        controller_request = controller_request_model.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        )
        repository_root = os.environ["CUESTRAP_CONTROLLER_REPOSITORY_ROOT"]
        controller_state_root = os.environ["CUESTRAP_CONTROLLER_STATE_ROOT"]
        expected_identity = os.environ["CUESTRAP_CONTROLLER_REQUEST_IDENTITY"]
        if controller_request_model.identity != expected_identity:
            raise ValueError("configured controller request identity mismatch")
    return (
        controller_request,
        controller_request_model,
        controller_state_root,
        repository_root,
    )


@app.cell
def _(
    Path,
    controller_request_model,
    controller_state_root,
    read_controller_receipt,
    repository_root,
):
    if controller_request_model is None:
        execution_result = {
            "schema": "cuestrap.operation-controller-result/v0",
            "status": "unconfigured",
        }
    else:
        receipt = read_controller_receipt(
            controller_request_model,
            Path(repository_root),
            Path(controller_state_root),
        )
        if receipt is None:
            execution_result = {
                "schema": "cuestrap.operation-controller-result/v0",
                "status": "pending",
            }
        else:
            execution_result = receipt.model_dump(
                by_alias=True,
                mode="json",
                exclude_none=True,
            )
    return (execution_result,)


@app.cell
def _(controller_request, execution_result, mo):
    mo.vstack(
        [
            mo.md("# Operation controller"),
            mo.md(
                "Use the typed workbook MCP adapter to inspect this bound request, "
                "execute its effect once, collect read-only diagnostics, and release "
                "the binding. Durable "
                "claim and receipt files make execution reruns inert."
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
