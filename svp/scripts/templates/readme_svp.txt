================================================================================
                        SVP-MANAGED PROJECT NOTICE
================================================================================

This project is managed by the Stratified Verification Pipeline (SVP).

IMPORTANT: Files in this project are protected by a two-layer write
authorization system:

  1. Pre-commit hooks prevent unauthorized modifications to pipeline-controlled
     files (pipeline_state.json, blueprint documents, verified source files).

  2. The SVP orchestration layer enforces write permissions at runtime,
     ensuring that only authorized pipeline operations can modify protected
     artifacts.

Do NOT manually edit pipeline-controlled files. All changes must flow through
the SVP pipeline to maintain verification integrity.

To interact with this project, use the `svp` command:

    svp start          Start or resume the pipeline
    svp status         Show current pipeline state
    svp restore        Restore example project files
    svp help           Show available commands

For more information about SVP, refer to the project documentation.

================================================================================
