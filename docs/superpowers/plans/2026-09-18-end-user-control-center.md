# End-User Control Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Add a dependency-free AER control-center CLI that makes installation health, background execution, durable sessions, learning state, and recent reports visible without creating a second runtime or state store.

**Architecture:** A new \`portable/aer_diagnostics.py\` module provides read-only aggregation over the existing AER owners. \`portable/aer_runtime.py\` only routes new subcommands to that module; no execution semantics move into diagnostics. Documentation and deterministic tests prove the user-facing contract.

**Tech Stack:** Python 3.11+, stdlib only for diagnostics, existing SQLite state stores, unittest, GitHub Actions.

**Spec:** \`docs/superpowers/specs/2026-09-18-end-user-control-center-design.md\`

## Global Constraints

- Diagnostics are read-only and must never create a second source of truth.
- Existing build, verify, install, update, check-update, and rollback behavior must remain compatible.
- Missing optional providers are warnings, not hard failures.
- JSON output contains a stable \`command\`, \`status\`, and domain payload.
- The portable bundle must include \`portable/aer_diagnostics.py\` through the existing \`portable/\` payload rule.
- No third-party runtime dependency may be introduced.

---

### Task 1: Add the diagnostics control-center module

**Files:**
- Create: \`portable/aer_diagnostics.py\`
- Test: \`tests/test_aer_diagnostics.py\`

**Interfaces:**
- Produces \`collect_status(aer_home: Path | str | None = None, project_root: Path | str | None = None) -> dict[str, object]\`.
- Produces \`run_doctor(aer_home: Path | str | None = None, project_root: Path | str | None = None) -> dict[str, object]\`.
- Produces \`list_sessions(aer_home: Path | str | None = None, project_root: Path | str | None = None) -> dict[str, object]\`.
- Produces \`trigger_status(trigger_id: str, aer_home: Path | str | None = None) -> dict[str, object]\`.
- Produces \`learning_status(aer_home: Path | str | None = None, project_root: Path | str | None = None) -> dict[str, object]\`.
- Produces \`render_text(report: Mapping[str, object]) -> str\`.
- Produces \`render_json(report: Mapping[str, object]) -> str\`.

- [ ] **Step 1: Write the failing tests for provider and installation diagnostics**

~~~python
class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.aer_home = self.home / ".aer"

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def test_status_reports_missing_install_as_unconfigured(self):
        report = collect_status(self.aer_home)
        self.assertEqual(report["status"], "unconfigured")
        self.assertFalse(report["installation"]["active"])

    def test_doctor_missing_install_has_actionable_error(self):
        report = run_doctor(self.aer_home)
        self.assertEqual(report["status"], "error")
        self.assertTrue(any(item["name"] == "active_installation" and item["status"] == "error"
                            for item in report["items"]))

    def test_provider_absence_is_warning_not_error(self):
        with mock.patch("portable.aer_diagnostics.shutil.which", return_value=None):
            report = run_doctor(self.aer_home)
        provider_items = [item for item in report["items"] if item["name"].startswith("provider:")]
        self.assertTrue(provider_items)
        self.assertTrue(all(item["status"] == "warning" for item in provider_items))
~~~

- [ ] **Step 2: Run the focused tests and confirm import/implementation failures**

Run: \`python -m unittest tests.test_aer_diagnostics -v\`

Expected: FAIL because \`portable.aer_diagnostics\` does not yet provide the diagnostics functions.

- [ ] **Step 3: Implement installation/provider status collection**

~~~python
def _provider_status() -> list[dict[str, str]]:
    providers = ("claude", "codex", "gemini")
    return [
        {
            "name": f"provider:{name}",
            "status": "ok" if shutil.which(name) else "warning",
            "detail": "available on PATH" if shutil.which(name) else "CLI not found; integration remains optional",
        }
        for name in providers
    ]

def _installation_status(aer_home: Path) -> dict[str, object]:
    active_path = aer_home / "active.json"
    current = aer_home / "current"
    if not active_path.is_file() or not (current.exists() or current.is_symlink()):
        return {"active": False, "status": "unconfigured", "version": None, "source_commit": None}
    try:
        active = json.loads(active_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"active": False, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
    install_json = current / "install.json"
    if not install_json.is_file():
        return {"active": False, "status": "error", "error": "active installation is missing install.json"}
    return {
        "active": True,
        "status": "ok",
        "version": active.get("version"),
        "source_commit": active.get("source_commit"),
        "bundle_sha256": active.get("bundle_sha256"),
        "install_root": active.get("install_root"),
    }
~~~

- [ ] **Step 4: Add read-only SQLite, session, trigger and report aggregation**

Use only \`SELECT\`/PRAGMA queries. Never write from diagnostics.

~~~python
def _db_integrity(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {"status": "warning", "detail": "state database not created yet"}
    try:
        with sqlite3.connect(path, timeout=5) as db:
            result = db.execute("PRAGMA integrity_check").fetchone()
        return {"status": "ok" if result and result[0] == "ok" else "error",
                "detail": str(result[0] if result else "no result")}
    except sqlite3.Error as exc:
        return {"status": "error", "detail": f"{type(exc).__name__}: {exc}"}
~~~

Trigger aggregation must report counts by \`pending\`, \`claimed\`, \`success\`, \`failed\`, and \`cancelled\` when the table exists. Sessions must validate each checkpoint with the existing \`SessionStore.load\` contract before reporting it as recoverable.

- [ ] **Step 5: Implement the five public reports and text/JSON renderers**

Each report must contain \`command\`, \`status\`, \`generated_at\`, a domain-specific payload, and \`items\` for doctor checks.

The doctor status is \`error\` when any item is \`error\`, \`warning\` when there are warnings but no errors, otherwise \`ok\`.

Text rendering must keep normal output compact and readable, with a final \`Next:\` line when actionable information exists.

- [ ] **Step 6: Run focused diagnostics tests**

Run: \`python -m unittest tests.test_aer_diagnostics -v\`

Expected: PASS.

- [ ] **Step 7: Commit**

~~~bash
git add portable/aer_diagnostics.py tests/test_aer_diagnostics.py
git commit -m "feat: add AER end-user diagnostics"
~~~

---

### Task 2: Expose the control center through the stable CLI

**Files:**
- Modify: \`portable/aer_runtime.py\`
- Modify: \`aer_cli.py\`
- Test: \`tests/test_aer_cli_control_center.py\`

**Interfaces:**
- Adds commands:
  - \`status [--project-root PATH] [--aer-home PATH] [--json]\`
  - \`doctor [--project-root PATH] [--aer-home PATH] [--json]\`
  - \`sessions [--project-root PATH] [--aer-home PATH] [--json]\`
  - \`trigger-status TRIGGER_ID [--aer-home PATH] [--json]\`
  - \`learning [--project-root PATH] [--aer-home PATH] [--json]\`
- Existing commands retain their current parser and return behavior.

- [ ] **Step 1: Write failing CLI tests**

~~~python
class ControlCenterCliTests(unittest.TestCase):
    def test_status_json_is_machine_readable(self):
        result = subprocess.run(
            [sys.executable, "-m", "portable.aer_runtime", "status", "--json", "--aer-home", str(self.aer_home)],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["command"], "status")
        self.assertIn("installation", payload)

    def test_doctor_json_returns_nonzero_for_actionable_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "portable.aer_runtime", "doctor", "--json", "--aer-home", str(self.aer_home)],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "error")
~~~

- [ ] **Step 2: Run the focused CLI tests and confirm failures**

Run: \`python -m unittest tests.test_aer_cli_control_center -v\`

Expected: FAIL because the new subcommands are not registered.

- [ ] **Step 3: Add the parser subcommands and dispatch**

Import the diagnostics functions at the bottom of \`portable/aer_runtime.py\` rather than copying their logic.

~~~python
def _diagnostic_parser(parent, *, project=False):
    parent.add_argument("--aer-home", type=Path, default=None)
    if project:
        parent.add_argument("--project-root", type=Path, default=None)
    parent.add_argument("--json", action="store_true")
    return parent
~~~

Dispatch each command to the matching function and write either JSON or \`render_text\` output. Return \`1\` only for \`doctor\` when its report status is \`error\`; all other successful read-only queries return \`0\`.

- [ ] **Step 4: Preserve the outer \`aer_cli.py\` behavior**

The outer launcher must continue to accept a bare bundle path and install it exactly as before. No diagnostic command may bypass runtime loading, repository isolation, or the existing install/update code path.

- [ ] **Step 5: Run focused CLI tests**

Run: \`python -m unittest tests.test_aer_cli_control_center -v\`

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add portable/aer_runtime.py aer_cli.py tests/test_aer_cli_control_center.py
git commit -m "feat: expose AER control center CLI"
~~~

---

### Task 3: Make sessions resumable from the user's perspective

**Files:**
- Modify: \`portable/session_state.py\`
- Modify: \`portable/adaptive_runtime.py\`
- Modify: \`portable/aer_diagnostics.py\`
- Test: \`tests/test_session_recovery_metadata.py\`

**Interfaces:**
- Extends \`SessionCheckpoint\` with optional \`project_root: str | None = None\` and \`intent: str | None = None\`.
- Existing checkpoint JSON without these fields remains loadable.
- \`sessions\` reports a \`resume_hint\` containing the stored task/session identifiers and project root, without executing work.

- [ ] **Step 1: Write the failing persistence test**

~~~python
def test_checkpoint_preserves_resume_context(self):
    store = SessionStore(self.home / "sessions")
    checkpoint = SessionCheckpoint(
        session_id="s1",
        task_id="t1",
        project_key="p1",
        stage="verify",
        project_root="/workspace/service",
        intent="Fix authentication timeout",
    )
    store.save(checkpoint)
    restored = store.load("s1")
    self.assertIsNotNone(restored)
    self.assertEqual(restored.project_root, "/workspace/service")
    self.assertEqual(restored.intent, "Fix authentication timeout")
~~~

- [ ] **Step 2: Run the test and confirm the missing-field failure**

Run: \`python -m unittest tests.test_session_recovery_metadata -v\`

Expected: FAIL because \`SessionCheckpoint\` does not persist the two fields.

- [ ] **Step 3: Add backward-compatible fields and populate them from \`AdaptiveRuntime.run\`**

Give both fields default values of \`None\`, and when constructing the checkpoint pass the resolved project root and original intent.

- [ ] **Step 4: Expose a safe resume hint**

The diagnostics layer must produce text such as:

~~~text
resume_hint: open the same repository with the stored session context
session_id: s1
task_id: t1
project_root: /workspace/service
stage: verify
~~~

It must not automatically execute the task, change files, or grant permissions.

- [ ] **Step 5: Run focused session tests**

Run: \`python -m unittest tests.test_session_recovery_metadata -v\`

Expected: PASS.

- [ ] **Step 6: Commit**

~~~bash
git add portable/session_state.py portable/adaptive_runtime.py portable/aer_diagnostics.py tests/test_session_recovery_metadata.py
git commit -m "feat: expose durable session resume context"
~~~

---

### Task 4: Add end-user documentation and regression coverage

**Files:**
- Modify: \`README.md\`
- Modify: \`portable/README.md\`
- Modify: \`docs/USAGE_AND_PLATFORM_INTEGRATION.md\`
- Modify: \`.claude-plugin/plugin.json\`
- Modify: \`.claude-plugin/marketplace.json\`
- Test: \`tests/test_aer_diagnostics.py\`

**Interfaces:**
- Documentation presents a three-command first-run path: \`status\`, \`doctor\`, then normal host invocation.
- Version moves from \`22.1.0\` to \`22.2.0\` in both plugin manifests because the control-center surface is user-visible.

- [ ] **Step 1: Add the golden-path documentation**

Document:

~~~bash
python aer_cli.py status
python aer_cli.py doctor
python aer_cli.py sessions
python aer_cli.py learning
python aer_cli.py trigger-status <trigger-id>
~~~

Explain that these commands are read-only and do not modify the target repository.

- [ ] **Step 2: Document JSON output as the future UI/IDE contract**

Show:

~~~bash
python aer_cli.py status --json
python aer_cli.py doctor --json
~~~

State that fields are intended for automation while the human renderer remains the primary interactive output.

- [ ] **Step 3: Bump the plugin version consistently**

Set both plugin manifests to \`22.2.0\` and update the marketplace plugin entry to the same version.

- [ ] **Step 4: Run the relevant deterministic tests**

Run:
~~~bash
python -m unittest tests.test_aer_diagnostics tests.test_aer_cli_control_center tests.test_session_recovery_metadata -v
python scripts/run_evals.py --json
~~~

Expected: all focused tests pass and routing/policy evals remain release-ready.

- [ ] **Step 5: Commit**

~~~bash
git add README.md portable/README.md docs/USAGE_AND_PLATFORM_INTEGRATION.md .claude-plugin/plugin.json .claude-plugin/marketplace.json tests/
git commit -m "docs: add AER control center golden path"
~~~

---

### Task 5: Full repository verification and pull request

**Files:**
- No source changes unless verification reveals a concrete regression.

- [ ] **Step 1: Run the complete deterministic suite locally when execution tooling is available**

Run:
~~~bash
python -m unittest discover -s tests -v
python scripts/run_evals.py
python scripts/run_p0_evals.py
python scripts/run_p1_evals.py
python scripts/run_p2_evals.py
python scripts/run_full_suite.py
python aer_cli.py build --output /tmp/aer-portable.zip
python aer_cli.py verify /tmp/aer-portable.zip
~~~

- [ ] **Step 2: Inspect the diff for scope, ownership and repository-isolation regressions**

Specifically confirm:
- diagnostics never writes to SQLite;
- no duplicate memory/scheduler/trigger owners were introduced;
- bundle inclusion is automatic through the existing \`portable/\` source inclusion;
- existing install/update/rollback commands are behaviorally compatible where no change was requested.

- [ ] **Step 3: Push the feature branch and open a pull request against \`main\`**

Use the title:
\`feat: add end-user AER control center\`

The PR body must list the new commands, compatibility guarantees, focused tests, and full-suite verification status.

- [ ] **Step 4: Inspect all CI checks, not only the primary harness check**

Wait for every check on the PR to reach a terminal state. If any check fails, inspect its job log, patch only the concrete defect, push a follow-up commit, and repeat the full verification.

- [ ] **Step 5: Review the finished PR for end-user impact**

Verify:
- a new user can diagnose installation state without opening source;
- missing optional providers are clearly distinguishable from broken AER state;
- background jobs expose their status;
- durable sessions expose enough context to resume manually;
- learning status is visible but advisory;
- no safety gate is weakened.

- [ ] **Step 6: Merge only after all checks are green**

Use the existing repository merge policy and leave the branch history auditable.
