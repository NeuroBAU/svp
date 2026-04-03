# Project Context: GoL Plugin

## Project Name

GoL Plugin (Game of Life -- Claude Code Plugin)

## Domain

Computational biology / cellular automata demonstration. This is a Claude Code plugin that generates, benchmarks, and compares three algorithmic implementations of Conway's Game of Life. It serves as a reference example of the Claude Code plugin archetype (archetype C) within the SVP ecosystem.

## Problem Statement

Conway's Game of Life has multiple well-known implementation strategies with dramatically different performance characteristics. A naive grid scan is simple but O(n^2) per generation. Hashlife achieves sub-linear amortized time through memoization but has significant constant overhead. Sparse-set approaches offer a middle ground by tracking only live cells.

Developers evaluating these strategies need to generate correct implementations, benchmark them under controlled conditions, and compare results -- but doing so manually is tedious and error-prone. This plugin automates the entire workflow.

## What the Plugin Delivers

A Claude Code plugin with three slash commands and three backing agents:

- `/gol:generate` -- Generates a Game of Life implementation using a selected strategy (naive, hashlife, or sparse).
- `/gol:evaluate` -- Benchmarks an implementation across configurable grid sizes and generation counts.
- `/gol:report` -- Produces a ranked comparison of all benchmarked implementations.

One orchestration skill coordinates the generate-evaluate-report workflow end-to-end.

## Architecture

Four implementation units:

1. **GoL Strategies** (Python) -- Pure computation: three GoL step functions and a timing wrapper.
2. **Plugin Infrastructure** (plugin_markdown + plugin_json) -- Plugin manifest, agent definitions, skill definition as string constants.
3. **Command Definitions** (plugin_markdown) -- Slash command definition files as string constants.
4. **Assembly** (Python) -- Writes the plugin directory structure from the constants and source code.

## Technical Context

- Primary language: Python (strategy implementations, assembly logic).
- Artifact languages: plugin_markdown (agent/skill/command definitions), plugin_json (plugin manifest).
- Archetype: `claude_code_plugin` (archetype C).
- No external dependencies beyond Python standard library.
- Grid representation: 2D list of ints (0/1) for naive and hashlife; set of (row, col) tuples for sparse.
- Benchmarking uses `time.perf_counter` for wall-clock timing.
