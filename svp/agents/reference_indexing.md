# Reference Indexing Agent

## Role

The reference indexing agent processes reference documents and repositories, producing structured summaries for use by other agents throughout the pipeline.

## Interaction Pattern

Single-shot interaction. The agent receives the full document content (or repository access via GitHub MCP), produces a structured summary, and exits with a terminal status line.

## Document Reference Handling

For document references:

1. Receives the full document content as task prompt.
2. Produces a structured summary containing:
   - What the document is.
   - Topics covered.
   - Key terms.
   - Relevant sections.
3. Saves the summary to `references/index/`.

## Repository Reference Handling

For repository references:

1. Explores the repository via GitHub MCP.
2. Produces a structured summary of the repository contents, structure, and relevant components.
3. Saves the summary to `references/index/`.

If GitHub MCP is not configured, the agent offers to configure it.

## Availability

Available during Stages 0-2 only.

## Context

Receives the full document or repository (via GitHub MCP) as task prompt.

## Default Model

Defaults to Sonnet-class (`claude-sonnet-4-6`).

## Terminal Status Lines

The reference indexing agent MUST produce exactly one terminal status line:

- `INDEXING_COMPLETE` -- the document or repository has been indexed successfully.

The terminal status is written to `.svp/last_status.txt`.
