# ADR-0001: Hexagonal Architecture Layering and Invariants

- **Status**: Accepted
- **Date**: 2026-10-19
- **Author**: Jimrit

## Context
The smartmech video pipeline generates automated vertical short-form videos requiring multiple disparate AI models, media utilities, and publishing targets. Without strict architectural boundaries, vendor specifics (e.g. Gemini, Veo, ElevenLabs, Whisper, YouTube) bleed into domain logic, making testing brittle and replacement costly.

## Decision
We enforce a strict hexagonal (ports and adapters) layered architecture:
1. **`domain`**: Pure entities, value objects, schemas, and invariants. Dependencies: Standard library + Pydantic only. Zero external dependencies.
2. **`ports`**: Protocols and abstract definitions. Dependencies: `domain` only.
3. **`application`**: Use cases, workflows, and policies. Dependencies: `domain` + `ports` only.
4. **`adapters`**: Concrete technology/vendor implementations. Dependencies: `domain` + `ports` only. Adapters NEVER import each other.
5. **`interface`**: User/CLI entrypoint (Typer). Dependencies: `application` + `compose` only.
6. **`compose`**: Composition root. The ONLY place permitted to import `adapters`.

## Enforcement
Architectural boundaries are mechanically enforced in CI via `import-linter` contracts (`.importlinter`). Any violation immediately fails the CI build.

## Consequences
- Clean separation of concerns; domain logic is completely decoupled from API providers.
- Highly testable using in-memory and local mock adapters.
- New vendors or alternative models can be plugged in by implementing a port without touching application or domain code.
