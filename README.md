# Foundation

Architecture blueprint for a capability-based, event-driven Linux desktop built around a system-wide Knowledge Graph.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19119730.svg)](https://doi.org/10.5281/zenodo.19119730)

## What this is

This repository contains the LaTeX source for the architecture document. It covers the full system stack: event pipeline (eBPF), Knowledge Graph (SQLite + Ladybug), AI layer, Wayland compositor fork, shell, permission model, and roadmap.

The compiled PDF is published on Zenodo:

> Kicker, T. (2026). *A Capability-Based, Event-Driven Linux Desktop: Knowledge Graph Architecture and Design Rationale* (1.0). Zenodo. https://doi.org/10.5281/zenodo.19119730

## Building

```bash
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Requires a standard LaTeX distribution with `biblatex`, `tikz`, `tabularx`, and `listings`.

## Status

Design phase complete. Implementation starting now. See the roadmap in Chapter 10.

## License

CC BY 4.0
