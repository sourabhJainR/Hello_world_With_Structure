# Portable Runtime Boundary

`portable/` is the provider-neutral execution substrate. It owns repository modeling, task planning, execution, evidence adapters, execution contracts, capability semantics, and adaptive recommendations that can operate without host-specific integrations.

`.ai-harness/`, `.agents/`, `.claude/`, provider adapters, external integrations, and architecture documentation are host surfaces. They may call portable contracts but portable code must not import them.

The portable distribution may package selected host-facing skills and metadata through its build process, but packaging does not change dependency direction or runtime authority.

A host integration may add transport, credentials, UI, model/provider selection, reporting, or persistence behind an explicit adapter. It may not introduce a second repository model, execution engine, evidence store, capability catalog, or release authority.
