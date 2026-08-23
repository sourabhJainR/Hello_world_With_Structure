# Coding Style and Naming Decision Policy

## Precedence

1. Explicit repository/team instruction.
2. Dominant local pattern for the same responsibility and technology.
3. When multiple local patterns are valid, choose the most advanced, scalable, maintainable, compatible, well-tested, and operationally proven local pattern.
4. When no suitable local pattern exists, choose the current mature mainstream convention for the language/ecosystem and task.

## Evidence to inspect

Before adding code, inspect nearby examples for:

- file and directory names
- type/class/interface names
- method/function names
- constants
- namespaces/packages/modules
- visibility/modifier ordering
- imports/includes
- async/concurrency style
- error/exception handling
- dependency registration
- configuration
- logging and telemetry
- test naming and location

## Multiple local patterns

Do not mix patterns by preference. Compare candidates on:

- recency
- breadth of adoption in the repository
- test coverage
- maintainability
- scalability
- compatibility with public contracts
- operational maturity
- consistency with adjacent code

Use the strongest pattern for the responsibility being changed, not the most fashionable pattern in the repository.

## New areas

A new pattern is justified only when there is no suitable local pattern or the existing pattern has a demonstrated limitation. Record the decision, alternatives considered, and compatibility impact.

Third-party frameworks require an explicit dependency decision in `.ai-harness/DEPENDENCIES.md` before incorporation.