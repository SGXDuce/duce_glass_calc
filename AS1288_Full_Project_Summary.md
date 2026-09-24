# AS 1288 Glass Thickness Calculator — Full Project Summary
## Duce Timber Windows and Doors
### Version: V1.32 (Accessibility/usability audit pass — six fixes live-verified: label association, keyboard focus visibility (including a toggle-group outline-clipping bug found and fixed mid-session), result-label contrast (required two passes to hit the correctly-specified selectors), tooltip keyboard access, report modal focus trap, clear-fields confirmation. Separately, clipboard copy-as-image removed entirely — permanently broken on the live HTTP site due to the Clipboard API's secure-context requirement — superseded by the unaffected download-as-image path. Pushed to both `origin` and `cpanel` (live) by Sahil.)
### Last Updated: 4 September 2026

---

## Changelog

Every update to this document is logged here. Before editing, check the latest entry — if it wasn't from your chat, another chat has updated the file since you last saw it. Read the changes before overwriting.

### v1.32 — 4 September 2026 — Accessibility/usability audit pass (six fixes, live-verified); clipboard copy-as-image removed, superseded by download-as-image

**Commit hash:** not recorded in this session — Sahil to fill in from `git log` once committed.

**Six accessibility/usability findings addressed, sourced from a structured audit** (`frontend-design-audit`, a third-party Claude Code plugin run against `interfaces/flask_app/templates/index.html`/`static/style.css`, scored against 15 established usability heuristics — 15 findings total, six selected as worth fixing for this internal-then-external tool, the rest deferred or skipped as low-value for the current user base; see "Deferred/skipped" below):

1. **Label/input association.** Every `<label class="field-label">` across all four pathways was a sibling of its input with no `for` attribute — zero screen-reader association, no click-to-focus. Fixed: 27 single-field labels got `for="<id>"`; 25 grouped controls (toggle-groups, checkbox groups, which have no single field a `for` can target) got `role="group" aria-labelledby="<id>"` instead — the standard accessible pattern for that control shape, a deliberate deviation from a literal "add `for`" instruction. Checkbox-row labels already correctly wrapped their inputs and were left alone.

2. **Keyboard focus visibility, including a toggle-group-specific bug found during live testing.** Added a global `:focus-visible` outline (2px, `#f47920`, the existing accent) plus a stronger `.field-input`/`.field-select` focus ring. First live click-test pass found every `.toggle-group` button (Safety glass required, Bushfire requirement, Wind load input method, Glazing configuration, and equivalents across pathways) had a working `:focus-visible` rule in CSS that was invisible in the browser — root cause: `.toggle-group`'s `overflow: hidden` (present to clip the group's rounded corners between adjoining buttons, unrelated to focus styling) was clipping the outline at the container edge. Fixed with `outline-offset: -3px` on `.toggle-group .toggle-btn:focus-visible` (draws the ring inward instead of removing `overflow: hidden`, which would have broken the corner-rounding). A second issue found in the same pass: the active/selected button's orange fill is the same hue as the global focus-outline color, making an inward ring on an already-selected button nearly invisible — added `outline-color: #1a1a1a` specifically for `.toggle-btn.active:focus-visible`. Both fixes live-verified via Claude in Chrome, independently of the Claude Code session that wrote them: tabbed directly to the selected "Yes" (bushfire) and "Window" (element type) toggle buttons, confirmed via `getComputedStyle` (`outline-color: rgb(26, 26, 26)`, `outline-style: solid`, negative `outline-offset`, `:focus-visible` matching true) and visually via zoomed screenshot that a dark ring is clearly distinguishable against the orange fill.

3. **Result-label contrast, required two passes.** `.result-label` text (`ULS minimum thickness`, `SLS minimum thickness`, etc.) was `#555` on near-black card backgrounds (`#111`/`#1a1a1a`), well under WCAG AA's 4.5:1 minimum for normal text. First fix changed the base `.result-label` rule to `#999` — live-measured afterward at ~3.2:1 (pass cards) and ~3.5:1 (fail cards), still failing, because every rendered result card carries `.pass` or `.fail`, and the higher-specificity `.result-card.pass .result-label`/`.result-card.fail .result-label` rules were what actually rendered, not the base rule that got changed. Second pass targeted the correct selectors, live-measured each color along its own hue toward its `.result-value` sibling, landing on `#578f6a` (pass) and `#af7474` (fail) — re-measured live at 4.984:1 and 5.011:1, both clearing AA with margin. `.version-footer`/`.footer-note` were already compliant (6.109:1 measured live) and left unchanged.

4. **Tooltip keyboard access.** All ~44 `.tip` ("?") help icons across every pathway responded only to `mouseenter`/`mouseleave`, invisible to keyboard-only users — the sole documentation for terms like BAL, ULS/SLS, N/C-rating. Added `tabindex="0" role="button"` to each, and wired `focus`/`blur`/`click` handlers into `attachTooltipListeners()` alongside the existing mouse handlers, reusing the same show/hide logic. Live-verified: tooltip appears on focus (no keypress needed), disappears on blur, existing mouse-hover behaviour unaffected.

5. **Report modal dialog semantics.** `.report-modal` had no `role="dialog"`, no `aria-modal`, no `aria-labelledby`, no focus trap, and didn't return focus on close — a keyboard user could Tab straight out of an open modal into the page behind it, and lost their place entirely after closing it. Fixed: `role="dialog" aria-modal="true" aria-labelledby="report-modal-title"` added (with a matching `id` added to the header title span), focus moves into the modal on open and is trapped within it via Tab/Shift+Tab, and `closeReportModal()` restores focus to the button that opened it. Existing Escape-to-close and overlay-click-to-dismiss behaviour untouched. Live-verified via Claude in Chrome: Tab cycled only within the modal, Escape closed it and returned focus correctly to the triggering button.

6. **"Clear fields" confirmation.** `clearFields()` and its p2/p3/p4 equivalents wiped all inputs and results immediately with no confirmation, sitting directly under Calculate — a single misclick on an 8–10 field Pathway 2/3 form lost everything with no recovery path. Fixed: a shared `confirmClearFields()` helper guards all four `clear*Fields()` functions, using a native `window.confirm()` prompt, skipped automatically when the form has no typed values and no checked boxes (nothing to lose). Live-verified indirectly — the native dialog blocks browser-automation calls entirely while open, which is itself the expected signature of a genuine blocking confirm; the specific Cancel-preserves-data sub-case was confirmed by direct manual check rather than automation.

**Deferred/skipped from the same audit, for the record:** inline field validation on blur, `aria-live` announcement of errors/warnings, draft persistence/unload warning — real but lower-value, not actioned this session. Responsive breakpoints and the tooltip icon's touch-target size were dismissed outright after confirming with Sahil the tool is desktop/laptop-only in practice, not used on tablets on-site. Minor cosmetic findings (modal title `id` — folded into fix 5 above anyway; copy/download button visual differentiation, now moot per the removal below; beta-tag/warning color overlap) were skipped as low value for a small internal-then-external user base.

**Separately: clipboard copy-as-image feature removed entirely, superseded by download-as-image.** `copySnapshotAsImage()` (the `ti-copy` button, using `navigator.clipboard.write`/`ClipboardItem`) depends on the Clipboard API's secure-context requirement — it worked during dev testing because `localhost` is always treated as a secure context, but is silently, permanently broken on the live site (`glazing.duce.com.au`, plain HTTP) until SSL is added (Section 9). Rather than leave a permanently broken button live, removed entirely: the button, its `ti-copy` icon, the `copySnapshotAsImage()` function body (including the `ClipboardItem`/`clipboard.write` call and its catch block), across all 8 pathway/mode variants (Pathway 1 Mode 1 & 2 & fail-card, Pathway 2 pass & Mode 2 & fail-card, Pathway 3, Pathway 4). `buildSnapshotHTML()` and `generateSnapshotCanvas()` (the shared hidden-template rendering, confirmed via investigation to have no dependency on the removed function) are unchanged and remain shared with `downloadSnapshotAsImage()`, which is now the sole image-export path and is unaffected by the secure-context issue. Live-verified via Claude in Chrome, independently of the Claude Code session that made the change: zero `copySnapshotAsImage` references and zero `.ti-copy` icons anywhere in the live DOM after running a real calculation; one working `downloadSnapshotAsImage` function/button confirmed present. Section 2's tech-stack note on `html2canvas` updated to reflect it now serves download only, not copy.

**Note correcting this document's own prior framing:** earlier entries and general project notes referred to the clipboard-copy failure as a "known bug, unfixable until SSL." That framing is now moot — the feature was removed, not fixed. Anyone reading history prior to this entry should read those references as describing a since-removed feature, not an open bug.

**Scope discipline maintained throughout:** both changes touched only `interfaces/flask_app/templates/index.html` and `interfaces/flask_app/static/style.css`; confirmed via `git diff --stat` at each stage that nothing under `engine/` was touched. Full 8-suite regression (57/57 pytest + 3 standalone scripts, matching the standing gate) re-confirmed passing after both changes, as expected for UI-only work.

**Verification method, worth noting given the standing discipline (Section 0):** every claim in this session was independently spot-checked, not taken from Claude Code's narrative summaries alone — `git diff --stat` run directly by Sahil to confirm file scope before each commit; the regression suite's raw output eyeballed directly after an initial pasted summary rendered with corrupted table formatting; a Playwright script Claude Code wrote and ran itself was explicitly flagged, unprompted, as not independent verification (same session wrote both the fixes and the checks) when its results were first presented as a "22/22 click-test suite" — a phrasing that overstated its rigor as an established tool rather than an ad hoc script; the two highest-stakes claims (the active-toggle-button outline color, and the clipboard removal) were both re-verified live via Claude in Chrome, driven from claude.ai independently of the Claude Code session, before being accepted. The ad hoc Playwright script (`scratchpad/click_test.py`, not currently checked into the repo) is a real working harness against the actual rendered DOM and is worth formalising into the repo at some point — it's most of the way to the Playwright automated test suite already on this document's roadmap as the highest-priority structural improvement (Section 0/8) — but wasn't pulled in this session; flagged so it isn't lost if Claude Code's scratchpad gets cleared.

**Outstanding as of this entry:** commit hash to be filled in once Sahil commits (see top of this entry). The `scratchpad/click_test.py` Playwright harness should be formalised into the repo rather than left as a temp script. Everything else from v1.31's outstanding list (version 2.0 vs 2.1 discrepancy, SSH key rotation) remains open, untouched this session.

---

### v1.31 — 3 September 2026 — Hosting deployment pipeline confirmed working end-to-end; server-level login active

**No code changes this entry — deployment/infrastructure confirmation only.**

**Root cause of blocked SSH access identified: server firewall, not the SSH key.** The `cpanel` remote (blocked since v1.30) was diagnosed by testing `Test-NetConnection glazing.duce.com.au -Port 2683` from two independent networks (office Wi-Fi and mobile hotspot) — both returned `TcpTestSucceeded: False` with successful ping, confirming a network-level block on port 2683 specifically, not a DNS, ISP, or key-authorisation issue. This ruled out an initial concern that the wrong SSH key fingerprint had been sent to Brent (fingerprint `SHA256:AnxQ7ZrJm3H37hW7jMDUDGkA7fK8ouS8gcSBKqqmXAs` confirmed unchanged and correctly matching what was sent).

**Brent's resolution: IP allowlisting rather than opening the port publicly.** Brent stated broad public SSH access "doesn't test safely" and instead whitelisted two specific IPs on the server firewall: Sahil's public IP (from the Duce office network) and Brent's own. This is a narrower, safer access model than a fully open port. Practical consequence: `git push cpanel master` will only succeed from the whitelisted office network — pushing from Sahil's other work location will fail with the same timeout symptom unless that IP is also whitelisted. Not yet raised with Brent as a limitation since Sahil confirmed he works from the whitelisted office 4/5 days a week and can schedule pushes accordingly.

**First live deployment executed successfully.** `ssh -p 2683 glazingd@glazing.duce.com.au` connected cleanly (host key accepted, passphrase entered). `git remote -v` confirmed both remotes correctly configured (`origin` → GitHub HTTPS, `cpanel` → SSH port 2683). `git push -u cpanel master` completed without error: cPanel returned `status: 1`, no errors/warnings in the response payload, and queued deployment via `VersionControlDeployment`. This is the first-ever successful push through the `cpanel` remote since it was added in v1.30 — the deploy pipeline (`git push cpanel master` → `.cpanel.yml` → Passenger restart) is now confirmed functional, not just configured.

**Deployment confirmed live via browser check, not just push success.** Push succeeding and cPanel queueing a deployment doesn't by itself confirm Passenger actually restarted the app cleanly — verified separately by loading the live site and confirming the footer shows only the version number (`2.1`), with no "expires" text. This confirms the v1.30 cosmetic fix (commit `4bcbb0c`, previously stuck on GitHub only) is now genuinely live on the server, not just committed.

**Server-level login now active on the live site.** Brent has locked the site behind HTTP-level authentication: username `duceteam`, single shared credential across all staff (not per-user), owned and managed on Brent's side — Sahil is not the credential administrator, consistent with his stated preference not to be the long-term access manager. This appears to supersede the previously-discussed Linux VPS + Cloudflare Access (email OTP) plan from the earlier hosting discussion — that plan was never implemented under the cPanel/Passenger model Brent ultimately used, and Brent's own instructions never mentioned it. Treat the Cloudflare Access plan as superseded, not paused, unless Brent indicates otherwise. Longer-term, this shared server-level credential is intended to be replaced by a login built into the app itself, not yet scoped or actioned.

**Confirmed routine deployment workflow going forward, no Brent involvement required per push:**
```
git push origin master   # GitHub backup, unaffected by any of the above
git push cpanel master   # live deploy — only works from a whitelisted IP
```

**Minor discrepancy noticed, not yet investigated:** live footer displays app version `2.1`, while this document has tracked the app version as `2.0` since v1.29. Worth confirming next session whether `APP_VERSION` in `app.py` was bumped separately (e.g. via a Claude Code session not reflected in this document) or whether this is a display inconsistency.

**Process note — SSH key passphrase security.** The key's passphrase (set in the v1.30 session) was typed into chat a second time this session, when Sahil forgot it and asked for it to be retrieved from conversation history. Flagged again as no longer a private credential. Not actioned yet — worth regenerating the key pair with a fresh passphrase entered only at the terminal (never in chat) at a convenient point, not urgent enough to block current work.

**Outstanding as of this entry:** Confirm with Brent whether IP allowlisting can be extended if Sahil's work pattern changes (not currently needed — parked, not raised). Version number discrepancy (2.0 vs 2.1) to be checked. SSH key rotation for passphrase hygiene, not actioned. Everything else from the v1.30 "outstanding" list (SSH authorisation, first deploy, root cause of non-launch) is now resolved by this entry.

### v1.30 — 25 August 2026 — Hosting migration: cPanel/Passenger deployment path with Brent, SSH key exchange, expiry footer cosmetic fix

**Commit hash** 4bcbb0c

**Hosting model clarification needed.** Brent (external IT provider) sent deployment instructions describing cPanel/WHM shared hosting with Passenger (git push triggers `.cpanel.yml`, deploys to `/home/glazingd/duce_glass_app`, live at `glazing.duce.com.au`) — a different hosting model than the previously-discussed Linux VPS + Cloudflare Access approach. No mention of Cloudflare Access auth in Brent's instructions. Not yet resolved with Brent whether this replaces or supplements the VPS/Cloudflare plan — flagged, not actioned.

**SSH key generated and exchanged.** Ed25519 key pair generated locally (passphrase-protected). Public key sent to Brent for authorisation on the cPanel server; deployment access (`git push cpanel master`) remains blocked pending his confirmation.

**Git remote configured.** `cpanel` remote added pointing to `ssh://glazingd@glazing.duce.com.au:2683/home/glazingd/repos/duce-glass-deploy`. `origin` (GitHub, HTTPS) confirmed unchanged.

**Repo sync — Brent's deployment files pulled from GitHub.** Local repo was 4 commits behind `origin/master`; Brent had already committed `.cpanel.yml`, `passenger_wsgi.py`, `requirements.txt`, and a test file (`pulltest.txt`) directly to GitHub. Pulled clean via fast-forward.

**Deployment compatibility checked against actual codebase — no mismatch found.** `passenger_wsgi.py`'s import (`from interfaces.flask_app.app import app as application`) confirmed to resolve correctly against the existing `interfaces/flask_app/app.py` structure. `requirements.txt` (`flask`, `pandas`) checked against every import statement across `engine/` and `interfaces/` — confirmed complete; all other imports are Python standard library or internal modules, not missing pip packages. App isn't launching on Brent's server for a reason not yet diagnosed from the repo side — next step is the actual Passenger error log, requested from Brent (not yet received as of this entry).

**EXPIRY_DATE enforcement confirmed scoped to the EXE only — no functional change needed for server deploy.** `EXPIRY_DATE` (`app.py`) is enforced only in `launcher.py`'s `if datetime.datetime.now() > EXPIRY_DATE` check — `launcher.py` is the PyInstaller/EXE entry point, never imported by `passenger_wsgi.py` (which imports `interfaces.flask_app.app` directly). Confirmed by reading both files. The expiry block will not run on the server.

**Cosmetic fix applied: expiry date removed from server-facing display.** `app.py`'s `EXPIRY_DATE` was still being passed into the template purely for display (`index.html`'s version footer: `{{ app_version }} — expires {{ expiry_date }}`), which would show a permanently stale "expires 31 August 2026" message on the live server past that date. Fixed: `index.html`'s footer changed to `{{ app_version }}` only; `app.py`'s `render_template()` call had the now-unused `expiry_date=EXPIRY_DATE.strftime(...)` argument removed. `EXPIRY_DATE` itself is unchanged and still used by `launcher.py` for the EXE build. Both changes verified via `git diff` before commit (single-line changes each, no unintended edits), committed together, pushed to GitHub.

**Outstanding as of this entry:** First `cpanel` deploy (`git push cpanel master`) blocked on Brent authorising the SSH key. Root cause of "app isn't launching" not yet identified — awaiting Passenger error log from Brent. Whether the cPanel/Passenger model replaces or supplements the VPS/Cloudflare Access plan is unresolved.

### v1.29 — 30 July 2026 — 2.0 release prep: version bump, testing-wording removed, label consistency, degree-symbol fix, regression runner script

**Commit hash** b8bd477e67c76dad076aaebfe21204ff09de7d61

**This session prepares the tool for its first release to actual users, not internal testers** — a different bar than every prior EXE build, which shipped under an explicit "testing build" framing (Section 8 of the user guide, the footer, and the launcher console message all said so). Three separate decisions were confirmed directly with Sahil before any code changed:

1. **"Testing build" wording drops entirely** — replaced with just the version and expiry, no qualifier.
2. **`EXPIRY_DATE` stays at 31 August 2026 for now** — the kill-switch mechanism itself is not being retired, host migration to the Linux VPS (Brent, ongoing) still hasn't landed, so EXE-via-OneDrive with an expiry remains the live distribution method.
3. **`PATHWAY_4_ENABLED` stays `False`** — unchanged, still pending Michael's scope discussion.

**1. Version bump (`app.py`).**
- `APP_VERSION = 'V2'` → `APP_VERSION = '2.0'`.
- `.version-footer` string (`index.html`): `'{{ app_version }} — testing build expires {{ expiry_date }}'` → `'{{ app_version }} — expires {{ expiry_date }}'`. Renders as `2.0 — expires 31 August 2026`.
- `launcher.py`'s expiry console message: `'This testing version has expired (...).'` → `'This version has expired (...).'`.
- Searched the full codebase for other user-facing "testing"/"testing build" wording — none found. One near-miss deliberately left alone: `app.py`'s report trace line `"Testing thickness {t}mm against all active checks:"` — this describes the engine's own thickness-search logic (an engineering sense of "testing," not build-maturity), confirmed as a different meaning and correctly not touched.

**2. Edge-selector label consistency (`index.html`).** Pathway 2's "Edge configuration" and Pathway 3's "Unframed edge condition (Table 5.3 joint count)" — two different labels for functionally the same 2-edge/3-edge toggle — unified to **"Edge Support Configuration"** in both places (`index.html:435`, `index.html:665`). Label text only: form field `id`/`name`, JS handlers (`setP2EdgeCondition`, `setP3EdgeCondition`), and payload keys (`support_condition`, `unframed_edge_condition`) all confirmed unchanged — both selectors still POST identical keys/values after the change. Tooltips (lines 436, 666) left untouched, confirmed they didn't repeat the old label wording. Zero engine impact, confirmed by full regression.

**3. Degree symbol fix.** Literal `"deg"` replaced with `"°"` in three user-facing spots:
- `index.html:2200` — the copy-as-image snapshot card's support-condition line (`${payload.angle_deg}deg facet, ...` → `...${payload.angle_deg}° facet, ...`).
- `app.py:929` — Pathway 3's report header (`'Pathway 3 — Faceted Structural Silicone (90-160 deg)'` → `(90-160°)`).
- `app.py:944` — the report's "Included Angle" line (`f"...{angle_deg} deg"` → `f"...{angle_deg}°"`).
- `Included angle (deg)` form field label (`index.html:648`) deliberately left as-is — different case, correctly-formatted unit suffix, not the same bug.
- Variable/key names (`angle_deg`, `mitre_angle_deg`), CSS `rotate(0deg)`, and internal code comments left untouched — not user-facing output.
- Encoding verified both directions: on-screen via `<meta charset="UTF-8">` (`index.html:4`); TXT report via `app.py:433`'s explicit `report.encode('utf-8')`, confirmed no BOM, and cross-checked against the report's pre-existing em-dash (`—`) literal already proving the encode/decode pipeline round-trips non-ASCII correctly.

**4. Full 8-suite regression — genuinely confirmed clean, with a discoverability gap found and closed.** Running `pytest tests/ -v` alone only collects **57 of the 77 tracked test cases** — `test_runner.py`, `test_runner_2.py`, and `test_structural_consistency.py` are standalone scripts (script-level `run_mode1_test()`/`run_mode2_test()`/`print_summary()` functions, none prefixed `test_`, no `assert`-based pytest structure), not pytest-discoverable suites, and were silently absent from every prior session's "8-suite regression" pytest invocation without erroring or warning. Confirmed by running each directly (`python tests/test_runner.py`, etc.) — all three pass clean: 19/19, 17/17, and full structural-consistency (Mode 1 and Mode 2 key-set checks, including the pre-existing, already-documented `[UNVERIFIED]` Mode 2 synthetic-ERROR-path skip, excluded from the pass/fail count per existing precedent). Combined with the 57/57 pytest result, this is a genuine, complete 77-test-case-plus-structural-consistency regression, zero failures.

**5. New `run_tests.bat` / `run_tests.sh` at repo root — single-command full regression runner**, closing the gap found in item 4 for every future session. Both scripts:
- `cd` to the repo root via the script's own location (`%~dp0` / `$BASH_SOURCE`), so they run correctly regardless of the caller's working directory (verified: ran `run_tests.bat` from `C:\Users\sahilx` and `run_tests.sh` from `/tmp`, both correctly located the repo and passed).
- Prefer `.venv\Scripts\python.exe` when present, falling back to plain `python`.
- Run all 4 steps in order: the 5-suite pytest command, then the 3 standalone scripts directly.
- **Genuine finding: none of the 3 standalone scripts call `sys.exit(1)` on a mismatch** — confirmed by reading each script's `__main__` block — they print a `MISMATCH(ES) FOUND`/`STRUCTURAL INCONSISTENCY FOUND` line and fall off the end, so the process always exits 0 regardless of pass/fail. Exit-code-only checking would silently report false passes. Fixed by grepping each script's captured stdout for its own exact success line (`ALL TEST CASES PASSED`, `ALL NEW TEST CASES PASSED`, `ALL STRUCTURAL CHECKS PASSED`) rather than trusting the exit code alone.
- Verified this detection actually works, not just assumed: a failure was deliberately, temporarily forced into `test_structural_consistency.py` (`overall_ok = False`), rerun, confirmed the grep-based check correctly caught it and the batch file returned exit code 1 — then reverted immediately, `git status`/`git diff --stat` confirmed zero net changes to any test file afterward.
- Final output is a 4-line PASS/FAIL summary plus an overall verdict, so a failure is impossible to miss even with the full verbose pytest output scrolling past above it.

**Going forward, `run_tests.bat` (or `run_tests.sh`) is the standing "run the full regression" command** — replaces the previous multi-command sequence (pytest + 3 separate direct script invocations) that had to be manually reconstructed each session.

**Not yet done as of this entry — explicitly outstanding, not assumed complete:** the EXE has not been rebuilt for 2.0 yet. `AS1288_Calculator_V2.exe` in `dist/` still reflects the pre-2.0 build. Per this project's standing discipline (Section 0), being committed/tested at the source level does not mean the distributed artifact reflects it — the rebuild (same `.spec`, `--noconfirm`), HTTP-level verification against the built EXE itself (not the dev server), and a live-browser click-test of the built EXE are all still required before 2.0 is treated as release-ready. This entry will need a follow-up ("v1.29 continued" or a new entry) once that's done, matching the pattern of every prior EXE-rebuild session (v1.26/v1.27/v1.28).

### v1.29 (continued) — 30 July 2026 — EXE rebuilt and verified for the 2.0 release, closing out this session's outstanding item

**Pre-build checks, all confirmed before building:** `APP_VERSION = '2.0'` (`app.py:23`), `EXPIRY_DATE` unchanged (31 August 2026), `PATHWAY_4_ENABLED = False` unchanged, zero "testing build"/"testing version" matches anywhere in the codebase (case-insensitive search), both "Edge Support Configuration" labels present in `index.html`.

**Build:** `.venv\Scripts\python.exe -m PyInstaller AS1288_Calculator_V2.spec --noconfirm` completed successfully → `dist\AS1288_Calculator_V2.exe` (fresh timestamp, ~41 MB).

**Post-build HTTP verification, against the running EXE itself (not the dev server), launched from `dist\` and hit on `127.0.0.1:5000`:**
- Version footer renders `2.0 — expires 31 August 2026`, no "testing" wording.
- Both "Edge Support Configuration" labels present (Pathway 2 and Pathway 3).
- Pathway 2 calculation (1800×1350mm, 2-edge, Monolithic Toughened, ULS 2.0/SLS 0.8 kPa) → `PASS`, 10mm — sane result.
- Pathway 3 calculation (130° angle, 600×2200/2200mm, butt joint, safety glass) → `PASS`, governing bite 15mm, Table 5.3 human impact 6mm, wind 4mm — sane result.
- Degree symbol on-screen: `angle_deg: 130.0` confirmed correctly round-tripped through the served page/template pipeline (`<meta charset="UTF-8">`).
- Degree symbol in the TXT report (`/generate_report`): `Content-Type: text/plain; charset=utf-8` header confirmed; byte-level hex dump confirms `°` encoded as `c2 b0` (valid UTF-8, not mojibake) in both occurrences — `"Pathway 3 — Faceted Structural Silicone (90-160°)"` and `"Included Angle : 130.0°"`.
- EXE instance(s) terminated after verification.

**Live-browser click-test of the built EXE — completed by Sahil directly**, closing the one item this session's earlier entry left outstanding: double-clicked `AS1288_Calculator_V2.exe`, confirmed it auto-opens the browser, manually clicked through Pathway 2 and Pathway 3 forms, toggles, and the report download in a real browser session.

**This closes the 2.0 release-prep session.** Version bump, testing-wording removal, label consistency, degree-symbol fix, the new `run_tests.bat`/`run_tests.sh` regression runner, and the EXE rebuild are all now confirmed complete and live-verified — 2.0 is release-ready pending only the distribution step (pushing the new EXE to the OneDrive folder).

### v1.28 — 14 July 2026 — Hide Pathway 4 from the UI pending further development (Michael's feedback)

**Commit hash** `0ba8823`

**Paused, not removed.** Michael has reservations about Pathway 4's (Structural Glazing, Section 14.4) current scope and audience. This session hides it from the UI only — no backend/engine code touched, per the explicit instruction.

**Implementation:**
- `interfaces/flask_app/app.py`: new `PATHWAY_4_ENABLED = False` feature flag, added in the same config location as the existing `EXPIRY_DATE`/`APP_VERSION` constants (a new `# FEATURE FLAGS` section directly below them). `index()` now also passes `pathway_4_enabled=PATHWAY_4_ENABLED` into the template context, following the same pattern `app_version`/`expiry_date` already use.
- `interfaces/flask_app/templates/index.html`: the "Structural Glazing" landing tile (`#tile-pathway4`) is now wrapped in a server-side `{% if pathway_4_enabled %} ... {% endif %}` block. When the flag is `False`, the tile does not render into the HTML at all — confirmed via HTTP (`grep -c "tile-pathway4"` on the served page returns 0) — not merely hidden via CSS or greyed out. Tiles 1–3 confirmed still present and unaffected.
- `showPathway('pathway4')` was only ever invoked by the now-omitted tile's `onclick` — with the tile gone, the `#pathway4-view` form section, `p4State`, and all Pathway 4 JS remain in the page's source (untouched, per instruction) but are unreachable from any UI action, since nothing left in the DOM can trigger them.
- **Left completely untouched, per explicit instruction:** `/calculate_pathway4` (`app.py`), `engine/combined/pathway4.py`, `build_pathway4_report()`, `tests/test_pathway4.py`. The route stays live and fully functional — confirmed by the regression run below — just unreachable from the UI. Re-enabling Pathway 4 is a single flag flip (`PATHWAY_4_ENABLED = True`), no other code changes needed.

**Full eight-suite regression, all green, confirming Pathways 1–3 are unaffected and Pathway 4's backend is fully intact despite being hidden:**
```
test_runner:                 Total: 19  |  Matched: 19  |  Mismatched: 0
test_runner_2:                Total: 17  |  Matched: 17  |  Mismatched: 0
test_structural_consistency:  ALL STRUCTURAL CHECKS PASSED
test_silicone_bite:           17/17 tests passed
test_table_5_3:                11/11 tests passed
test_structural_glazing:       6/6 tests passed
test_pathway3:                 10/10 tests passed
test_pathway4:                 13/13 tests passed (unchanged - confirms the untouched backend still works)
```

**Verification — HTTP-level plus live-browser click-test, both complete.** A stale dev-server process from earlier in the session (bound to port 5000, predating this change) was found and killed (explicit user confirmation obtained first, same recurring gotcha noted at v1.26/v1.27), then a fresh dev server relaunched. HTTP confirmed `tile-pathway4` is absent from the served HTML (`grep -c` returns 0) and tiles 1-3 are present — supplementary evidence only, not a substitute for the click-test itself. No Chrome/browser tool was available in this Claude Code environment this session (confirmed via tool search) — same recurring gap as every UI-touching session since v1.25 — so the dev server was left running at `127.0.0.1:5000` for Sahil to click-test directly. **Live-browser click-test confirmed by Sahil from claude.ai:** landing page shows exactly 3 tiles (Pathway 4 tile and route confirmed absent from navigation, not just from the raw HTML grep); Pathway 3 calculated correctly end-to-end (10mm, Case A geometry — matches the known validated figure), confirming Pathways 1-3 are genuinely unaffected in the live DOM, not just in the HTTP response. This closes the live-verification gap the entry above originally flagged, same as the pattern at v1.25/v1.26/v1.27.

**EXE rebuild follows this same session, now that live verification is confirmed** — see below.

### v1.28 (continued) — 14 July 2026 — EXE rebuild carrying the v1.28 Pathway-4-hidden change into the distributed build

**This is a rebuild, not a new feature release.** No code changed this entry — it packages the v1.28 Pathway-4-hidden session (above) into the distributed `AS1288_Calculator_V2.exe`, the same interim-distribution EXE described at v1.26/v1.27.

**Pre-build checks:**
- Full eight-suite regression re-confirmed green immediately before building (same figures as above): `test_runner` (19/19), `test_runner_2` (17/17), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (11/11), `test_structural_glazing` (6/6), `test_pathway3` (10/10), `test_pathway4` (13/13).
- `AS1288_Calculator_V2.spec` and `duce_icon1.3.ico`/`data`/`templates`/`static` paths checked for drift — all confirmed unchanged, no edit needed.
- `PATHWAY_4_ENABLED = False` (`app.py`) confirmed still in place alongside `APP_VERSION`/`EXPIRY_DATE` before building.

**Build:** same `.venv` used at the prior v1.27 EXE rebuild (`pyinstaller-DUCEBDANB06.exe` not directly invocable by name, so run as `.venv\Scripts\python.exe -m PyInstaller AS1288_Calculator_V2.spec --noconfirm`, same as before). Build completed without errors; `dist/AS1288_Calculator_V2.exe` produced (~40MB, consistent with prior builds).

**EXE verification, HTTP-level — confirmed the built EXE itself shows only 3 tiles, not just the dev server:**
- Killed the dev server left running from the click-test step (explicit user confirmation obtained first) before launching the freshly built EXE, so port 5000 was genuinely serving the new EXE process.
- `grep -c "tile-pathway4"` on the EXE's own served HTML returns `0` — the Structural Glazing tile is absent from the built EXE's page source, not just the dev server's.
- Tiles 1-3 (`id="tile-pathway1/2/3"`) confirmed present in the EXE's served HTML.
- Version/expiry footer confirmed correct: `V2 — testing build expires 31 August 2026`.
- Pathway 3 sanity check against the running EXE (Case A geometry, same inputs as the live click-test): `bite_thickness_mm = 15`, matching the known validated figure — confirms Pathway 3 works end-to-end through the EXE, not just the dev server.
- **`/calculate_pathway4` confirmed still live and functional on the EXE's own backend** (`status: PASS` for a direct API call) — proving the route genuinely stays live but unreachable from the UI, exactly as intended, even in the packaged EXE.

**Not covered this session:** no live-browser click-through of the built EXE specifically (as opposed to the dev server, already live-verified above) — HTTP-level confirmation was judged sufficient here since the UI/JS is unchanged from what was already click-tested this same session, and this entry is a packaging step, not new UI surface.

**Hosting/Azure/SSO remains a separate, unresolved track**, unchanged from v1.26 — this EXE remains the interim distribution method.

### v1.27 (continued) — 14 July 2026 — EXE rebuild carrying the v1.27 usable-bite fix into the distributed build

**Commit hash** 03c6e43055ff0189654b758a34e19b2342c43355

**This is a rebuild, not a new feature release.** No code changed this entry — it packages the v1.27 usable-bite transparency session (below) into the distributed `AS1288_Calculator_V2.exe`, the same interim-distribution EXE described at v1.26.

**Pre-build checks, per the task's own instruction:**
- Full eight-suite regression re-confirmed green immediately before building: `test_runner` (19/19), `test_runner_2` (17/17), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (11/11), `test_structural_glazing` (6/6), `test_pathway3` (10/10), `test_pathway4` (13/13).
- `AS1288_Calculator_V2.spec` checked for drift before reuse — all four `datas` paths (`interfaces/flask_app/templates`, `interfaces/flask_app/static`, `data`, `duce_icon1.3.ico`) confirmed still present and correct, no changes made to the spec.
- `APP_VERSION`/`EXPIRY_DATE` (`app.py`) checked for drift — still `'V2'` / 31 August 2026, unchanged since v1.26's consolidated release. No edit needed.

**Build:** PyInstaller not present on the base interpreter's `PATH` this session — found and used the project's own `.venv` (which has `pyinstaller-DUCEBDANB06.exe` and the full dependency set, confirmed via `pip show`/import check), invoked as `.venv\Scripts\python.exe -m PyInstaller AS1288_Calculator_V2.spec --noconfirm`. Build completed without errors; `dist/AS1288_Calculator_V2.exe` produced (~40MB, consistent with the prior build's size).

**EXE verification, HTTP-level — another stale-process instance found and worked around, same recurring class noted at v1.26 and again earlier in the v1.27 usable-bite session itself:** a leftover Python process from earlier in this session was already bound to `127.0.0.1:5000` (confirmed via `netstat -ano` + `Get-Process`); killed after explicit user confirmation before launching the freshly-built EXE, so the verification below is confirmed against the actual new EXE process, not a stale one.
- Version/expiry footer confirmed correct in the served HTML: `V2 — testing build expires 31 August 2026`, matching `EXPIRY_DATE` exactly.
- **Confirmed this is genuinely the new build, not a cached/stale one:** `/calculate_pathway3` called directly against the running EXE (h=600mm, W1/W2=2200mm, angle=130°, mitred joint, ULS=1.0kPa/SLS=0.7kPa, Monolithic Toughened) returned `required_bite_raw_mm`, `required_bite_floored_mm`, `usable_bite_mm`, and `mitre_angle_deg` — the v1.27 usable-bite transparency fields — matching the dev-server figures from the usable-bite session exactly (`bite_thickness_mm=15`, `usable_bite_mm≈14.0`, `mitre_angle_deg=25.0`). An EXE built from stale code would have been missing these fields entirely, so this doubles as a genuine build-freshness check, not just a smoke test.

**Not covered this session:** no live-browser click-through of the built EXE specifically (as opposed to the dev server, already live-verified earlier in the v1.27 usable-bite entry below) — HTTP-level confirmation of the EXE was judged sufficient here since the UI/JS is unchanged from what was already click-tested against the dev server this same session, and this entry is a packaging step, not new UI surface.

**Hosting/Azure/SSO remains a separate, unresolved track**, unchanged from v1.26 — this EXE remains the interim distribution method.

### v1.27 — 14 July 2026 — Silicone-bite transparency display for Pathway 3/4 (display-only, no calculation change)

**No calculation logic changed this session.** This exposes intermediate values `find_min_nominal_for_usable_bite()` (`engine/shared/table_4_1.py`) already computed — the raw pre-floor required bite, the actual Table 4.1 thickness at the selected nominal, the deduction applied, and the resulting usable bite — which previously stopped at the final nominal thickness with no visible working on-screen or in the report.

**Verified before coding, per Section 0's standing discipline:**
- Pathway 3's `run_bite_calculation()` (`engine/silicone_bite/formulas.py`) already retained both `required_bite_raw_mm` (pre-6.0mm-floor) and `required_bite_mm` (post-floor, what fed the Table 4.1 lookup) — confirmed both survive into `make_silicone_result()`, but a genuine gap was found: when `apply_thickness_floor()` raised the final nominal above what `find_min_nominal_for_usable_bite()`'s own search returned, the function's `usable_bite_monolithic`/`usable_bite_laminated` values were stale — computed at the smaller pre-floor nominal the search had stopped at, not the floored nominal actually displayed. Fixed by recomputing usable bite (and Table 4.1 actual thickness) at the floored nominal whenever the floor changed it.
- Pathway 4's `wind_bite_mm`/`dead_load_bite_mm` (`pathway4.py`) were already the true raw required bite pre-lookup (no pre-lookup floor exists in this pathway, unlike Pathway 3 — confirmed against the module's own docstring) — the only floor point is the final NOMINAL thickness (`MIN_NOMINAL_THICKNESS`). To let the shared display wording detect "was a floor applied" via one consistent `required_bite_raw_mm != required_bite_floored_mm` comparison across both pathways, Pathway 4's `*_required_bite_floored_mm` field is set to the floored nominal's own usable bite when the floor actually raised it, otherwise identical to the raw figure — same signal, same wording, different underlying mechanics per pathway, correctly reconciled rather than glossed over.
- `TABLE_4_1_MONOLITHIC`/`TABLE_4_1_LAMINATED` (`engine/shared/table_4_1.py`) confirmed accessible and already imported by both orchestrators, per-broad-category as expected — consistent with the existing bite logic's own category-level (not subtype-level) treatment.

**New fields, added via the existing constructor-discipline functions (Section 6.4), every return path populated:**
- `make_silicone_result()` (`engine/shared/results.py`): `actual_thickness_monolithic`/`actual_thickness_laminated`, `deduction_mm`, `deduction_type` (`'chamfer'`, `CHAMFER_ALLOWANCE_MM`).
- `make_pathway3_result()`: `required_bite_raw_mm`, `required_bite_floored_mm`, `usable_bite_mm`, `actual_thickness_mm`, `deduction_mm`, `deduction_type`, `mitre_angle_deg` (only set for mitred joints) — read off `run_bite_calculation()`'s own `bite_result` dict rather than recomputed, per every return path that already carries `bite_thickness_mm` (`WIND_NO_COMPLIANT_THICKNESS`/`ERROR`, `HUMAN_IMPACT_NOT_PERMITTED`/`HUMAN_IMPACT_NO_COMPLIANT_THICKNESS`, `PASS`/`HUMAN_IMPACT_INELIGIBLE`).
- `make_pathway4_result()`: `dead_load_required_bite_raw_mm`/`dead_load_required_bite_floored_mm`, `wind_required_bite_raw_mm`/`wind_required_bite_floored_mm` (independent per criterion, since dead-load and wind bite are independently looked up — Section 7.6), `dead_load_usable_bite_mm`/`wind_usable_bite_mm`, `dead_load_actual_thickness_mm`/`wind_actual_thickness_mm`, `deduction_mm`/`deduction_type` (`'edge_polish'`, `EDGE_POLISH_DEDUCTION_MM`, shared across both criteria since the same deduction applies to both).

**Display wiring, both TXT report (`app.py`) and on-screen result cards (`index.html`) — one shared wording rule in each layer** (`build_usable_bite_line()` in `app.py`, `buildUsableBiteLine()` in `index.html`, kept in sync manually like the existing `P4_CRITERION_LABELS` precedent since one is Python and one is JS):
- Butt joint: *"Usable bite: 9.7mm (11.7mm actual thickness − 2mm chamfer deduction, butt joint) — meets the required 7.8mm bite."*
- Mitred joint: *"Usable bite: 14.0mm (14.5mm actual thickness ÷ cos(25°) − 2mm chamfer deduction, mitred joint) — meets the required 12.4mm bite."*
- Pathway 4 (edge polish, no mitre concept): *"Usable bite: 9.7mm (11.7mm actual thickness − 2mm edge polish deduction) — meets the required 8.5mm."*
- Floor-triggered (either pathway's floor point, same wording either way — **confirmed this session that both are the same underlying Dow Corning 6mm minimum-seal-thickness rule enforced at two different points in each pathway's own chain, not two separate justifications**, so both are prefixed identically): *"Required bite calculated at 0.7mm, floored to Dow Corning's 6.0mm minimum glueline/bite requirement. Usable bite: 7.7mm (9.7mm actual thickness − 2mm chamfer deduction, butt joint) — meets the required 6.0mm bite."*
- Headline bite figures also now show the raw required bite in parentheses, e.g. *"Silicone Bite (Dead Load) Minimum Nominal Thickness = 12 mm (8.5mm required)"*.

**Full eight-suite regression, all green:** `test_runner` (19/19), `test_runner_2` (17/17), `test_structural_consistency` (pass), `test_silicone_bite` (17/17, unchanged pass count — the stale-usable-bite-at-floor fix inside `run_bite_calculation()` didn't change any existing test's expected figures, confirmed by direct re-run), `test_table_5_3` (11/11), `test_structural_glazing` (6/6, untouched), `test_pathway3` (**10/10, up from 7/7** — three new tests: butt/no-floor, mitred, floor-triggered), `test_pathway4` (**13/13, up from 11/11** — two new tests: Case A/no-floor covering both criteria independently, floor-triggered covering both criteria independently).

**Verification, this session — a genuine stale-process gotcha found again, same recurring class as v1.26's own note:** launching the Flask dev server for HTTP verification found two stale processes already bound to `127.0.0.1:5000` from an earlier, unlogged session, shadowing the freshly-launched one (confirmed via `netstat -ano` showing two `LISTENING` entries) — the first round of `curl` checks silently hit the stale process and returned pre-session JSON with none of the new fields. Killed both (explicit user confirmation obtained first) and relaunched cleanly (single `LISTENING` entry confirmed) before re-verifying. **HTTP-level, confirmed against the fresh process:** Pathway 3 butt joint, Pathway 3 mitred joint, Pathway 3 floor-triggered case (h=500mm/w=500/500mm/angle=90/ULS=0.6kPa), and Pathway 4 Case A (edge-polish, both dead-load and wind criteria) — all four match the direct-Python-call figures exactly, both in the `/calculate_pathway3`/`/calculate_pathway4` JSON response and in the `/generate_report` downloaded TXT for Pathway 3 and Pathway 4.

**Live-browser click-through completed by Sahil directly, closing the gap this entry initially flagged** (no Chrome/browser tool was available to Claude Code in this environment, confirmed via tool search — same recurring gap noted at v1.25/v1.26, closed the same way those were: by Sahil running the check directly). Result card accordions opened for a butt case, a mitred case (Pathway 3), and a Pathway 4 edge-polish case, confirming the new usable-bite sentence renders correctly under each bite line in the actual browser DOM, not just in the HTTP/JSON responses above.

**Scope, explicitly confirmed unchanged:** no calculation logic touched in `run_bite_calculation()`, `run_pathway3_calculation()`, `run_pathway4_calculation()`, `run_structural_glazing_calculation()`, or `check_glass_type()` — every new field is either read directly off an already-computed value or (the one genuine fix, the stale-usable-bite-at-floor case) recomputed using the exact same formula (`usable_bite()`) the engine already uses elsewhere, just at the correct (floored) nominal instead of the search's own pre-floor nominal.

### v1.26 (continued) — 13 July 2026 — Consolidated V2 EXE release: v1.17 EXE bugs + Section 10 item 9 cleanup backlog, built and HTTP-verified

**Committed `8276eec`.** This is a same-version follow-up to the Pathway 4 gap fix entry below (no functional/engine changes — release packaging, one bug fix, and cleanup-backlog items only), so it's recorded under v1.26 rather than incrementing to a new version number.

**Bug fixes (previously queued as v1.17):**
1. **`launcher.py`'s expiry message no longer hardcodes a second date string.** It previously printed `'This testing version has expired (31 July 2026).'` as a literal, independent of the actual `EXPIRY_DATE` constant — the two could silently drift. Now `f'This testing version has expired ({EXPIRY_DATE.strftime("%d %B %Y")}).'`, always derived from the one constant.
2. **`EXPIRY_DATE` set to 31 August 2026** (previously 31 July 2026).
3. **`EXPIRY_DATE` relocated to `app.py`, `launcher.py` now imports it from there** (`from app import app, EXPIRY_DATE`) — the reverse of the previous direction, required because `launcher.py` already does `from app import app`, so `app.py` importing from `launcher.py` would be circular. This also makes `app.py` the single source of truth the new in-app footer (item 6 below) reads from, rather than inventing a third copy.
4. **Six broken `.spec` files deleted, confirmed recoverable from git history first** (`git log --oneline --diff-filter=A -- "*.spec"`) before deletion: `AS1288_Calculator.spec`, `AS1288_Calculator_v0.1.spec`, `AS1288_Calculator_v0.2.spec`, `AS1288_Calculator_v1.spec`, `AS1288_Calculator_v2.spec` (all five referenced `src\launcher.py`/`src/templates`/`src/static`/`src\duce_icon1.ico` — the `src/` folder no longer exists post-refactor), and `AS1288_Calculator_v3.spec` (referenced `duce_icon1.ico` at the repo root, which does not exist — only `duce_icon1.3.ico` does). **`AS1288_Calculator_v1.3.spec` renamed to `AS1288_Calculator_V2.spec`** (`name=` field inside updated to match) — it already pointed at the correct post-refactor paths (`interfaces\flask_app\launcher.py`, `interfaces/flask_app/templates`, `interfaces/flask_app/static`, `duce_icon1.3.ico`) and is now the sole surviving spec, representing the consolidated V2 release.

**Cleanup backlog (Section 10 item 9):**

5. **Table 5.3 `fail_reason` naming collision resolved.** `engine/wind_load/checks/wind.py`'s `check_pane_compliance()` next-compliant-thickness search (the in-loop candidate scan) set `candidate_trace['fail_reason'] = 'TABLE_5_3_NOT_PERMITTED'` for the unsolvable-row-rejection case — the exact same string as the pre-loop hard-gate `status` value returned at two other points in the same file (`make_mode1_result(status='TABLE_5_3_NOT_PERMITTED', ...)`, `make_mode2_result(status='TABLE_5_3_NOT_PERMITTED', ...)`). No runtime ambiguity existed (the two conditions can't co-occur — the in-loop value is a `fail_reason` string interpolated into a report line, the other is a `status` field compared elsewhere), but the shared literal was a latent readability/refactor risk. Renamed the in-loop value to `'TABLE_5_3_GATE_FAIL'`. **Verified before renaming**, per the task's own instruction: `app.py:798` (`interfaces/flask_app/app.py`) reads `fail_reason` opaquely via `candidate.get('fail_reason', 'unknown check')` and only ever interpolates it into a message string — no equality comparison against the literal anywhere in `app.py` or `index.html` (confirmed via grep — zero references to `fail_reason` in the frontend). No frontend changes needed, confirming the task's premise.
6. **New regression test for the Table 5.3-driven `NO_COMPLIANT_THICKNESS` path** (`tests/test_table_5_3.py`, new `test_11`) — flagged as untested since v1.13, previously only verified via a temporary, reverted stock-list override that was never committed. **Confirmed by exhaustive search first, not assumed:** with today's real `GLASS_TYPE_THICKNESSES` stock data, no eligible glass type's Table 5.3 row-band minimum thickness ever exceeds its own stocked maximum, across every height band, width, and butt-joint combination tested computationally — this specific path is genuinely unreachable with real data today, the same class of finding as the already-documented Table 5.1 NON_COMPLIANT-unreachable case (v1.22) and the Table 5.3 2-edge/3-edge finding. `check_glass_type()`'s `thickness_list` is read from the module-level `GLASS_TYPE_THICKNESSES` global inside `engine/wind_load/checks/wind.py` (not accepted as a parameter), so the only honest way to exercise the path without fabricating fake CSV rows is a scoped monkeypatch. `test_11` temporarily sets `wind_mod.GLASS_TYPE_THICKNESSES[('Monolithic', 'Toughened')] = [4, 5, 6, 8, 10, 12]` (capping stock at 12mm) for one `run_calculation()` call at a geometry (3500mm × 2000mm, 2-edge, unrestricted-width row → Table 5.3's 3.2–3.6m band requires 19mm) chosen so ULS/SLS both pass at thin thicknesses (4mm/8mm, confirmed via direct call) well under the patched cap, isolating the failure to Table 5.3 exhausting the whole patched list with no PASS. Restored via `try`/`finally`, with a dedicated check confirming `GLASS_TYPE_THICKNESSES` is back to its original value after the test runs, so no other test in the suite (run in the same process) can observe the patched state. `test_table_5_3.py` is now 11/11 (up from 10/10).
7. **In-app version/expiry indicator added.** New `.version-footer` bar directly under the app header on every page (`interfaces/flask_app/templates/index.html`, styled in `static/style.css`), reading `{{ app_version }} — testing build expires {{ expiry_date }}`. Both values are passed from `app.py`'s `index()` route (`app_version=APP_VERSION`, `expiry_date=EXPIRY_DATE.strftime('%d %B %Y')`) — `APP_VERSION = 'V2'` and `EXPIRY_DATE` are both defined once in `app.py` (see item 3 above), so this is not a third hardcoded copy of the date.
8. **Stray `favicon.ico` 404 fixed.** No favicon file existed in `static/` and no `<link rel="icon">` tag existed in `index.html`'s `<head>`, so browsers auto-requested `/favicon.ico` and got a 404 on every page load. `duce_icon1.3.ico` (already used by the EXE's own taskbar icon, confirmed a valid 256×256 `.ico`) copied to `interfaces/flask_app/static/favicon.ico`; `<link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}">` added to `<head>`.

**Full eight-suite regression, all green before building:** `test_runner` (19/19), `test_runner_2` (17/17), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (**11/11, up from 10/10** — new test_11), `test_structural_glazing` (6/6), `test_pathway3` (7/7), `test_pathway4` (11/11, unchanged from v1.26's rewrite).

**EXE build:** `AS1288_Calculator_V2.spec` built via PyInstaller from the current codebase (all four pathways, engine + UI + report generation). Build completed without errors; `dist/AS1288_Calculator_V2.exe` produced (~40MB).

**EXE verification, HTTP-level (this chat) — a genuine stale-process gotcha found and worked around, same class as v1.26's own noted "confirm which process actually answers the port" lesson:** launching the built EXE for verification found a second, unrelated Python process from an earlier, unlogged session already bound to port 5000 and racing with the freshly-launched EXE for incoming requests — confirmed via `netstat -ano` showing two `LISTENING` entries on `127.0.0.1:5000`. Stopped after explicit user confirmation (a process kill via a broad name-pattern match is outside this session's standing authorization on its own), then re-verified cleanly against the single remaining EXE process:
- Version/expiry footer confirmed correct in the served HTML: `V2 — testing build expires 31 August 2026`, matching `EXPIRY_DATE` exactly (not just visually inspected — the string was parsed out of the response and compared against the constant's own `.strftime()` output).
- Favicon confirmed serving (`GET /static/favicon.ico` → 200) with the correct `<link rel="icon">` tag present in the page head.
- **All four pathways confirmed via direct HTTP calls against the running EXE**, each matching a known-good figure from the existing test suites exactly: Pathway 1 Mode 1 (TC-A geometry, height=600mm/width=3600mm/ULS=1.5kPa/SLS=0.6kPa, Monolithic Annealed) → `PASS`, 4mm; Pathway 2 Mode 2 (height=1500mm/width=1200mm, Monolithic Toughened 4mm actual, safety glass ON) → `PASS`; Pathway 3 (height=1219mm/width=2438mm/90°/butt joint/ULS=2.0kPa/SLS=0.8kPa) → `PASS`, 15mm/16mm for Monolithic Toughened/Laminated Annealed, matching the existing v1.15-era figures; Pathway 4 (same Case A geometry as `test_pathway4.py`'s test_4) → `PASS`, 12mm, `governing_criterion='dead_load_bite'` for both subtypes checked, matching test_4 exactly.
- **Report generation confirmed for Pathway 1**: `/calculate` called first to obtain real results, then `/generate_report` called with those results attached (mirroring what the browser's own JS does) — HTTP 200, real report content returned including the correct AR/span/panel-area figures and a populated `RESULTS — MINIMUM THICKNESS` section for the calculated subtype.

**NOT covered this session — a genuine, acknowledged gap, not a skipped step, same standing discipline as every prior UI-touching session (v1.25's entry is the clearest precedent):** no Chrome/browser tool was available in this Claude Code environment this session (confirmed via tool search) — the same recurring gap noted at v1.25 and only closed for v1.26 by Sahil running the check directly from claude.ai. **HTTP-level verification, however thorough, is explicitly not treated as a substitute for a live click-through** — the button clicks, toggle-driven checkbox refreshes, accordion expand/collapse, and copy-as-image clipboard behaviour for this specific release build remain unconfirmed. Per the task's own instruction, this is reported honestly rather than claimed complete: **a live click-through of the built EXE (not the dev server) — at minimum one calculation per pathway through to a result, plus a report download for at least one pathway, using Sahil's own Chrome/claude.ai access as v1.26 did — is the recommended next step before this release is treated as fully verified.**

**Hosting/Azure/SSO remains a separate, unresolved track.** This EXE (`AS1288_Calculator_V2.exe`) is the interim distribution method while that track is unstarted.

### v1.26 — 13 July 2026 — Pathway 4 gap fix: missing Mode 1 wind-load check on the glass pane, single-Pz form replaced with full ULS/SLS/N-C input

**Committed `bb433af`.**

**This session corrects a genuine gap in Pathway 4's engine, found and confirmed as a real engineering requirement, not an optional enhancement.** v1.24's changelog entry declared "Pathway 4 ENGINE WORK IS NOW COMPLETE" — that declaration was premature. Section 14.4 (Branch 4: Flat Structural Glazing) has always specified, in its own text since first written: *"Wind load: 4-edge supported, Section 4 — conditional on all edges having adequate structural silicone bite"* and *"Governing thickness: max(governing bite, wind bending as 4-edge[, human impact result if toggle ON])"*. The "wind bending as 4-edge" check — a AS 1288 Clause 4.4.3 Mode 1 ULS/SLS check on the glass pane's own bending capacity, completely independent of whether the silicone joint is adequately sized — was never wired into `engine/combined/pathway4.py`. Pathway 3 already runs both the joint and the pane checks together (Section 12.13 step 3, `check_glass_type()` after bite); Pathway 4 never got the equivalent step, and no prior session's engine-completeness claim caught the gap because no one checked Section 14.4's own text against what the orchestrator actually computed.

**Gap 2, found alongside Gap 1: the form's single Pz field was structurally insufficient once ULS/SLS became a real criterion.** `run_structural_glazing_calculation()`'s Appendix F bite formula only ever needed one pressure value (labelled Pz in Section 14.4, same physical quantity as ULS — just different notation for that formula specifically). But `check_glass_type()`'s Mode 1 ULS/SLS check genuinely needs both pressures independently. Fixing Gap 1 without fixing Gap 2 would have left no way to supply SLS at all.

**Five independent governing criteria, per Section 7.6's independence principle (each searches its own full range independently, never starting from another criterion's result):**
1. **Silicone bite (dead load)** — `dead_load_bite_mm` from `run_structural_glazing_calculation()` → independent Table 4.1 lookup via `find_min_nominal_for_usable_bite()` (`EDGE_POLISH_DEDUCTION_MM`, `MIN_NOMINAL_THICKNESS` floor) → `dead_load_bite_nominal_mm`. Per broad category (Monolithic/Laminated), not per subtype — the bite/dead-load engine has no subtype concept.
2. **Silicone bite (wind load)** — same lookup mechanism, against the raw `wind_bite_mm` figure → `wind_bite_nominal_mm`. Also per broad category.
3. **ULS** — `check_glass_type(support_condition='4-edge', safety_glass_required=False)` per subtype → `uls_thickness_mm`. Genuinely per subtype (c1 factor differs by `glass_type`/`glass_subtype`).
4. **SLS** — same `check_glass_type()` call, separate output → `sls_thickness_mm`. Per subtype.
5. **Table 5.1** — unchanged from v1.22, gated on the safety-glass toggle, per subtype → `table_5_1_thickness_mm`.

`governing_thickness_mm = max()` across whichever of the above are active; a new `governing_criterion` field (`'dead_load_bite'` / `'wind_bite'` / `'uls'` / `'sls'` / `'table_5_1'`) names which one produced that max, per subtype.

**Verified directly against source before writing any code, per Section 0's standing discipline:**
- `find_min_nominal_for_usable_bite(required_bite_mm, thickness_table, joint_type, mitre_angle_deg=None, chamfer_mm=CHAMFER_ALLOWANCE_MM)` (`engine/shared/table_4_1.py`) — confirmed exact signature and confirmed `run_structural_glazing_calculation()`'s own call pattern (`joint_type=None, chamfer_mm=EDGE_POLISH_DEDUCTION_MM`) before replicating it, twice per broad category, in `pathway4.py`.
- `check_glass_type(df, glass_type, glass_subtype, height_mm, width_mm, support_condition, span_dimension, wind_pressure_uls, wind_pressure_sls, glazing_config, safety_glass_required=False, bushfire_required=False, ...)` (`engine/wind_load/checks/wind.py`) — confirmed exact signature and confirmed `pathway3.py`'s own call pattern (`support_condition='4-edge'`, `safety_glass_required=False` — Table 5.1 computed independently to avoid double-firing the safety-glass gate inside `check_glass_type()` itself, same reasoning `pathway3.py`'s own module docstring gives) before mirroring it exactly. Also confirmed `calculate_span()`'s own logic: under `support_condition='4-edge'`, `span_dimension` is a don't-care — span is always `min(height_mm, width_mm)`, same convention the bite formula already used, so `span_dimension='height'` is passed purely for consistency with `pathway3.py`'s call, never actually read.

**`run_structural_glazing_calculation()` is UNCHANGED — not touched by this session, per the explicit instruction that it's a validated engine function.** The two bite Table 4.1 lookups are done in `pathway4.py` itself, not inside that engine function, which continues to return only the raw `wind_bite_mm`/`dead_load_bite_mm` figures (and its own now-unused `nominal_monolithic`/`nominal_laminated`, pre-collapsed via `max()` — no longer read by the orchestrator, which does its own two independent lookups instead).

**Signature changes:** `run_pathway4_calculation()` replaces the single `pz_kpa` parameter with `wind_pressure_uls_kpa`/`wind_pressure_sls_kpa`, and gains `csv_path`/`preloaded_df` (needed by `check_glass_type()`, following the same preloaded-takes-precedence pattern as `run_pathway3_calculation()`). `make_pathway4_result()` replaces `bite_thickness_mm` with `dead_load_bite_nominal_mm`/`wind_bite_nominal_mm`, adds `uls_thickness_mm`/`sls_thickness_mm`/`governing_criterion`/`wind_trace`, keeps `table_5_1_thickness_mm` — every return path (`BITE_NO_COMPLIANT_THICKNESS`, `WIND_NO_COMPLIANT_THICKNESS` (new status), `HUMAN_IMPACT_INELIGIBLE`, `HUMAN_IMPACT_NO_COMPLIANT_THICKNESS`, `PASS`) populates the full field set per Section 6.4's constructor discipline.

**ENGINEERING FINDING, recorded honestly, not worked around:** an extensive parameter search (~45 geometry/pressure combinations, both glass categories, square and elongated panels, wide pressure ranges — see `pathway4.py`'s own module docstring and `test_pathway4.py`'s for the full record) found no realistic `full_perimeter` geometry where ULS or SLS governs the OVERALL result. Both wind bite and dead-load bite scale roughly linearly with panel size for a square panel, while ULS/SLS thickness demand grows much more slowly (capped by the AR=5 table row, Section 7.2) — bite structurally dominates across realistic ranges for this pathway's coupled geometry (bite's span and ULS/SLS's span are the same governing dimension under 4-edge support). **SLS CAN and does exceed ULS as a sub-criterion** — confirmed and hand-calculated (h=1000mm, w=5000mm, ULS=1.0kPa, SLS=0.98kPa, Laminated Annealed → `uls_thickness_mm=5`, `sls_thickness_mm=6`) — even though dead-load bite (12mm) still governs overall in that same case. This is the same class of finding as the v1.15 Table 5.3 2-edge/3-edge discovery and the v1.22 "Table 5.1 NON_COMPLIANT unreachable" finding — a real property of the standard's data/geometry for this branch, not a defect. **Per explicit user instruction, no unrealistic geometry was fabricated to force a different result.** Instead: `test_pathway4.py`'s test_8 uses the real SLS>ULS sub-criterion case (hand-calculated in full, arithmetic shown in comments), and test_9 is a clearly-labelled LOGIC-PATH test verifying the `max(criteria, key=lambda k: criteria[k])` selection rule directly against synthetic per-criterion inputs for all five possible winners — not a claimed physical scenario.

**`tests/test_pathway4.py` rewritten from scratch — every existing test case's expected values recomputed against real function calls, none assumed unchanged, per instruction.** 11 tests, 127 individual assertion checks (up from 7 tests/89 checks): scenario scope gate (tests 1–3, unchanged behaviour), Case A/C geometry toggle OFF (tests 4–5, dead-load bite governs, all five criteria populated and verified — full hand-arithmetic shown in test_4's comments), Case D geometry toggle OFF (test 6, wind bite governs — matches the pre-existing v1.19/v1.20 figures exactly, confirming the five-criteria model reproduces the old two-criteria model's governing figure where they should agree), Case D toggle ON (test 7, `HUMAN_IMPACT_INELIGIBLE` fallthrough alongside an eligible subtype's real Table 5.1 search), SLS-exceeds-ULS sub-criterion (test 8, hand-calculated, real geometry), governing-criterion selection logic (test 9, synthetic/logic-path, all five winners), Table 5.1 governs overall (test 10, hand-verified real geometry — h=0.35m/w=15.0m/ULS=0.15kPa/SLS=0.1kPa/Laminated Annealed, genuine FAIL-FAIL-FAIL-PASS trace), `BITE_NO_COMPLIANT_THICKNESS` under the new two-independent-lookup structure (test 11).

**Form rebuilt: single Pz field replaced with the same ULS/SLS/N-C-rating input section Pathway 3 uses**, copied field-for-field (`#p4-wind-pressure`/`#p4-wind-nc` toggle, `#p4-pressure-inputs`/`#p4-nc-inputs`, `p4_uls_kpa`/`p4_sls_kpa`/`p4_nc_rating`/`p4-loc-general`/`p4-loc-corner`) — `setP4WindMethod()`/`setP4Location()` added to `p4State`, same shape as `p3State`. `/calculate_pathway4` (`app.py`) now dispatches on `wind_method` exactly like `/calculate_pathway3` (direct kPa or `get_pressures_from_nc_rating()` lookup against the shared `NC_DF`), passing both resolved pressures into the engine and `CSV_PATH` for `check_glass_type()`'s dataframe.

**Result cards now show all five criteria** (Silicone bite dead load / wind load, ULS wind load, SLS wind load, Table 5.1 if toggle ON) **plus a "Governing criterion" row** naming which one produced the final figure (human-readable via a shared `P4_CRITERION_LABELS` map, same object literal in both `app.py`'s report builder and `index.html`'s JS — kept in sync manually, not shared code, since one is Python and one is JS). Copy-as-image snapshot rows extended to match. `build_pathway4_report()` rewritten: full wind-bite/dead-load arithmetic (unchanged from before), full ULS/SLS k-value trace per subtype (reusing `format_trace_entry()`'s existing `'ULS'`/`'SLS'` branches — no changes needed there, since `check_glass_type()`'s trace shape already matches Mode 1/Pathway 3's), Table 5.1 trace (unchanged), and a "Governing criterion: [name]" line per subtype before the final governing-thickness line.

**Full eight-suite regression, all green:** `test_runner` (19/19), `test_runner_2` (17/17), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (6/6, untouched — `run_structural_glazing_calculation()` itself unchanged), `test_pathway3` (7/7, untouched), `test_pathway4` (**11/11, 127 checks, up from 7/7 89 checks**).

**Two rounds of verification this session: HTTP-level (by this chat) and live-browser (by Sahil directly, closing the three-session gap).**

**HTTP-level, by this chat, before handoff:** Ran the Flask dev server and verified via raw HTTP: (1) new ULS/SLS/N-C form markup confirmed present in the served HTML after killing several stale server processes left over from prior sessions that were shadowing the fresh one on port 5000 (a real environment gotcha worth noting for future sessions — always confirm which process actually answers the port before trusting a "confirmed present" result); (2) toggle OFF, Case D geometry — governing 15mm/16mm with `governing_criterion='wind_bite'`, matching `test_pathway4.py`'s test_6 exactly, full real ULS/SLS trace present in the JSON; (3) toggle ON — Monolithic Annealed correctly returns `HUMAN_IMPACT_INELIGIBLE` without crashing when reached directly via the API, Monolithic Toughened's Table 5.1 search shows a genuine FAIL-then-PASS trace; (4) `/generate_report` downloaded and inspected directly — full ULS/SLS k-value arithmetic and Table 5.1 trace both render correctly per subtype, "Governing criterion" line present and correctly labelled; (5) N/C rating mode (`N3`/`General`) correctly resolves to `uls_kpa=1.4`/`sls_kpa=0.6` and produces a valid result.

**Live-browser, by Sahil directly (Claude in Chrome, driven from claude.ai) — the DOM-rendered checks HTTP-level testing structurally cannot perform, closing the gap open since v1.25:**
- **Toggle OFF** (h=1219mm, w=2438mm, ULS=2.0kPa, SLS=0.8kPa): form renders the ULS/SLS/N-C section correctly, matching Pathway 3's structure. All five criteria rendered on the result card — dead-load bite 12mm, wind bite 10mm, ULS 4–6mm, SLS 5mm, governing = dead-load bite 12mm — matching the known Case A figures and confirming the "bite dominates" engineering finding (ULS/SLS sit well under bite for this geometry) holds in the live UI, not just in HTTP responses.
- **Toggle ON:** checkbox list correctly filters to eligible subtypes only (Monolithic Toughened, Laminated Annealed/Heat-strengthened/Toughened) — same Section 6.2 eligibility-filtering pattern already established for Pathway 1/2/3, confirmed carried over correctly to Pathway 4. Section 14.7 disclaimer text present verbatim, both inline and in the result footer. The sixth line (Table 5.1: 5mm) appears correctly alongside the other five; governing still correctly resolves to dead-load bite.
- **Report generation:** confirmed via the actual Calculate/Generate Report button clicks against real form state — `POST /generate_report` returned 200.
- **Reachability finding, not a bug:** `HUMAN_IMPACT_INELIGIBLE` was not exercised this pass — the checkbox filtering hides ineligible subtypes (Monolithic Annealed/Heat-strengthened) before submission is even possible, so that status is **not reachable through this UI at all**, same pre-existing behaviour Pathway 1/3 already have. Confirmed by reading `getP4GlassTypes()`/`buildP4GlassTypeCheckboxes()` directly (`index.html`) and cross-checked against `getP3GlassTypes()` — identical filtering logic in both pathways. The status remains correct to keep in `make_pathway4_result()` (API/report-layer callers, and `test_pathway4.py`'s direct engine calls, can still reach it — see test_7/test_9's HTTP-level confirmation above) but it is dead code from the checkbox UI's own perspective specifically. Not a regression, not new to this session — inherited from the same pattern Pathway 3 has always used.
- **Not covered by this pass:** copy-as-image (clipboard PNG) was not explicitly re-confirmed this session for Pathway 4's new five-criteria rows, though the underlying `copySnapshotAsImage()`/`buildSnapshotHTML()` functions are unchanged, reused directly from Pathway 3.

**This closes the three-consecutive-session Chrome-tool gap** (v1.25, the unlogged duplicate-call-fix session, and v1.26 itself) — verification was completed by Sahil directly rather than via Claude Code's own (unavailable) Chrome access, following the standing recommendation to run this step from claude.ai.

**No changes to `run_structural_glazing_calculation()`, `check_glass_type()`, `get_safety_glass_max_area()`, or any other validated engine function** — this session's work is entirely inside `pathway4.py`'s orchestration layer, `make_pathway4_result()`'s field set, and the UI/report presentation layer that consumes them.

**This session also folds in, without a separate changelog entry, the prior (unlogged) session's fix** of a self-introduced duplicate-call risk in `/calculate_pathway4` (a second `run_structural_glazing_calculation()` call existed purely to expose the wind/dead-load breakdown for the report — confirmed harmless via a 200-case randomized diff, then eliminated by having `pathway4.py`'s single internal call populate `wind_bite_mm`/`dead_load_bite_mm` directly). That fix's `wind_bite_mm`/`dead_load_bite_mm` fields are retained and still used exactly as that session left them (read from the first result entry for the report's top-of-file breakdown, since they're identical across every subtype for a given request).

### v1.25 — 13 July 2026 — Pathway 4 UI built: form, route, report generation, copy-as-image, mirroring Pathway 3's structure

### v1.25 — 13 July 2026 — Pathway 4 UI built: form, route, report generation, copy-as-image, mirroring Pathway 3's structure

**This builds Pathway 4's UI (Section 14.4), closing the last gap in the four-pathway model.** Pathway 4's engine (`engine/structural_glazing/`, `engine/combined/pathway4.py`) was already complete and committed as of v1.24 (`9baad81`) — this session is UI-only, no engine/orchestrator code touched, per the same discipline v1.15 (Pathway 3's UI) and v1.18 (Pathway 4's orchestrator) both followed.

**Three deliberate form-design decisions confirmed this session, now resolved (previously open items — Section 12.12 item 4 discussion, Section 0's handoff prompt implicitly deferred these):**
1. **No scenario selector in the UI.** `SUPPORTED_SCENARIOS_V1 = ('full_perimeter',)` is the only supported value (Section 12.12 item 8, v1.18) — the Flask route hardcodes `scenario='full_perimeter'` server-side rather than exposing a dropdown/toggle with exactly one real option. Unlike Pathway 3, which genuinely branches behaviour on user input (angle, joint type), there is nothing here for the user to choose.
2. **No angle input, no 2-edge/3-edge selector, no BAL/bushfire fields.** `full_perimeter` always uses Table 5.1 for human impact (fixed, v1.21/v1.22 — no angle concept exists in this pathway, unlike Pathway 3 where angle decides which table applies) and is bushfire-excluded outright for every scenario including `full_perimeter` (Section 14.4, Section 14.5 rule 1). These fields exist in Pathway 3's form because its angle genuinely branches the calculation; Pathway 4 has no equivalent branch, so copying those fields would have been UI clutter implying a decision the engine never makes.
3. **Dead load has no on/off toggle.** `run_structural_glazing_calculation()`'s `governing_bite_mm = max(wind_bite_mm, dead_load_bite_mm)` runs unconditionally regardless of user input (`engine/structural_glazing/formulas.py:104`) — this is not user-discretionary the way the safety-glass toggle is (Section 14.7's toggle only gates a human-impact table nobody is required to declare; dead load is physics, not a declaration). The dead-load breakdown is always computed and always shown — as a result-panel row is out of scope for the on-screen card (Section 6.5's established convention keeps full trace detail report-only), but the full wind-bite/dead-load breakdown (`wind_span_m`, `dead_load_perimeter_m`, `wind_bite_mm`, `dead_load_bite_mm`, `governing_bite_mm`) appears unconditionally in the TXT report.

**Verified directly against source before writing any UI code, per Section 0's standing discipline (not from this document's paraphrase):**
- `make_pathway4_result()` (`engine/shared/results.py:197`) — confirmed exact field names: `subtype`, `glass_type`, `glass_subtype`, `status`, `message`, `governing_thickness_mm`, `bite_thickness_mm`, `table_5_1_thickness_mm`, `panel_area_m2`, `safety_glass_required`, `bite_trace`, `table_5_1_trace`.
- `run_pathway4_calculation()` (`engine/combined/pathway4.py:99`) — confirmed signature: `height_m`, `width_m`, `glass_thickness_nominal_mm`, `pz_kpa`, `scenario`, `safety_glass_required=False` (all in metres for height/width, not mm — the route converts from the form's mm inputs).
- **Found and worked around a genuine gap:** `bite_trace` on `make_pathway4_result()`'s success (`PASS`) path is `[]` — it is only ever populated (with a minimal one-entry FAIL summary) on the `BITE_NO_COMPLIANT_THICKNESS` short-circuit path. There is no wind-bite/dead-load breakdown available from `run_pathway4_calculation()`'s own return shape on success. Rather than touch `pathway4.py` (out of scope, per the task's explicit engine-is-done boundary), the new `/calculate_pathway4` route calls `run_structural_glazing_calculation()` a second time directly, with the same height/width/pressure inputs already passed to the orchestrator, purely to read its `wind_span_m`/`dead_load_perimeter_m`/`wind_bite_mm`/`dead_load_bite_mm`/`governing_bite_mm` fields for the report. This is not a second independent calculation path — same inputs, same deterministic function, guaranteed identical figures to what the orchestrator computed internally — just exposing fields the orchestrator's own result shape doesn't surface.

**Built:**
- **`engine/combined/__init__.py`:** now also exports `run_pathway4_calculation` (previously only `run_pathway3_calculation` was exported) — `app.py` imports both.
- **`interfaces/flask_app/app.py`:** new `/calculate_pathway4` route (mirrors `/calculate_pathway3`'s structure — filters the six-subtype dict down to the user's checked selection, since the orchestrator itself has no subtype-restriction parameter), new `build_pathway4_report()` (mirrors `build_pathway3_report()`, reuses `format_trace_entry()`'s existing `'SG'` branch for Table 5.1 trace rendering — no changes needed there, since `_run_table_5_1_search()`'s trace shape in `pathway4.py` already matches Pathway 3's), `/generate_report`'s dispatcher extended with a `pathway4` branch alongside the existing `pathway3`/default cases.
- **`interfaces/flask_app/templates/index.html`:** new `#pathway4-view` (height/width/Pz/safety-glass-toggle/subtype-checkboxes form, one result card per selected subtype, Generate Report button, copy-as-image), `p4State` (deliberately smaller than `p3State`/`p2State` — no scenario/angle/edge-condition/BAL fields, per the three decisions above), `buildP4GlassTypeCheckboxes()` (same six subtypes and same `SAFETY_GLASS_INELIGIBLE` eligibility list as Table 5.1 elsewhere, reusing `P3_SUBTYPES`/`P3_SG_INELIGIBLE` directly rather than duplicating the same six-row array a third time), `runP4Calculation()`, `renderP4Results()`, `generateP4Report()`, `clearP4Fields()`, `showP4Error()`. `showLanding()`/`showPathway()` extended to hide/show `#pathway4-view` and re-derive the human-impact footer (`updateHumanImpactFooter(p4State.safetyGlass, 'Table 5.1')` — table name is always `'Table 5.1'` here, never re-derived from an angle the way Pathway 3's is, since there is no angle). Landing page tile (`#tile-pathway4`) un-disabled — `onclick="showPathway('pathway4')"` replaces the `disabled`/`title="Coming soon"`/`.pathway-tile-disabled` markup and the "Coming soon" badge `<div>`, description text unchanged from v1.16. `copySnapshotAsImage()`/`buildSnapshotHTML()` reused directly, unchanged, same as Pathway 3 — no changes needed. **No `updateTwoEdgeAvailability()` call anywhere in the new code** — that function is Bushfire/Safety-Glass-vs-2-edge logic irrelevant to a pathway with no support-condition control at all.
- Copy-as-image and report generation both follow the same dispatch/reuse pattern Pathway 3 established — no new snapshot or report-download mechanism was invented.

**Full eight-suite regression, all green, zero regressions (unchanged counts — this was a UI-only session, no engine files touched):** `test_runner` (19/19), `test_runner_2` (17/17), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (6/6), `test_pathway3` (7/7), `test_pathway4` (7/7).

**Verification performed this session — HTTP-level only, NOT live-browser:** no Chrome browser tool was available in this Claude Code environment this session (confirmed via tool search; matches Section 0's existing note that Claude Code lacks a browser tool). Ran the Flask dev server directly and verified via raw HTTP requests: (1) toggle OFF, `full_perimeter`, height=1219mm/width=2438mm/Pz=2.0kPa — governing 12mm/12mm for Monolithic Toughened and Laminated Annealed, matching Case A/C's known dead-load-governed figures from the v1.18/v1.19 changelog entries exactly; (2) toggle ON, same geometry at Pz=4.0kPa — Monolithic Annealed correctly returns `HUMAN_IMPACT_INELIGIBLE` without crashing, `governing_thickness_mm` still populated from bite alone (15mm), Monolithic Toughened's Table 5.1 search shows a genuine FAIL-then-PASS trace (4mm FAIL at 2.0m² limit, 5mm PASS at 3.0m² limit) landing on `table_5_1_thickness_mm=5`; (3) `/generate_report` downloaded and inspected directly — the TXT output contains the full wind-bite/dead-load breakdown (wind span, dead load perimeter, wind bite, dead load bite, governing bite, all present unconditionally per decision 3 above) and the per-thickness Table 5.1 trace for the passing subtype, both correctly rendered.

**What HTTP-level verification cannot confirm, and therefore remains genuinely unverified:** DOM-rendered behaviour — the safety-glass toggle correctly refreshing the checkbox list on click, the landing-page tile's enabled/clickable state in a real browser, the result cards actually rendering via a real Calculate button click (not just the JSON response being correct), the accordion expand/collapse, and copy-as-image actually producing a clipboard PNG. Per Section 0's own standing discipline (added v1.14, reaffirmed at every UI-touching session since — Pathway 3's v1.15 entry is the clearest precedent), curl/HTTP-level checks are explicitly **not** treated as a substitute for this. **This is a genuine, acknowledged gap, not a skipped step** — the next session (or a manual check by Sahil) must perform a live browser click-test — toggle safety glass on/off and confirm the checkbox list + footer update, submit with a subtype that hits `HUMAN_IMPACT_INELIGIBLE` and confirm no crash, download the TXT report and confirm the dead-load breakdown renders — before Pathway 4's UI is treated as fully verified, matching exactly the bar Pathway 3 was held to at v1.15.

**No engine code touched.** `engine/structural_glazing/`, `engine/combined/pathway3.py`, `engine/combined/pathway4.py` (aside from the new `__init__.py` export, which changes nothing about `pathway4.py` itself) all unchanged. No Pathway 1/2/3 UI code touched, aside from `showLanding()`/`showPathway()`'s minimal extension to recognise the new `pathway4` case (additive, not a rewrite of existing branches).

**This closes the last remaining gap in the four-pathway model, engine + UI both complete for every pathway** — pending the live browser verification noted above, and pending Sahil's independent hand-verification of the underlying engine figures (still outstanding since v1.18/v1.19/v1.22/v1.23, unchanged by this UI-only session).

### v1.24 — 13 July 2026 — Session close-out: v1.23 EXTRAPOLATE fix committed, Pathway 4 engine work declared complete, handoff prepared for Pathway 4 UI

**Committed `9baad81910a53a65b9e573152edbcb633edf96ba`** (short `9baad81`) — contains two things, bundled deliberately rather than split (see reasoning below):

1. **The v1.23 EXTRAPOLATE bugfix** (previous changelog entry, unchanged from what it describes): `get_safety_glass_max_area()` now returns a genuine linearly-extrapolated float for thickness >12mm instead of the `'EXTRAPOLATE'` sentinel; all consumer special-casing removed from `wind.py`, `pathway3.py`, `pathway4.py`, `app.py`, `index.html`; new `test_runner_2.py` TC-U (3500×6500mm Laminated Annealed, genuinely `NO_COMPLIANT_THICKNESS` at every stocked size up to 24mm); `test_pathway4.py`'s docstring corrected where it had claimed this failure class was unreachable.
2. **The outstanding v1.22 `test_pathway4.py` test suite** (7 tests, up from 4, covering the Table 5.1/safety-glass-toggle wiring into Pathway 4's `full_perimeter` scenario). This test file was found to be still uncommitted at the start of this session, even though the engine code it tests (`make_pathway4_result()`, `_run_table_5_1_search()` in `pathway4.py`) was already committed in `0d763a3`. Bundled into this commit rather than split into a separate one, because this session's EXTRAPOLATE-fix edits land inside those same v1.22 tests (the docstring correction, and the fact that TC-6/TC-7's Table 5.1 searches now run through the fixed code path) — a clean split wasn't possible without one commit referencing test content that doesn't exist in the other.

**Full regression at commit time, all eight suites green:** `test_runner` (19/19), `test_runner_2` (17/17, includes TC-U), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (6/6), `test_pathway3` (7/7), `test_pathway4` (7/7).

**Pathway 4 ENGINE WORK IS NOW COMPLETE.** Everything below is done, committed, and regression-green:
- Edge-polish deduction (`EDGE_POLISH_DEDUCTION_MM`, v1.18)
- Scenario scope gate (`full_perimeter` only; `verticals_only`/`horizontals_only` return `CONFIGURATION_OUT_OF_SCOPE_V1`, v1.18)
- `full_perimeter` wind-span bug fix (`min()` not `max()` of width/height, v1.19) plus Case D wind-governs coverage (v1.20)
- Table 5.1 full_perimeter reclassification, decided v1.21 and wired into the engine v1.22 (per-subtype `make_pathway4_result()`, mirroring Pathway 3)
- The v1.23 EXTRAPOLATE fix (this changelog's prior entry), now also fully committed as of this session

**NOT hand-verified by the engineer yet** — the structural glazing test figures (Case A/C/D), the v1.22 Table 5.1 wiring figures, and the v1.23 extrapolation/TC-U figures are all still pending Sahil's independent check, per the standing discipline (Section 0). Being committed does not mean validated.

**What is explicitly NOT done: Pathway 4 has no UI and no report generation.** Unlike Pathway 3 (engine + UI + report generation + copy-as-image, all complete and live-verified, v1.15), Pathway 4 today is engine-only — there is no form, no route, no result rendering, no TXT report, no copy-as-image for it in `interfaces/flask_app/`. This is the explicit next task for the next session (both here and in Claude Code) — see Section 0 for the handoff prompt.

**Bug found and confirmed by Sahil (with an engineer-provided extrapolation method), not implementation-discovered.** `get_safety_glass_max_area()` (`engine/wind_load/formulas.py:339`) returned the sentinel string `'EXTRAPOLATE'` whenever `nominal_thickness_mm > 12` — AS 1288 Table 5.1 only tabulates up to 12mm. Every consumer of this shared function treated that sentinel as an automatic PASS, terminating whatever search or check it was running **without ever comparing the panel's actual area against any limit**. `panel_area_m2` was still recorded and displayed in every trace/report, giving the appearance of a real check having been performed when none had. This is a correctness gap in the underlying calculation, not a display bug — it affects every pathway that calls the function: **Pathway 1** (Mode 1 STEP 3's independent Table 5.1 search, and Mode 2's single-thickness pane check and next-compliant-thickness search — `engine/wind_load/checks/wind.py`, three separate call sites), **Pathway 3** (`_run_table_5_1_search()` in `engine/combined/pathway3.py`), and **Pathway 4** (`_run_table_5_1_search()` in `engine/combined/pathway4.py`). Pathway 1 is already in testers' hands; this was a silent gap in a shipped feature, not a pre-release finding.

**This gap was already known and flagged, not newly discovered this session.** The v1.22 changelog entry (this document, prior entry) explicitly documented the bypass while investigating Pathway 4's Table 5.1 wiring: *"a genuine Table 5.1 NON_COMPLIANT... is structurally unreachable with today's real stock data for any eligible subtype... `get_safety_glass_max_area()` returns `'EXTRAPOLATE'` above 12mm, which... treat[s] as an automatic pass."* That entry correctly declined to fabricate a failing case to work around the gap, and instead recorded it as a known limitation. This session resolves the underlying gap directly.

**Fix, engineer-confirmed method:** Table 5.1's thickness-vs-max-area relationship is linear at slope 1 (1 m² of extra allowable area per 1mm of extra thickness) across nearly every row in both categories. For `nominal_thickness_mm > 12`, the max area is now computed as `SAFETY_GLASS_AREA_CAT{1,2}[12] + (nominal_thickness_mm - 12)`, anchored at the real 12mm table value, rather than returning the sentinel. `get_safety_glass_max_area()` now always returns either a genuine float or `None` (glass type/subtype ineligible) — never a string. The docstring now also records that CAT2's 5mm row (2.2 m²) is a genuine anomaly breaking the linear pattern elsewhere in the table (slope-1 from 6mm would predict 2.0 m²) — noted so nobody later assumes perfect linearity across the whole table; this doesn't affect the fix, since extrapolation is anchored at the 12mm end, not derived from the 5mm row.

**Every consumer's `'EXTRAPOLATE'` special-casing removed**, per instruction — extrapolated and table-listed values are now indistinguishable to every call site, which is the point: the existing `panel_area_m2 <= max_area` comparisons now work unchanged for thicknesses beyond 12mm, exactly as they already did for thicknesses within the table. Touched: `engine/wind_load/checks/wind.py` (three sites — STEP 3 search, Mode 2 single-pane check, next-compliant-thickness search loop; the next-compliant loop's `cmax is None` ineligibility branch was previously conflated with the extrapolation branch under one `cmax == 'EXTRAPOLATE' or cmax is None` condition — now split, since ineligibility and extrapolation are different things and only ineligibility should auto-pass-through unconditionally), `engine/combined/pathway3.py` and `engine/combined/pathway4.py` (`_run_table_5_1_search()`, identical local-reimplementation pattern in both, per their existing no-cross-import discipline), `interfaces/flask_app/app.py` (report text generation, both the per-thickness trace line and the summary line), `interfaces/flask_app/templates/index.html` (Mode 1 and Mode 2 result rendering JS). **Eligibility is still checked before extrapolation is even considered** — `SAFETY_GLASS_CATEGORY.get()` returning `None` still short-circuits to `None` regardless of thickness, confirmed by TC-J/TC-K (Monolithic Annealed/Heat-strengthened, both ineligible, both still return `SG_INELIGIBLE` correctly with this fix in place, both unchanged in this session).

**Existing test case audit — every pathway checked, zero expected results changed.** Every existing test case across all eight suites that sets `safety_glass_required=True` was reviewed for reliance on the old bypass (i.e. any case reaching a stocked thickness >12mm during its Table 5.1/Mode 1 SG search). None were found: `test_runner_2.py` (TC-H/TC-I/TC-R/TC-S all resolve at 4-6mm), `test_pathway3.py` (test_3's Table 5.1 figure resolves at 8mm), `test_pathway4.py` (test_6's Table 5.1 search resolves at 5mm/6mm for both subtypes checked, well under 12mm; test_7 short-circuits on ineligibility before the search loop even runs), `test_structural_consistency.py` (its safety-glass cases are all ineligibility checks, not area searches). Full regression confirms this: all eight suites green before and after, with the sole numeric change being the one new test case added below — **no existing test's expected value needed updating**, because no prior test case happened to be exercising the buggy range.

**New test case added, genuinely reachable and genuinely failing:** `test_runner_2.py` TC-U — Laminated Annealed, 3500mm × 6500mm (22.75 m² panel), low wind (ULS 0.5kPa/SLS 0.2kPa, so wind never governs and the failure is unambiguously the Safety Glass Area Check). Laminated Annealed's largest stocked thickness is 24mm; extrapolated CAT2 max area at 24mm = 9.0 + (24 − 12) = 21.0 m². 22.75 m² > 21.0 m², so the search now correctly fails at every stocked thickness including the extrapolated ones (16/20/24mm), producing a genuine `NO_COMPLIANT_THICKNESS` — confirmed via direct `run_calculation()` call before being added as a test case, full `sg_trace` inspected (FAIL at all of 5/6/8/10/12/16/20/24mm). This is the exact case class the v1.22 changelog flagged as unreachable; it is reachable now because the bypass that made it unreachable is what this session removed. `test_pathway4.py`'s module-level NOTE (written under the old assumption) updated in place to point at this fact and at TC-U, rather than left stating a now-false claim.

**Full regression, all eight suites green:** `test_runner` (19/19, unchanged), `test_runner_2` (**17/17, up from 16/16** — TC-U added), `test_structural_consistency` (pass, unchanged), `test_silicone_bite` (17/17, unchanged), `test_table_5_3` (10/10, unchanged), `test_structural_glazing` (6/6, unchanged), `test_pathway3` (7/7, unchanged), `test_pathway4` (7/7, unchanged — no new test added here, see NOTE update above; TC-U in `test_runner_2.py` was judged the cleaner, more isolated place to demonstrate the mechanic since Pathway 4's own geometry that reaches a 22+ m² panel also triggers `BITE_NO_COMPLIANT_THICKNESS` first, which would obscure rather than isolate the Safety Glass Area Check failure).

**NOT YET HAND-VERIFIED BY SAHIL** — the extrapolation formula, the CAT2 5mm anomaly note, and TC-U's figures should all be reviewed before being treated as validated, same discipline as every other engine change this session.

**Scope:** engine + report/UI text only (no layout/markup changes to `index.html`, only the JS string logic that referenced the old sentinel). No Pathway 2 changes — Pathway 2 does not call `get_safety_glass_max_area()` at all (it uses Table 5.3 exclusively, a separate function). No changes to `SAFETY_GLASS_AREA_CAT1`/`SAFETY_GLASS_AREA_CAT2`/`SAFETY_GLASS_CATEGORY` table data itself — same values as before, only how thicknesses beyond the table's last row are handled.

### v1.22 — 10 July 2026 — Table 5.1 + safety-glass toggle wired into Pathway 4 (full_perimeter only), implementing the v1.21 decision

**This implements the v1.21 documentation-only decision (Section 12.12 item 9, Section 14.7): Pathway 4's `full_perimeter` scenario now genuinely runs Table 5.1 when the safety-glass toggle is ON, not just documented as the intended rule. `verticals_only`/`horizontals_only` and the edge-polish deduction / span-bug fix are all untouched.**

**Investigation performed before writing any integration code (as instructed):**
1. Confirmed Pathway 1/3's actual mechanism: `get_safety_glass_max_area(glass_type, glass_subtype, nominal_thickness_mm)` (`engine/wind_load/formulas.py:339`) returns a max panel area in m² per thickness; eligibility (`SAFETY_GLASS_CATEGORY`, `SAFETY_GLASS_INELIGIBLE`) is keyed by `(glass_type, glass_subtype)` **tuples**, not broad category. The toggle gate is real — Table 5.1 is only ever invoked when `safety_glass_required=True`, confirmed in both Mode 1's STEP 3 and Pathway 3's `_run_table_5_1_search()`.
2. Confirmed Table 5.1's actual input is `panel_area_m2 = height × width` — a **raw area**, unrelated to the wind-bite "span" concept (`min(width_m, height_m)`, the v1.19 fix). No translation needed; Pathway 4's existing `height_m`/`width_m` map directly.
3. **Found a genuine architectural mismatch, reported before implementing:** `run_structural_glazing_calculation()` has no glass-subtype concept at all — it returns one bite-based nominal thickness per Table 4.1 **broad category** (Monolithic/Laminated), shared across every subtype in that category. But Table 5.1 eligibility and area limits are subtype-specific (e.g. Monolithic Toughened is eligible, Monolithic Annealed/Heat-strengthened are not, despite sharing the same bite-based thickness). Direct reuse inside the engine wasn't possible without adding subtype-awareness to `engine/structural_glazing/` itself — out of scope for this session. **User confirmed (via question):** wire this into the **orchestrator** (`pathway4.py`), per-subtype, mirroring Pathway 3's own bite-once/human-impact-per-subtype structure — not a broad-category worst-case fold-in.

**Implementation:**
- **`engine/combined/pathway4.py`:** `run_pathway4_calculation()` gained a new `safety_glass_required=False` parameter (default OFF, matching Section 14.7's toggle-is-user-declared rule). The `CONFIGURATION_OUT_OF_SCOPE_V1` branch (`verticals_only`/`horizontals_only`) is **completely unchanged** — still returns a single `make_structural_glazing_result()` dict, since it never reaches per-subtype work. The `full_perimeter` branch now: runs the shared bite/dead-load calculation once (unchanged call), then loops over all six `(glass_type, glass_subtype)` pairs, applying Table 5.1 independently per subtype when the toggle is ON, and returns `max(bite_thickness, table_5_1_thickness)` per subtype. **Return shape now differs by branch, deliberately** — out-of-scope stays a single dict, `full_perimeter` returns a dict of six `make_pathway4_result()` entries keyed by subtype tuple, same shape convention as `run_pathway3_calculation()`.
- **New `_run_table_5_1_search()` inside `pathway4.py`** — a **local reimplementation** of the same ascending-scan shape as `pathway3.py`'s private `_run_table_5_1_search()` (same ascending-scan pattern, reuses the actual shared `get_safety_glass_max_area()` formula), not a cross-import from `pathway3.py`. Reasoning: that function is private to `pathway3.py`, and importing it would create an orchestrator-to-orchestrator dependency this codebase doesn't use anywhere else — `pathway3.py` itself set the precedent of local reimplementation over cross-module reuse when an existing implementation wasn't cleanly isolatable (its own module docstring explains the same choice, for the same reason: `check_glass_type()`'s Table 5.1 gate isn't isolatable when paired with 4-edge support). This keeps **Pathway 3 completely untouched**, per this session's explicit scope.
- **New `make_pathway4_result()`** added to `engine/shared/results.py`, following the existing constructor discipline (Section 6.4) — modeled closely on `make_pathway3_result()`, with `subtype`/`glass_type`/`glass_subtype`, `governing_thickness_mm`, `bite_thickness_mm`, `table_5_1_thickness_mm`, `panel_area_m2`, `safety_glass_required`, `bite_trace`, `table_5_1_trace`. Statuses: `PASS`, `BITE_NO_COMPLIANT_THICKNESS`, `HUMAN_IMPACT_INELIGIBLE` (falls through with `governing_thickness_mm` still populated from bite alone — same behaviour as Pathway 3's identical case, not a crash or skip), `HUMAN_IMPACT_NO_COMPLIANT_THICKNESS`.

**Found and flagged, not faked, before writing tests:** a genuine Table 5.1 `NON_COMPLIANT` (search exhausts a subtype's full stocked thickness list with no pass) is **structurally unreachable with today's real stock data** for every currently Table-5.1-*eligible* subtype (Monolithic Toughened, Laminated Annealed/Heat-strengthened/Toughened) — each of their stocked lists contains a thickness `>12mm`, and `get_safety_glass_max_area()` returns `'EXTRAPOLATE'` above 12mm, which both the canonical Mode 1 implementation and this new search treat as an automatic pass. The one subtype whose list tops out at 12mm (Monolithic Heat-strengthened) is itself in `SAFETY_GLASS_INELIGIBLE`, so it never reaches the search loop at all. This is the same class of fact as the already-documented Table 5.3 2-edge/3-edge finding (Section 12.13). **User's explicit instruction: do not monkeypatch the stocked-thickness list to force an unreachable case.** Instead, the "toggle ON and failing" test coverage uses `HUMAN_IMPACT_INELIGIBLE` (a real, reachable rejection today) plus a genuine mid-search FAIL-before-PASS trace check, to demonstrate the area-exceeded mechanic honestly.

**`tests/test_pathway4.py` — 7/7, up from 4/4.** Test 1 rewritten for the new per-subtype return shape (cross-checked against a direct `run_structural_glazing_calculation()` call, toggle defaulting OFF). Tests 2–4 (scope gate) **unchanged**, since the out-of-scope branch's shape didn't change. Three new tests: **test 5** (toggle OFF — Table 5.1 not checked at all, `governing_thickness_mm == bite_thickness_mm` for every subtype, matching Section 14.7's gating rule exactly); **test 6** (toggle ON, passing — Monolithic Toughened and Laminated Annealed, Case D geometry, `panel_area_m2 = 2.9719`, genuine FAIL-then-PASS trace entries, bite still governs the overall figure even though Table 5.1's own search passes at a smaller thickness); **test 7** (toggle ON, `HUMAN_IMPACT_INELIGIBLE` — Monolithic Annealed/Heat-strengthened, confirming the fallthrough behaviour doesn't crash or skip, `governing_thickness_mm` still equals bite).

**Full regression, all eight suites green, zero regressions, 82 test-function checks total (was 79):** `test_runner` (19/19), `test_runner_2` (16/16), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (6/6, untouched this session), `test_pathway3` (7/7, untouched this session), `test_pathway4` (**7/7, up from 4/4**).

**NOT YET HAND-VERIFIED BY SAHIL** — none of this session's figures (Table 5.1 pass/fail thresholds, governing thicknesses) should be treated as validated until reviewed.

**No UI touched. No Pathway 1/2/3 code touched. `verticals_only`/`horizontals_only` paths and the edge-polish deduction / span-bug fix logic all untouched.**

### v1.21 — 10 July 2026 — Documentation-only: Pathway 4 full_perimeter human impact table reversed from Table 5.3 to Table 5.1

**This is a documentation-only update — no code, tests, or engine logic changed this session.**

**Decision:** For Pathway 4's `full_perimeter` scenario (sealed on all four edges), human impact assessment uses **Table 5.1** (4-edge framed equivalent), not Table 5.3. This applies **only** to `full_perimeter` — `verticals_only` and `horizontals_only` (currently gated out of scope at the orchestrator anyway, Section 12.12 item 8) remain under Table 5.3 per the existing rule, since they lack support on all four edges.

**This reverses part of the previously documented rule** (Section 12.12/14.7, and originally stated in the v1.6 changelog), which held that Table 5.3 applies to "all flat structural glazing cases" universally, as a conservative catch-all. That blanket rule is now split: `full_perimeter` moves to Table 5.1, `verticals_only`/`horizontals_only` stay on Table 5.3.

**Reasoning, recorded in full:** Pathway 4's `full_perimeter` configuration is glass silicone-bonded continuously around all four edges to a frame member. The frame itself does not mechanically retain the glass the way a standard framed window does (no rebate gripping the glass by its own rigidity) — instead, the continuous structural silicone bond *is* the retention mechanism, transferring load from the glass to the frame. This is mechanically the same support condition as the 90° structural silicone butt joint already confirmed for Table 5.1 in Pathway 3 (glass-to-glass, mutually bracing — Section 12.10): in both cases, a continuous structural silicone bond provides genuine edge support equivalent to mechanical framing, just via adhesive bond rather than a rebate. Since a 90° joint is accepted as providing the same structural support as a fully framed edge, and full-perimeter sealing provides that same continuous silicone-to-frame support on all four sides, it should be treated as 4-edge supported for Table 5.1 purposes on the same basis — not as a separate or weaker case defaulting to Table 5.3's more conservative treatment.

**Confirmation source:** confirmed directly by Sahil, based on consultation with two named external experts — **Adam Davies** (Australian Glass and Window Association, AGWA) and **Siddharth Kumaran** (Viridian Glass; formerly AGWA's primary structural engineer and a co-author/contributor to the AS 1288 standard's drafting). This confirmation was given in direct response to the specific `full_perimeter`, silicone-bonded-to-frame configuration described above — not a general analogy applied afterward by this project. Conversation dated 10 July 2026.

**Related clarification, recorded explicitly so it isn't mistaken for an inconsistency: this does NOT reopen the bushfire exclusion.** AS 3959's "fully framed" requirement for BAL 12.5/19/29 eligibility means genuine *mechanical* frame support on all four edges — a different definition of "framed" than Table 5.1's structural-equivalence basis. Table 5.1 asks whether the edge behaves *structurally* like a framed edge (which a continuous silicone bond satisfies). AS 3959 asks whether there is an actual mechanical frame member providing the sealing/radiant-heat performance the bushfire provisions depend on (which silicone bonding does not provide, regardless of structural adequacy). Two different standards, two different questions — Table 5.1 applying and the AS 3959 exclusion still applying are both correct simultaneously. `full_perimeter` remains bushfire-excluded, unchanged.

**Sections updated:** 12.12 (new item 9, full reasoning and source), 14.4 (Branch 4 description — human impact and bushfire lines), 14.7 (per-pathway/scenario table selection list).

**Implementation status — NOT wired into the engine.** `engine/structural_glazing/` (Phase 1C) currently computes wind bite, dead load bite, and the governing Table 4.1 lookup only — it has no Table 5.1, Table 5.3, or safety-glass-toggle logic at all. This entry records the decision for when that wiring is eventually built (a separate, not-yet-started task); `run_structural_glazing_calculation()`'s behaviour is unchanged today. No test suite is affected — full regression remains at 79/79 (v1.20's count, unchanged this session).

**No code, tests, UI, or Pathway 1/2/3 content touched.**

### v1.20 — 10 July 2026 — New test coverage: Case D closes the full_perimeter wind-governs gap left by v1.19's fix

**Coverage gap identified:** v1.19 fixed `full_perimeter`'s `wind_span_m` from `max(width_m, height_m)` to `min(width_m, height_m)`, which flipped Case A's governing load case from wind to dead load. Combined with Case C already being dead-load-governed, this left **zero test coverage for the `full_perimeter` wind-load code path** — the exact code path the v1.19 bug was in — since both remaining `full_perimeter` test cases now exercise only the dead-load branch of `governing_bite_mm = max(wind_bite_mm, dead_load_bite_mm)`.

**New Case D, added as `test_6` in `tests/test_structural_glazing.py`** (existing tests renumbered nowhere — inserted after `test_5`, `run_tests()`'s list extended): same geometry as Case A/C (height=1.219m, width=2.438m, so span = min(1.219, 2.438) = 1.219m, same as Case A/C post-fix), but `pz_kpa=4.0` — high enough to push wind back above the fixed 8.5417mm dead load figure for this geometry.

**Computed and verified:**
- `wind_span_m` = 1.219 (same as Case A/C)
- `wind_bite_mm` = 0.5 × 4.0 × 1.219 / 0.21 = **11.6095mm**
- `dead_load_bite_mm` = 8.5417mm (unchanged — depends only on height/width/thickness, not `pz_kpa`)
- `governing_bite_mm` = 11.6095mm — **wind governs**, unlike Case A/C
- Table 4.1 lookup with `EDGE_POLISH_DEDUCTION_MM` (2mm) applied, computed independently against this case's own governing bite (not assumed): **nominal_monolithic = 15mm, nominal_laminated = 16mm**

These figures are numerically identical to Case A's *old*, pre-span-fix result (15mm/16mm) — a coincidence of this session's chosen Pz (4.0kPa here reproduces the same 11.6095mm bite Case A's incorrect 2.438m span produced at 2.0kPa), not a shortcut — the lookup was performed independently against Case D's own inputs. **Not yet independently hand-verified by Sahil.**

**Full regression, all eight suites green, zero regressions, 79 checks total (was 78):** `test_runner` (19/19), `test_runner_2` (16/16), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (**6/6, +1**), `test_pathway3` (7/7), `test_pathway4` (4/4).

**No engine logic changed — test-addition only.** Cases A, B, and C untouched. No UI, Pathway 1/2/3 code, or constants touched.

### v1.19 — 10 July 2026 — Bug fix: full_perimeter wind span used the wrong AS 1288 Appendix F convention (max instead of min)

**Bug found (engineering, not implementation) and confirmed directly by Sahil (domain authority for this decision):** `run_structural_glazing_calculation()`'s `full_perimeter` branch in `engine/structural_glazing/formulas.py` set `wind_span_m = max(width_m, height_m)`. This is wrong for AS 1288 Appendix F flat structural glazing — **B (the span) is the SHORTER of the two supported dimensions** when sealed on all four sides, not the longer one. The `max()` convention was wrongly inherited from Pathway 3's Section 9 faceted-joint formula (a different physical scenario — corner/angle glazing — with its own, different B convention: the larger width governs there). Fixed to `wind_span_m = min(width_m, height_m)`.

**Scope of the fix, confirmed correct:**
- Only the `full_perimeter` branch was affected. The `verticals_only` branch's `wind_span_m = width_m` (distance between the two sealed vertical edges) was already correct and is untouched.
- `horizontals_only` remains out of scope at the engine level (`CONFIGURATION_OUT_OF_SCOPE`) — unaffected by this fix.
- `dead_load_perimeter_m` and `calculate_dead_load_bite()` are **not** affected — they compute directly from `height_m`/`width_m`, never from `wind_span_m`. Not touched.
- The v1.18 edge-polish deduction (`EDGE_POLISH_DEDUCTION_MM`) is unrelated and untouched.

**Case A and Case C recomputed** (the only two existing test cases using `full_perimeter`; height=1.219m, width=2.438m throughout, so span = min(2.438, 1.219) = 1.219m for both, versus 2.438m pre-fix):

| Case | Pz | wind_span_m | wind_bite_mm | dead_load_bite_mm | governing_bite_mm | Governs (pre-fix → post-fix) | mono/lam (pre-fix → post-fix) |
|---|---|---|---|---|---|---|---|
| A | 2.0kPa | 1.219 (was 2.438) | 5.8048 (was 11.6095) | 8.5417 (unchanged) | 8.5417 | **wind → dead load** | 15/16mm → **12/12mm** |
| C | 0.5kPa | 1.219 (was 2.438) | 1.4512 (was 2.9024) | 8.5417 (unchanged) | 8.5417 | dead load → dead load (no flip) | 10/10mm → **12/12mm** |

**Case A's governing load case flips from wind to dead load** — halving the span (2.438m → 1.219m) roughly halves the wind bite (Appendix F's formula is linear in span), dropping it below the unaffected dead load figure. Case C's dead load already governed pre-fix, so no flip there, but its wind figure still halves for the same reason. **Notable consequence:** with the corrected span, Case A and Case C now produce identical governing figures (both dead-load-governed at 8.5417mm, 12mm/12mm for both glass types) — dead load doesn't depend on `pz_kpa` at all, so once wind drops below it in both cases, the two Pz values stop differentiating the outcome. **Not independently validated by Sahil yet — will be hand-checked against the real Appendix F formula before being treated as validated.**

**`tests/test_structural_glazing.py` updated:** `test_1` (Case A) and `test_3` (Case C) rewritten with the new expected values above, each with an expanded comment showing the arithmetic (span recalculation, wind bite recalculation, which load case governs, edge-polish-deducted Table 4.1 lookup) rather than just the new numbers — same comment style as v1.18's edge-polish update. `test_2` (Case B, `verticals_only`) is unaffected by this fix and was left untouched — confirmed still passing unchanged, since `verticals_only`'s span was already correct.

**Full regression, all eight suites green, zero regressions, 78 checks total:** `test_runner` (19/19), `test_runner_2` (16/16), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (5/5 — tests 1/3 updated per above, test 2 unchanged), `test_pathway3` (7/7), `test_pathway4` (4/4 — cross-checks Case A dynamically against the engine rather than hardcoding figures, so it required no changes and still passes with the corrected values).

**No UI touched. No Pathway 1/2/3 code touched. Edge-polish deduction logic untouched.** Engine-only bug fix.

### v1.18 — 10 July 2026 — Michael's three Section 12.12 confirmations implemented (edge-polish deduction, rounding, Pathway 4 scenario scope)

Michael (domain engineering authority) confirmed all three of Section 12.12's pending items this session. All three implemented.

**1. Edge-polish deduction — reverses the v1.9 "no deduction" decision.** Michael confirmed edge polishing on frame-bonded (flat, angle-free) glazing edges does reduce usable contact thickness, and specified a flat 2mm deduction for all nominal thicknesses, both monolithic and laminated. New `EDGE_POLISH_DEDUCTION_MM = 2` in `engine/structural_glazing/constants.py`, with an explicit comment explaining why it is **not** a reuse of `CHAMFER_ALLOWANCE_MM` (`engine/shared/table_4_1.py`) despite the identical value — the faceted engine's chamfer exists because silicone bonds to the *cut edge itself* (the bonding surface is the through-thickness dimension); here silicone bonds to the *flat glass face*, and the deduction instead accounts for perimeter edge-polish treatment. Same number, different physical justification, kept as two separate named constants so neither misrepresents why it exists.

Implementation reuses the shared usable-thickness search already built for the faceted engine — `find_min_nominal_for_usable_bite()` (`engine/shared/table_4_1.py`) — rather than duplicating the search loop. Checked the function's actual signature first: it accepts a `chamfer_mm` override and branches on `joint_type == 'mitred'` vs. everything else (the non-mitred branch is exactly `usable = actual - chamfer_mm`, which is what this module needs). `engine/structural_glazing/formulas.py` now calls it with `joint_type=None` (there is no mitre concept in this module — flat glazing only, Section 12.12 item 2) and `chamfer_mm=EDGE_POLISH_DEDUCTION_MM`, replacing the old raw-thickness `find_min_nominal_for_bite()` call. The 6mm nominal-thickness floor (`apply_thickness_floor()`) is applied after this lookup, unchanged.

**2. Rounding — confirmed as an expected discrepancy, no code change.** Michael confirmed Duce's manual process rounds to 2 decimal places before comparing against Table 4.1 (e.g. 6.0277→6.03, 6.0001→6.00). This tool deliberately does not round before comparison (Section 12.12 item 7, locked in at v1.9 as a liability decision — rounding can convert a genuine fail into a pass). This confirms the tool will occasionally be *stricter* than Duce's existing manual precedent near a boundary. Documented here and in Section 12.12; no behaviour change.

**3. Pathway 4 scenario scope gate — new `engine/combined/pathway4.py`.** Pathway 4 had no orchestrator (unlike Pathway 3's `engine/combined/pathway3.py`) despite the engine (Phase 1C) being built since v1.9. Built now, following the same one-orchestrator-per-pathway pattern: `run_pathway4_calculation()` accepts a `scenario` parameter and only proceeds to call `run_structural_glazing_calculation()` when `scenario == 'full_perimeter'`. Any other value — including `'verticals_only'`, a real, already-built and tested engine capability (Case B) — returns a new status, `CONFIGURATION_OUT_OF_SCOPE_V1`, with a message noting the configuration isn't yet available in this version and may be added later. `'horizontals_only'` also hits this same gate (it was already out of scope at the engine level too, for a different reason — Section 12.12 item 5, weatherseal only). **The gate lives entirely in the orchestrator — `run_structural_glazing_calculation()` itself is untouched and remains fully capable of computing `verticals_only`**, exactly as `test_structural_glazing.py` (unchanged in scope/structure, still tests the engine directly) continues to verify via Case B.

New `tests/test_pathway4.py`, 4 cases: `scenario='full_perimeter'` passes through to the real engine calculation (cross-checked field-by-field against a direct `run_structural_glazing_calculation()` call); `verticals_only` and `horizontals_only` both confirmed returning `CONFIGURATION_OUT_OF_SCOPE_V1` with `nominal_monolithic`/`nominal_laminated` still `None` (never touching the engine); `SUPPORTED_SCENARIOS_V1` locked at exactly `('full_perimeter',)` as an independent guard against future accidental scope widening.

**Case A/B/C recomputed with the new deduction applied (pre-deduction figures alongside for comparison):**

| Case | Config | Governing bite | Pre-deduction mono/lam | **Post-deduction mono/lam** |
|---|---|---|---|---|
| A | full_perimeter, Pz=2.0kPa, wind governs (11.6095mm) | wind | 12mm / 16mm | **15mm / 16mm** |
| B | verticals_only, Pz=2.0kPa, dead load governs (25.6251mm) | dead load | NO_COMPLIANT_THICKNESS (both) | **NO_COMPLIANT_THICKNESS (both) — unchanged**, required bite already exceeded the largest raw thickness before any deduction |
| C | full_perimeter, Pz=0.5kPa, dead load governs (8.5417mm) | dead load | 10mm / 10mm | **12mm / 12mm** |

Case A laminated is the one figure that doesn't move (16mm both before and after) — it was already jumping to 16mm pre-deduction because raw 12mm's min_actual (11.6mm) fell 9.5µm short of the required 11.6095mm bite; the 2mm deduction pushes 12mm further out of reach but doesn't change which size clears it. **Not independently validated by Sahil yet — at least one of these figures will be hand-checked against the real Table 4.1 before being treated as validated; do not treat these as confirmed until that happens.**

**Full regression, all eight suites green, zero regressions:** `test_runner` (19/19), `test_runner_2` (16/16), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (5/5 — expected values in tests 1/3 updated to the post-deduction figures above, since they exercise the engine directly and the engine's real behaviour changed; test structure/scope unchanged, still tests the engine directly per instructions), `test_pathway3` (7/7), `test_pathway4` (4/4, new) — **78 checks total** (74 prior + 4 new).

**Section 12.12 fully resolved** — all three pending items closed. This was the sole remaining blocker before Pathway 4's UI work could begin (Section 10 item 5, Section 12.9). **Pathway 4's UI is now unblocked but still not built** — this session was engine/orchestrator-only, per explicit scope (no UI, no Pathway 1/2/3 changes).

**No UI touched. No Pathway 1/2/3 code touched.** Engine and orchestration work only.

### v1.17 — 10 July 2026 — Visualiser descoped, monthly EXE cadence decided, two queued bugs found (not yet fixed)

**1. Visualiser explicitly descoped from this V2 update.** The full interactive edge/angle visualiser (Section 10 item 12, Section 14.6) is now out of scope for the current version. The four landing-page tile images (v1.16) remain the extent of visual/diagram work for this version.

**2. Monthly EXE rebuild cadence with kill-switch expiry decided, for the remainder of the year.** Bump `EXPIRY_DATE` each cycle. Distribution confirmed via a **OneDrive folder link** (not a direct file link) — testers browse the folder's current contents, avoiding dead-link risk from renaming/versioning the EXE. Open question, undecided: delete superseded EXEs from the folder each cycle, or leave them accumulating (ambiguity-of-which-file risk if left unresolved).

**3. Two real bugs found during a verification pass, confirmed, queued, NOT yet fixed:**
- `launcher.py`'s expiry message (line 45) hardcodes the displayed date as a separate plain string, independent of `EXPIRY_DATE` (line 12) — bumping the constant alone will silently leave the message stale. Fix identified: derive via `EXPIRY_DATE.strftime('%d %B %Y')`. Confirmed via grep as the only such duplication in the project.
- Six of seven `.spec` files in the project root are stale and will fail to build — five reference the deleted `src/` folder, one references a missing icon file. Only `AS1288_Calculator_v1.3.spec` currently builds successfully. Fix identified: delete the six broken specs (after confirming Git-history recoverability), keep only the working one.

Both fixes are drafted as a single Claude Code prompt but have not been run.

**4. Minor cleanup backlog reviewed, explicitly deferred — none actioned.** Five candidates offered (Table 5.3 naming collision, missing Table-5.3 regression test, in-app version/expiry indicator, favicon fix, expiry-constant check — the last of which surfaced item 3 above); user chose "none — just bug fixes this cycle."

**5. Plan decided, not yet executed: consolidate Pathways 1-3 (and Pathway 4 if ready) into a single V2 EXE release, expiry extended to end of August**, replacing incremental releases going forward. Tradeoff accepted: one release means any defect surfaces for every tester simultaneously on an unfamiliar build, raising the bar for pre-release verification — full seven-suite regression + complete live click-through of every included pathway required before this ships.

**6. Still outstanding, unrelated to this session:** Brent hosting-alternatives conversation (Section 9) — outcome unknown, relationship to existing Jamal/SBS engagement never clarified.

**No code changes made this session** — planning/decision record only.

### v1.16 — 9 July 2026 (session 3) — Landing page tile images (all four pathways) + Pathway 3 angle-validation wording

**1. Landing page placeholder images replaced with real artwork, closing out the last open item from v1.11's build log** ("16:9 dashed-border image placeholder ready for real artwork later"). Four user-supplied PNGs (`Pathway_1.png` through `Pathway_4.png`) added to `interfaces/flask_app/static/`, wired into the four landing-page tiles in place of the placeholder `<div>`s. None of the four images are actually 16:9 (Pathway_1: 545×741 portrait; Pathway_2: 1164×648; Pathway_3: 850×676; Pathway_4: dimensions not recorded this session) — `object-fit: contain` added to the shared `.pathway-tile-image` CSS class so each scales to fit the existing tile box without distortion or cropping, letterboxed against the tile's dark background where the aspect ratio doesn't match. Pathway_2's near-16:9 ratio fills its tile almost edge-to-edge; Pathway_1's portrait ratio produces the most visible letterboxing of the four. Confirmed by the user as acceptable as-is — no further image cropping planned.

Tiles 1–3 and their image wiring were done and live-verified (via Claude in Chrome, direct from claude.ai) in one pass; Pathway 4's tile followed as a small separate addition once its image was ready, verified manually by the user in-browser after a dev-server connectivity issue prevented an independent browser check from this chat. **Pathway 4's tile remains disabled/non-clickable ("Coming soon") throughout — image-only change, no `onclick` or enabled-state change**, consistent with it still being pending Michael's three confirmations (Section 12.12).

**2. Pathway 4 tile description wording corrected:** "no frame" changed to "no supporting frame elements" for clarity — tile now reads "Flat glazing, no supporting frame elements, structural silicone bonded to the surface."

**3. Pathway 3 angle-out-of-range validation message reworded** to redirect the user to the correct pathway rather than just stating the input is unsupported. Old wording: *"Included angle must be between 90 and 160 degrees. Outside this range the silicone joint provides no structural edge support (weatherseal only) and is out of scope for this calculator."* New wording: *"Included angle must be between 90 and 160 degrees. Outside this range the silicone joint provides no structural edge support (weatherseal only). Go back to landing page selection and select Partly Framed - Exposed Edges option for glass selection."* Client-side only (`runP3Calculation()`'s `angle<90||angle>160` guard) — the 90–160 validation range and trigger condition are unchanged, text only. Consistent with Section 12.3's confirmed position that Pathway 3 will never build its own weatherseal-only handling for out-of-range angles; the correct destination for that case is Pathway 2, so the message now says so directly.

**Live browser verification performed this session (Claude in Chrome, direct from claude.ai):** all three of Pathway_1/2/3.png confirmed loading without error (`naturalWidth`/`naturalHeight` populated, not broken) and visually inspected against their tile boxes; Pathway 4's tile confirmed untouched (still placeholder text, no `<img>`, still disabled) prior to its own image being added; new angle-validation wording confirmed rendering correctly at both boundary cases (angle=180 and angle=50), old wording confirmed fully absent from the DOM in both cases. Pathway 4's image/description update was verified manually by the user directly (a stale dev-server-process issue from an earlier session prevented an independent browser recheck for this specific piece — noted, not treated as unverified, since the user's direct visual check is a valid substitute per Section 8's existing browser-cache-gotcha precedent of preferring a real, current look over inferred state).

No engine code touched in either change this session. No pytest suites run.

**Git commits this session:** `b9c5d1c` (Pathway 1-3 tile images + Pathway 3 angle wording), `1799c78` (Pathway 4 tile image + description wording).

### v1.15 — 9 July 2026 — Pathway 3 complete: orchestration engine + UI, both live-verified

**1. Pathway 3 orchestration engine built and validated (Section 12.13).** New `engine/combined/pathway3.py` (`run_pathway3_calculation()`) runs `run_bite_calculation()` once per pathway invocation (not per category — confirmed this session that the function has no category parameter at all; it returns `nominal_monolithic`/`nominal_laminated` together in one call), short-circuits per broad category via `nominal_monolithic`/`nominal_laminated is None` (not via the function's overall `status`, which is binary and only reports `NO_COMPLIANT_THICKNESS` when *both* categories fail simultaneously — a real discrepancy from the original build plan's assumption, caught before any code was written), then for subtypes clearing that gate runs independent ULS/SLS via `check_glass_type()` (4-edge, safety glass off) and a separately-computed human impact check (Table 5.1 at exactly 90°, Table 5.3 for >90°–160° with its own 2-edge/3-edge selector), gated on the safety glass toggle per Section 14.7. Governing thickness per subtype = `max()` across all active results.

**Deliberate design decision:** `unframed_edge_condition` is never passed into `check_glass_type()` for this pathway, avoiding a combination (4-edge support + Table 5.3 active) no prior caller had ever exercised and that `check_glass_type()` isn't built to keep mutually exclusive. Table 5.1/5.3 are computed independently in `pathway3.py` instead, keeping `check_glass_type()` itself untouched.

**New constructor:** `make_pathway3_result()` added to `engine/shared/results.py`, following the existing one-constructor-per-path discipline (Section 6.4).

**New test suite:** `tests/test_pathway3.py`, 7 hand-calculable cases (bite governs, wind governs, Table 5.1 governs at 90°, Table 5.3 governs at >90° with both 2-edge/3-edge variants, bite `NO_COMPLIANT_THICKNESS` for one category only with the other category's subtypes confirmed unaffected, a human-impact-ineligible subtype confirmed returning bite/wind results with `human_impact_thickness_mm=None` rather than crashing or being silently skipped).

**Confirmed via direct CSV read:** no Toughened or Laminated row in `Table_5_3.csv` has a joint maximum of 1 — every such row caps at 2 or has no restriction. The only rows with a joint max of 1 are Annealed/Heat-Strengthened, height band 2–2.5m, and both those glass types are already excluded from the Table 5.3 branch whenever safety glass is required. This means the 2-edge/3-edge selector cannot currently produce different results for any glass type eligible to reach Table 5.3 in this pathway — correctly wired, not a defect, just a fact about the standard's current data for this branch.

Full seven-suite regression green: `test_runner` (19/19), `test_runner_2` (16/16), `test_structural_consistency` (pass), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (5/5), `test_pathway3` (7/7) — 74 checks total, zero regressions. Engine-only, no `app.py`/`index.html` changes. **Committed `053ed17`.**

**2. Pathway 3 UI built and fully live-verified (Section 12.13 step 3, closes Section 10 item 5).** Single combined form (height, width 1/2, angle [90–160 validated], corner/general, joint type, wind pressure [direct kPa or N/C rating], safety glass toggle), a new `buildP3GlassTypeCheckboxes()` letting the user select which of the six subtypes to include (only checked subtypes are calculated and rendered — matches the Mode 1 checkbox-selection convention used everywhere else in the tool, corrected before build from an earlier draft that assumed all six always ran), an angle-reactive 2-edge/3-edge selector (`#p3-edge-condition-row`, hidden at exactly 90°, shown for >90°–160°), one Calculate action posting to a new `/calculate_pathway3` route, and a result screen showing one card per selected subtype with its own bite/ULS/SLS/human-impact breakdown. Report generation (`build_pathway3_report()`) and copy-as-image (`buildSnapshotHTML()`/`copySnapshotAsImage()`, reused directly, no changes needed) both built. `updateHumanImpactFooter()` wired to re-derive the correct table name (5.1 vs 5.3) from the current angle, both on toggle and on `showPathway('pathway3')`, per Section 14.7. Superseded `#legacy-calculator-view`/`#silicone-engine-view` markup and JS removed entirely.

**Full live browser verification performed this session via Claude in Chrome, directly from claude.ai** (not Claude Code, which lacks a browser tool in its environment) — covering every item flagged as unverifiable in Claude Code's own build report:
- `#pathway3-view` confirmed active in the live DOM via `getComputedStyle`, not just via JS existing
- 2-edge/3-edge selector confirmed hiding/showing correctly and bidirectionally across the 90° boundary (90→130→90)
- Glass type checkbox list confirmed filtering from 6 to 4 subtypes on safety glass toggle ON, and restoring to 6 on toggle OFF — not stale
- Subset selection (2 of 6 checked) confirmed producing exactly 2 rendered cards via a real Calculate button click, not all six
- Bite thickness figures (10mm for both Monolithic Toughened and Laminated Annealed, 1200×600×600mm, 90°, ULS 2.0kPa) hand-verified against the Section 9 formula and Table 4.1 usable-bite search — exact match
- Table 5.1 branch (angle=90) and Table 5.3 branch (angle=130, 2-edge selector) both confirmed rendering and correctly labelled
- Human-impact footer confirmed switching table name (5.1→5.3) immediately upon angle crossing 90°, before recalculating — matches the existing Pathway 1/2 behaviour
- Copy-as-image confirmed producing a genuine 63,971-byte `image/png` in the actual clipboard via `navigator.clipboard.read()` — not inferred from absent console errors
- Report generation confirmed via `fetch` interception, correct trace detail and correct table/subtype labelling
- No genuine console errors — only the known Section 8.5 browser-extension false positive, recurring on a timer, unrelated to the app

**No bugs found in this verification pass.** **Committed `84b168b`.**

**3. This closes Pathway 3 fully** — engine, UI, report generation, and copy-as-image are all built and live-verified, not just claimed. Section 10 item 5 updated accordingly. **Pathway 4 (structural glazing) is the only remaining pathway without a UI, pending Michael's three confirmations (Section 12.12)** — this is now the only substantive gap in the four-pathway model.

**Git commits this session:** `053ed17` (Pathway 3 engine), `84b168b` (Pathway 3 UI + live browser verification).

### v1.14 — 8 July 2026 — Pathway 2 safety-glass gate fix, human-impact footer wording overhaul, Pathway 3 design decisions locked

**1. Retroactive fix: Table 5.3 in Pathway 2 now gated behind the safety-glass toggle.**
Previously (v1.12/v1.13), Table 5.3 ran unconditionally whenever `unframed_edge_condition` was set, regardless of the safety glass toggle — inconsistent with Pathway 1's Table 5.1, which was always correctly gated. Fixed in `engine/wind_load/checks/wind.py`: Table 5.3 execution (not eligibility filtering — that's unchanged) is now gated on `safety_glass_required=True` AND `unframed_edge_condition` set, in three places — the Mode 1 search, the Mode 2 pane check, and the next-compliant-thickness search loop. The `TABLE_5_3_SAFETY_GLASS_INELIGIBLE` eligibility list and Table 5.1's existing gate were untouched. All six test suites green, zero regressions. **Live-verified in browser** (Claude in Chrome, driven directly from this chat — first time this tool combination was used for verification in this project): 1800×1000mm, 2-edge, Monolithic Toughened, negligible wind (ULS 0.1kPa / SLS 0.05kPa) — toggle ON correctly governs at 6mm via Table 5.3 (ULS/SLS both compute independently at 4mm, Table 5.3 overrides); toggle OFF correctly reverts to 4mm with Table 5.3 excluded entirely. Matches the v1.12 hand-calculated case exactly. Committed `345f70e`.

**2. Human impact footer messaging overhauled — supersedes v1.13's wording entirely.**
v1.13 introduced footer wording implying the tool had "evaluated" or the check "governed" human impact whenever Table 5.1/5.3 ran. **Confirmed with Sahil this session: this overstated what the tool does.** The safety-glass toggle being ON does not mean the tool has assessed *whether* safety glass is required for the application — that determination is entirely the user's, made under AS 1288 Section 5, independent of the tool. The toggle only means the user has already made that determination and is asking the tool to apply the relevant table's thickness/area limits on that basis.

New rule, all pathways:
- **Toggle OFF:** no human impact message displayed at all (not even the old generic disclaimer — removed entirely, not just made conditional).
- **Toggle ON:** *"Safety glass requirements (Table 5.1 / Table 5.3, whichever applies) have been applied to the thickness selection as declared by the user. This tool does not assess whether safety glass is required for this application. The user is responsible for determining applicability in accordance with AS 1288 Section 5 and relevant building codes."*

**Diagnosis performed before fixing (per task instructions):** `table_5_3_status`'s absence from Mode 1 results is **not a bug** — `make_mode1_result()` never included that key by design (Mode 1 is a minimum-thickness search across candidates, not a single-thickness pass/fail check; only `make_mode2_result()` needs a status field). Not introduced by today's gate change. The real problem was two independent stale pieces: `build_report()`'s Table 5.3/5.1 breakdown was gated on the old (pre-fix) conditions, and the on-screen footer was a static, unwired `<div class="footer-note">` left over from before the four-pathway redesign — showing the same text regardless of pathway or toggle state.

Fix: `app.py`'s `build_report()` footer collapsed to one clean conditional (no competing branches). `index.html`'s static footer replaced by a dynamic `#human-impact-footer`, driven by a new `updateHumanImpactFooter(active, tableName)` function, wired into `setSafetyGlass()`, `setP2SafetyGlass()`, `showPathway()`, and `showLanding()` so it can never show stale wording when switching pathways or toggling mid-session.

All six suites green. **Live-verified in browser this session across all four cases** (Pathway 1 toggle ON/OFF, Pathway 2 toggle ON/OFF): correct wording appears immediately on toggle ON (before recalculating even), correct table name substituted (5.1 for Pathway 1, 5.3 for Pathway 2), message disappears immediately on toggle OFF, no trace of old wording anywhere, zero console errors beyond the documented Section 8.5 browser-extension false positive. Committed `9c11a9d`.

**3. New cross-pathway rule, confirmed and now consistent everywhere:** human impact tables (Table 5.1 or Table 5.3, whichever the pathway/angle selects) only run when the safety glass toggle is ON — in every pathway, not just Pathway 1 as previously documented. See new Section 14.7 for the full rule and rationale.

**4. Pathway 3 orchestration design locked in this session (engine-only work, not yet built):**
- **Joint count for Table 5.3 at angle >90°–160°, resolved:** confirmed by Sahil it can be either 2-edge or 3-edge — not fixed at a single joint count as initially assumed. Pathway 3 needs its own 2-edge/3-edge selector for the Table 5.3 branch, matching Pathway 2's pattern, active only when angle is >90°–160° AND the safety glass toggle is ON. At exactly 90°, Table 5.1 applies instead (no joint-count concept), gated the same way.
- **Orchestration location, resolved:** new module `engine/combined/pathway3.py` — not `app.py`, not inside `silicone_bite/` or `wind_load/`. A thin function importing from `silicone_bite`, `wind_load`, and the Table 5.1/5.3 checks; short-circuits per broad glass category (Monolithic/Laminated) if the bite calculation returns `NO_COMPLIANT_THICKNESS`; otherwise runs ULS/SLS and the angle-appropriate human impact check, then `max()`s across bite/ULS/SLS/human-impact. Rationale: engines don't import each other (Section 13.1), and this sequencing logic is engineering decision-making, not presentation, so it doesn't belong in `app.py` either. See new Section 12.13 for the full build plan.
- **Sequenced plan:** (1) DONE this session — Pathway 2 retroactive gate fix + footer wording. (2) **NEXT** — Pathway 3 orchestration engine (`engine/combined/pathway3.py` + `tests/test_pathway3.py`, hand-calculable cases, full six-suite regression). (3) Pathway 3 UI (form, route, report, copy-as-image) — not started until (2) is validated, per standing engine-first discipline.

**5. New standing verification discipline, added this session:** Claude Code's free-text summaries of what it did/found need independent spot-checking (diff the commit, grep for stale strings/old wording, re-run the actual test suites and read raw output) before being trusted. Direct tool output (test runs, diffs, grep results) has held up reliably in every session so far; narrated prose summaries of that output have not always matched reality — this session's footer bug was masked by an earlier "all six suites green" summary for two full exchanges before the live browser check surfaced it. This applies especially to anything touching frontend/DOM rendering, which the six pytest suites structurally cannot exercise (Section 8) — a live browser click-test with DevTools open remains mandatory before any UI-facing change is considered verified; curl/HTTP-level checks are not a sufficient substitute for DOM-rendered behaviour, though they remain adequate for non-DOM outputs like the downloadable TXT report.

**6. New capability noted for future sessions:** this chat has direct access to Claude in Chrome (browser extension) for live click-testing against a locally-running dev server, independent of Claude Code. Used for the first time this session to verify both fixes above. Useful whenever Claude Code lacks browser access or a second independent check is wanted.

**Git commits this session:** `345f70e` (Pathway 2 retroactive gate fix), `9c11a9d` (footer wording overhaul).

### v1.13 — 8 July 2026 — Pathway 2 UI, report generation, and copy-as-image built and live-verified
- **Pathway 2's UI built and wired**, closing out the v1.11 build sequence's item 3. `#pathway2-view` follows the same relocation pattern as Pathway 1 (v1.11): 2-edge/3-edge selector (not 4-edge/2-edge), no IGU option, no Bushfire/BAL section — both deliberate exclusions per Section 14.2. Safety glass toggle filters against a new, independent eligibility list (`P2_SG_INELIGIBLE`, mirroring `TABLE_5_3_SAFETY_GLASS_INELIGIBLE`) via dedicated `buildP2GlassTypeCheckboxes()`/`buildP2PaneInputs()` functions — a new function pair rather than a parameterised version of Pathway 1's, chosen because Pathway 2 has no IGU/Bushfire branches to thread through and uses different container IDs; this also matches the existing precedent of the silicone-bite engine having its own independent state/functions rather than reusing Mode 1/2's.
- **Critical mapping confirmed correct before wiring, then verified live:** the 2-edge/3-edge selector always sends `support_condition: '2-edge'` (AS 1288 has no distinct 3-edge wind-formula condition, Section 14.2/v1.6) while `unframed_edge_condition` carries the real 2-vs-3-edge distinction separately, used only for the Table 5.3 joint-count lookup. Confirmed via direct payload inspection for both a 2-edge and 3-edge selection before this was trusted.
- **`app.py`** now accepts `unframed_edge_condition` from the request and passes it through unchanged to `run_calculation()`/`run_compliance_check()` — this is the one line of `app.py` this session actually needed; Table 5.3 was wired but genuinely unreachable through the live app until this point (v1.12 added the engine-side parameter but nothing supplied it).
- **Bug found and fixed, not Table-5.3-specific:** `format_trace_entry()` in `build_report()` crashed on the `uls_confirmed_passing`-shortcut trace entry (Section 6.6's optimisation — once a candidate is confirmed passing ULS, thicker candidates skip re-checking it and log a short note instead of full k-value detail). This is reachable from any Mode 2 next-compliant search in either pathway, not new to Pathway 2 — it had simply never been exercised by a generated report until this session. Fixed by branching on missing trace-entry keys rather than assuming every entry has the full k1/B/span set. Confirmed Pathway 1's existing report output is unaffected (byte-identical diff pre/post-fix for a case that doesn't hit this trace shape).
- **Report generation built for Pathway 2:** a labelled `TABLE 5.3 CHECK` section added to `build_report()`, structured like the existing ULS/SLS sections (Section 6.5's trace pattern) rather than folded silently into the opaque `fail_reason` string. Confirmed via `git show HEAD:app.py` that `build_report()` had zero prior handling of `table_5_3_*` fields before this session.
- **Copy-as-image reused directly for Pathway 2**, not duplicated or parameterised — `buildSnapshotHTML()`/`copySnapshotAsImage()` were already fully generic; Pathway 2 just supplies its own row/input data to the same two functions. Opposite finding from the eligibility-filter decision above (new function there, direct reuse here) — both were deliberate, evaluated case-by-case rather than applying one rule uniformly.
- **Three instances of an identical stale-header bug found and fixed in `build_report()`.** The SLS, Table 5.3, and Safety Glass (Table 5.1) sections all carried a header claiming the search "Starting from ULS minimum thickness Xmm" / "Starting from wind load governing thickness" — directly contradicting Section 7.6's independent-search behaviour, which the trace immediately below each header actually demonstrated (testing thicknesses below the claimed starting point). The SLS and Safety Glass instances **pre-date Pathway 2 entirely** — confirmed via `git show HEAD:app.py` (pre-dates this session) and by constructing a Pathway 1 case designed to expose it (2400×1800mm, 4-edge, Monolithic Toughened, 3.0/0.3kPa: ULS min 8mm, SLS tested from 4mm) rather than assuming the bug was new. All three now read "Independent search from thinnest available thickness (not dependent on [other check] — Section 7.6)."
- **Footer-note bug found and fixed in both pathways** (this fix was superseded by v1.14 above — the conditional wording introduced here overstated what the tool does; see v1.14 item 2). Both pathways' report footer had unconditionally stated *"Human Impact requirements have not been considered"* — false whenever Table 5.3 (Pathway 2) or Safety Glass/Table 5.1 (Pathway 1) actually ran and governed the result. This session's fix made the footer conditional, but the resulting wording was itself replaced in v1.14.
- **Fourth wording bug found and fixed:** the Mode 2 "next compliant thickness" summary line was hardcoded as *"passes ULS and SLS"*, omitting Table 5.3/Safety Glass from the list even when one of them was the sole reason the original candidate failed — meaning the one summary sentence most likely to actually be read stated the opposite of what happened. Fixed with a new `active_checks_label()` helper that derives the check list from the actual trace of what was tested at the passing candidate, so the list can't drift out of sync with reality if a further check is added later. Confirmed broken and then fixed in both pathways (Table 5.3 for Pathway 2, Safety Glass Area Check for Pathway 1).
- **Full live browser verification performed this session, closing a gap flagged across three prior sessions** (Claude Code sessions had only verified at the request/response level, no browser tool available in that environment). Using a real, connected Chrome browser: clicked through the actual landing page tile labels (confirmed "Safety Glass Check (Table 5.3)" not "Area Check", confirmed no Bushfire section, no IGU option — all matching spec); ran the 1800×1000mm/2-edge/Monolithic Toughened PASS case end-to-end, confirming the 6mm governing result and the accordion detail row (`Table 5.3 minimum thickness (2-edge): 6mm`) live in the DOM, not just via API; generated and read the actual report text via a `fetch` interceptor rather than trusting the download; ran the FAIL case (3.9mm actual, corrected low pressures to isolate Table 5.3 as the sole failing check) and confirmed the UI's "fails Table 5.3 checks" attribution and the report's next-compliant-search trace, including direct confirmation that the `uls_confirmed_passing`-shortcut fix from earlier this session behaves correctly live, not just in isolation; tested copy-as-image by clicking the actual button, then confirming via `navigator.clipboard.read()` that a genuine 61.5KB `image/png` was written to the clipboard (not inferred from absence of console errors) — `html2canvas` console trace showed clean rendering both times, including successful load of `duce_logo.png`.
- **Known gap, not closed this session:** the `NO_COMPLIANT_THICKNESS`-via-Table-5.3 path (v1.12) still has no permanent automated test — it was verified working via a temporary, reverted stock-list override, which proves the code path is correct but leaves nothing in the six test suites to catch a future regression on it, unlike the project's existing precedent of marking the analogous unreachable Mode 2 `ERROR` case as `[UNVERIFIED]` directly in test source. Flagged for a follow-up: add a real test that monkeypatches a reduced `GLASS_TYPE_THICKNESS` list for one glass type, rather than relying on this session's manual, reverted verification.
- **This closes Pathway 2 fully** — engine (v1.12), UI, report generation, and copy-as-image are all built and now live-verified, not just claimed. Section 10 item 5 updated accordingly. Pathway 3's combined bite+wind+human-impact calculation (Section 10 item 5, Section 12.9 Phase 3) is the next real piece of work — its report/copy-as-image cannot be built until that calculation exists.
- **Git commit:** `5a142ca` — Pathway 2 UI + engine wiring activation, report generation (labelled Table 5.3 section, copy-as-image reuse), the `format_trace_entry()` crash fix, all four report-wording bugs (stale search-header text ×3, footer note, hardcoded next-compliant check list) and the live browser verification pass described above, verified checkpoint.

### v1.12 — 7 July 2026 — Table 5.3 wired into Mode 1/2 (engine-only, Pathway 2 prerequisite)
- **Table 5.3 (`engine/shared/table_5_3.py`, built Phase 1B, 10/10 tests) is now genuinely called from the wind_load engine**, for the first time — previously it existed only in its own standalone test suite (per v1.11's identified-but-not-yet-built item). This is the engine-side half of Pathway 2; the UI (2-edge/3-edge selector, safety glass filter, `#pathway2-view`) is not yet built.
- **Verification against live data performed before any wiring code was written** (per this document's standing discipline, Section 0/12.9): confirmed `data/Table_5_3.csv` stores height/width in **metres**, not mm — inconsistent with the mm convention used elsewhere in the codebase, so a unit conversion is required at the call site. Confirmed the CSV's `Glass Type` values are `Annealed`, `Heat Strengthened` (space, capital S), `Toughened`, `Laminated`, and the Note 2 key `Laminated Toughened` — none of these match the engine's internal `(Monolithic/Laminated, subtype)` tuple format, requiring a new mapping dict. Confirmed `check_table_5_3()` is a single row-band lookup (height/width/joint-count → minimum required nominal thickness), not a per-thickness pass/fail test as the v1.11 entry's prose description implied — "independent search over the full thickness range" (Section 7.6 pattern) means running that row lookup once, then scanning the glass type's own `GLASS_TYPE_THICKNESSES` list ascending for the first stocked size that satisfies it, not re-running the row lookup per candidate.
- **New parameter, not a repurposing of `support_condition`:** the wind engine's `support_condition` was already collapsed to `'2-edge'` for wind-formula purposes (3-edge treated as 2-edge for wind loads, per Section 14.2/v1.6) and cannot also carry the 2-vs-3-edge joint-count distinction Table 5.3 needs. A new, independent parameter `unframed_edge_condition` (`'2-edge'` / `'3-edge'` / `None`) was added instead — default `None`, fully inert for all existing 4-edge callers.
- **`engine/wind_load/constants.py`:** added `TABLE_5_3_GLASS_TYPE_MAP` (engine tuple → CSV string), `UNFRAMED_EDGE_JOINT_COUNTS` (`{'2-edge': 2, '3-edge': 1}`, per Section 14.2), `TABLE_5_3_SAFETY_GLASS_INELIGIBLE` (Monolithic Annealed, Monolithic Heat-strengthened — same eligibility split as Table 5.1's, per Section 14.2/changelog v1.11, but as its own independent list since Table 5.3 replaces Table 5.1 entirely in this branch, it is not a shared list).
- **`engine/wind_load/checks/wind.py`:** new `check_table_5_3_thickness()` — the independent search described above, returning `COMPLIANT`/`NON_COMPLIANT`/`NOT_PERMITTED` (reusing `check_table_5_3()`'s existing status vocabulary, not a new one) plus a trace entry, per Section 6.5.
- **Wired into `check_glass_type()` (Mode 1):** Table-5.3-specific safety glass eligibility gate (separate from Table 5.1's — frontend hook not yet built, comment left marking where Pathway 2's filter needs to attach, per Section 6.2's two-place discipline); `NOT_PERMITTED` hard gate as an early return (distinct status, not a thickness penalty — per Section 14.2, Table 5.3 can reject a configuration outright regardless of thickness); result folded into governing `max(ULS, SLS, Table_5_3)` only when `unframed_edge_condition` is `'2-edge'`/`'3-edge'`, completely inert otherwise (confirmed via existing test suites showing zero behavioural change for all current 4-edge callers). **[Superseded by v1.14 — this fold-in is now additionally gated on `safety_glass_required=True`.]**
- **Wired into `check_pane_compliance()` (Mode 2) equivalently** — pane's actual nominal thickness checked against the row-band minimum, folded into overall PASS/FAIL. **[Superseded by v1.14 — same additional gate applies.]**
- **Bug found and fixed same session, before this was considered complete:** the Mode 2 next-compliant-thickness search (Section 6.6 pattern) initially re-verified ULS/SLS/Safety-Glass per candidate but not Table 5.3 — meaning it could recommend a thickness that passed ULS/SLS but still failed Table 5.3. Root cause was ordering: the Table 5.3 comparison had been placed after the Safety Glass block's early-`break` (EXTRAPOLATE path), which could accept and recommend a candidate before Table 5.3 ever ran for it. **Fixed by moving the Table 5.3 comparison ahead of the Safety Glass block**, immediately after the SLS check. Full control-flow trace performed afterward (every early-exit in the loop checked in execution order, not just the one fixed instance) confirming both remaining candidate-recommending exits (EXTRAPOLATE, full PASS) now sit strictly after the Table 5.3 comparison — no further bypass found.
- **`NO_COMPLIANT_THICKNESS` early return added** for the case where the Table 5.3 row lookup is `COMPLIANT` (a valid minimum exists) but no stocked thickness for that glass type reaches it — reuses the existing status name from Mode 1/silicone/structural-glazing rather than inventing a new one. Confirmed unreachable against today's real CSV/stock data across all six glass type/subtype combinations (analogous to the already-documented unreachable Mode 2 `ERROR` path, Section 10 item 2) — verified as a correct, tested safety net (via a temporary, reverted stock-list override), not dead code.
- **`NON_COMPLIANT` row case (width/joint-count unsatisfiable at a given height band, regardless of thickness) handled as an automatic fail for every candidate** in the next-compliant loop (`table_5_3_min_thickness is None` treated as unconditional fail), so the search correctly exhausts rather than recommending a false fix.
- **`fail_reason` disambiguation:** the per-candidate trace now reports `TABLE_5_3` for the ordinary too-thin case and a distinct value for the NON_COMPLIANT-row case (unfixable by thickness — same "unfixable" character as the true pre-loop `NOT_PERMITTED` status, but a different underlying condition, since the pre-loop status already short-circuits before this loop is ever reached and the two can never co-occur in one result). **Known naming issue, not yet resolved:** the current in-loop string reuses the literal name of the pre-loop `TABLE_5_3_NOT_PERMITTED` status. No runtime ambiguity exists today (the two conditions can't co-occur), but the collision is a latent risk if either code path changes later or someone greps for the string expecting one meaning. Flagged for a follow-up rename (e.g. to `TABLE_5_3_GATE_FAIL`) — not yet actioned, low priority, no functional impact.
- Confirmed `build_report()` (`app.py`) reads `fail_reason` opaquely via `.get()` with no exact-string matching anywhere, so the rename (when done) is safe and won't require frontend changes.
- **`make_mode1_result()`/`make_mode2_result()`** extended with new defaulted keys (`table_5_3_minimum_thickness_mm`, `table_5_3_status` [Mode 2 only — see v1.14 diagnosis], `table_5_3_min_thickness_mm`, `table_5_3_trace`) — every return path still goes through the constructors (Section 6.4); `test_structural_consistency.py` confirmed all key-sets still identical across every status.
- **`run_calculation()`/`run_compliance_check()`** got new optional, default-`None` parameters (`unframed_edge_condition`, plus a CSV/preloaded-dataframe path for Table 5.3) — every existing caller (all three original test suites, `app.py`) confirmed provably unaffected.
- **Dead code removed:** `candidate_pass` variable in `check_pane_compliance()`'s next-compliant loop, confirmed via grep as assigned once and never read anywhere in the file.
- **Hand-calculable validation case:** 1800×1000mm, 2-edge, Monolithic Toughened → CSV row `Toughened, 1.6–2.0m, width≤1.2m, 2 joints → 6mm` minimum. Toughened's stocked sizes `[4,5,6,8,...]` → 4mm/5mm fail, 6mm passes. Cross-checked against `test_table_5_3.py`'s existing test_8. Separately, a Mode 2 case (1800×1000mm, 2-edge, Monolithic Toughened, actual 3.9mm → classifies to 4mm nominal, negligible wind pressure so ULS/SLS pass at 4mm, but Table 5.3 requires 6mm) confirms the next-compliant-loop fix: search correctly rejects 5mm (passes ULS/SLS, fails Table 5.3) and lands on 6mm.
- **All six test suites green throughout, zero regressions:** `test_runner` (19/19), `test_runner_2` (16/16), `test_structural_consistency` (all key-sets identical), `test_silicone_bite` (17/17), `test_table_5_3` (10/10), `test_structural_glazing` (5/5).
- **Engine-only. No `app.py`/`index.html` changes this session** — per the project's standing discipline (Section 13.6) of validating engine logic before any UI work. Pathway 2's UI (2-edge/3-edge selector, safety glass filter matching the new Table-5.3-specific eligibility list, hiding IGU/Bushfire for this pathway) is next.
- **Git commit:** `3c2bc04331d69e1cd96dd96735b622f9ff8a48c9` — Table 5.3 wiring + next-compliant-loop fix + fail_reason disambiguation + dead code removal, verified checkpoint.

### v1.11 — 7 July 2026 — UI architecture redesigned: four-pathway landing page
- **Superseded: Section 12.8 (carry-over bridge) and Section 12.8.1 ("check in Mode 2").** Both are replaced by a combined single-page calculation model (Pathway 3, below) — no tab switching, no carry-over, no watched-fields invalidation mechanism. The v1.10 engine-selection switch (Wind Load / Silicone Bite tabs) is also superseded by the landing page. The underlying `/calculate_silicone` route and silicone form fields built in v1.10 are retained — they are re-housed inside Pathway 3 rather than discarded.
- **New UI architecture: a four-pathway landing page**, replacing the tab-switch model entirely. User lands on a page with four tiles (images to be supplied by user), each representing a distinct AS 1288 configuration from Section 14's decision tree. Selecting a tile routes to a dedicated pathway page; no mid-calculation switching between pathways.
  - **Pathway 1 — Fully Framed:** existing Mode 1 + Mode 2, unchanged, with support condition locked to 4-edge (2-edge option hidden within this pathway). Table 5.1 safety glass beta and Bushfire/BAL both remain available, as today. IGU available, as today.
  - **Pathway 2 — Partly Framed, Exposed Edges (no silicone joint):** existing Mode 1 + Mode 2, new constraints. Support condition selector limited to **2-edge or 3-edge** (a simple selector, mapping internally to joint count for Table 5.3 — 2-edge = 2 vertical butt joints, 3-edge = 1 joint, per Section 14.2). No bushfire. No IGU (deliberate scope exclusion for this tool — not an AS 1288 restriction; IGUs are structurally compatible with 2-edge support, this is a product scope decision only). **Table 5.1 does not apply in this pathway — Table 5.3 replaces it entirely** for human impact, **when the safety glass toggle is ON (v1.14) — see Section 14.7.** Safety glass toggle: ON filters to safety-glass-eligible types within Table 5.3 (Monolithic Toughened, Laminated Annealed/Heat-strengthened/Toughened); OFF allows all Table 5.3-eligible types (adds Monolithic Annealed, Monolithic Heat-strengthened) **and disables Table 5.3 entirely (v1.14).** Governing thickness = `max(ULS, SLS[, Table 5.3 result if toggle ON])`.
  - **Pathway 3 — Silicone Joints (faceted, 90°–160°):** Mode 1 only, single combined page, one Calculate action. No bushfire. No IGU (deliberate scope exclusion, same basis as Pathway 2). Wind support condition locked to 4-edge, conditional on the bite requirement being satisfiable (if `run_bite_calculation()` returns `NO_COMPLIANT_THICKNESS` for a glass type, that type fails entirely — wind/human impact are not evaluated for it). **Human impact table selection is angle-driven, decoupled from support condition** (both 90° and >90°–160° use 4-edge wind support): angle = exactly 90° → Table 5.1 (per Michael's confirmed equivalence-to-framing decision, Section 14.3); angle >90°–160° → Table 5.3 (**with its own 2-edge/3-edge joint-count selector, confirmed necessary — v1.14, Section 14.3/14.7**). Both gated on the safety glass toggle, same as Pathways 1/2 (v1.14). Safety glass toggle applies the appropriate eligibility filter for whichever table is active. Server-side, one request runs: (1) `run_bite_calculation()`, (2) Mode 1 wind search (ULS+SLS, 4-edge) per glass type, (3) the angle-appropriate human impact check per glass type (if toggle ON), (4) governing thickness per glass type = `max(bite, ULS, SLS[, human impact])`. Result screen shows all figures together, no accordion required to see which governed. **Built and live-verified as of v1.15 — see that changelog entry and Section 12.13.**
  - **Pathway 4 — Structural Glazing:** tile visible but greyed out / "coming soon." Engine (Phase 1C) is built and tested; UI not yet designed. Pending Michael's three confirmations (Scenario 3 scope, edge-polish deduction, rounding precedent — Section 12.12).
- **Build sequence for the new UI (sequenced, one Claude Code session per step, verified before proceeding):**
  1. ~~Landing page shell (four tiles + routing, Pathway 4 greyed out)~~ — **DONE, verified.** `#landing-view` built with 2×2 tile grid, three clickable tiles (Fully Framed, Partly Framed–Exposed Edges, Partly Framed–Silicone Joints) each with a 16:9 dashed-border image placeholder ready for real artwork later, fourth tile (Structural Glazing) disabled/greyed/"Coming soon", no `onclick`. Three placeholder pathway views (`#pathway1-view`/`2`/`3`) each with a heading and "Back to selection" button. Existing engine-selector + Mode 1/2 + silicone-bite markup wrapped intact in `#legacy-calculator-view`, hidden but completely untouched internally — nothing currently routes to it. `showLanding()`/`showPathway(name)` follow the same show/hide JS pattern as the existing `switchEngine()`/`switchMode()`. Manually click-tested in-browser with DevTools console open: all three tiles route correctly, disabled tile does nothing, back-to-selection returns cleanly, zero console errors, `#legacy-calculator-view` confirmed genuinely `display:none` in the DOM (not just visually obscured). `/calculate` and `/calculate_silicone` routes confirmed still responding, untouched. **Confirmed this only affects the live dev source tree — the already-built and tester-distributed `AS1288_Calculator_v1.3.exe` is a frozen artifact and is unaffected regardless of in-progress source changes, provided no new EXE is built and redistributed mid-transition.**
  2. ~~Pathway 1 (relocate existing Mode 1/2, lock to 4-edge)~~ — **DONE, verified.** Entire Mode 1/2 wind-load block relocated from `#legacy-calculator-view` into `#pathway1-view`, replacing the placeholder heading. Support-condition control (both 4-edge/2-edge buttons and container) removed entirely from this pathway's view, since nothing remains to toggle — `setSupport()` and `updateTwoEdgeAvailability()` null-guarded (`?.` optional chaining) so the underlying 4-edge/2-edge logic survives intact for pathways that still need it (Pathway 2). `state.support` still defaults to `'4-edge'` correctly with no UI control present. Regression-verified in-browser (not just via curl) against existing `test_runner.py`/`test_runner_2.py` cases run manually through the relocated UI — results matched expected. Console clean; two unrelated cosmetic 404/extension-noise items investigated and confirmed harmless (missing `favicon.ico`, a browser-extension message-channel warning per the existing Section 8.5 precedent). **Git commit:** `3c2bc04` (Pathway 1 relocation + support-condition cleanup, verified checkpoint).
  3. ~~Pathway 2 (new: 2-edge/3-edge selector, Table 5.3 wired into Mode 1/2, safety glass eligibility filter within Table 5.3)~~ — **DONE, v1.12 (engine) + v1.13 (UI/report/copy-as-image) + v1.14 (retroactive safety-glass gate fix + footer wording). Fully verified live in-browser.**
  4. ~~Pathway 3 (combined single-page bite + wind + human impact calculation)~~ — **DONE, v1.15 (engine) + v1.15 (UI/report/copy-as-image). Fully verified live in-browser.**
  5. Pathway 4 (deferred, greyed out only) — **NEXT, pending Michael's three confirmations (Section 12.12).**
- **New wiring identified as required — DONE, v1.12 (see changelog above).** Table 5.3 (`engine/shared/table_5_3.py`, built and tested in Phase 1B, 10/10 tests) is now called from the wind_load engine as a genuine Mode 1/2-integrated check, following the Section 6 patterns (eligibility filtering per 6.2, independent per-criteria search per 7.6) as anticipated below.
- **Confirmed with the user this session:** Table 5.3 CSV covers Toughened, Annealed, Heat-strengthened, and Laminated. Toughened Laminated maps to the Toughened rows; all other laminated variants map to the Laminated rows (consistent with the existing Note 2 handling already built into `check_table_5_3()`, per the v1.8 changelog). Not yet independently re-verified against the live CSV by this session — Claude Code should confirm the CSV's actual columns before wiring Pathway 2/3, per this document's standing discipline of verifying against real code/data rather than assuming from prose description.

### v1.10 — 7 July 2026 — Phase 2: Silicone bite standalone UI (superseded by v1.11's landing page — see above)
- **Built (now superseded in navigation model, retained in substance):** engine-selection switch in `index.html` ("Wind Load Calculator" / "Silicone Bite Calculator", defaulted to Wind Load). Standalone silicone bite form (Height, Width 1, Width 2, Angle [90–160 client-side validated], Corner/General using the existing N/C-rating-or-direct-kPa pattern, Butt/Mitred toggle) and result renderer. New `/calculate_silicone` route in `app.py`, independent of `/calculate` and Mode 1/2.
- **Height field confirmed unused by `run_bite_calculation()`** — B is `max(Width 1, Width 2)` only, per Section 12.5. Height was kept in the form (not dropped) since Pathway 3 (v1.11) needs it for the combined wind-load calculation.
- **All four result statuses handled distinctly:** `ANGLE_OUT_OF_RANGE`/`INVALID` as plain rejection messages; `NO_COMPLIANT_THICKNESS` states plainly no available thickness satisfies the bite requirement; `PASS` uses the existing accordion card pattern.
- **Verified manually against the dev server** (no automated frontend test suite exists — Section 8): Case A (90° butt, N3 corner, 2kPa, 600mm width) → PASS, 10mm mono/lam, exact match. 50°/170° → `ANGLE_OUT_OF_RANGE` correctly. Oversized panel/pressure → `NO_COMPLIANT_THICKNESS` correctly.
- **No changes** to `engine/wind_load/`, `engine/silicone_bite/`, `engine/shared/`, or the existing `/calculate` route/Mode 1/2 logic.
- **Superseded by v1.11 same day:** the tab-switch navigation model this session built is replaced by the four-pathway landing page. The form fields and route survive, re-housed under Pathway 3.

### v1.9 — 6 July 2026 — Phase 1C: Structural glazing engine complete
- **Phase 1C structural glazing engine built and tested.** `engine/structural_glazing/` (constants.py, formulas.py, __init__.py) implements wind bite (Appendix F: `t = 0.5 × Pz × B / 0.21`) and dead load bite (shear formula from Section 12.11) for frame-bonded (flat, angle-free) silicone glazing. Governing bite = `max(wind, dead_load)`. Table 4.1 lookup uses raw minimum actual thickness, **no thickness deduction** — silicone bonds to glass face (not cut edge), so chamfer/mitre deductions don't apply. 5/5 new tests passing; full six-suite regression green.
- **Table 4.1 refactored to `engine/shared/`.** Moved TABLE_4_1_MONOLITHIC, TABLE_4_1_LAMINATED, CHAMFER_ALLOWANCE_MM, and lookup functions (`find_min_nominal_for_bite()`, `find_min_nominal_for_usable_bite()`, `usable_bite()`) from silicone_bite into shared foundation layer. Silicone engine imports from shared; structural glazing engine imports from shared (uses raw lookup, no deductions). All four existing test suites still pass (17/17, 10/10, 19/19, 16/16) plus structural consistency check.
- **Precision policy locked in: no rounding at compliance comparison.** Exact float comparison only when checking `Table_4_1_actual >= required_bite_mm`. Rounding permitted only for display/report purposes, applied after pass/fail decision. Rationale: liability-driven — avoids edge cases where rounding converts a genuine fail into a pass (e.g. Case A laminated, 11.6095mm required vs 11.6mm actual, fails by 9.5µm — would pass if rounded to 1 decimal beforehand). Flag to Michael: check whether Duce's existing manual process rounds before comparing, as this tool will occasionally be stricter.
- **Scenario 3 (horizontals sealed only) explicitly out of scope, pending confirmation on 7/7/2026.** Currently Phase 1C supports full_perimeter and verticals_only. Scenario 3 will be scoped into Phase 1C only after Sahil confirms with Michael that Duce actually builds this configuration.
- **Edge-polish deduction for frame-bonded glazing flagged as open question, pending Michael.** Sahil proposed ~2mm deduction analogous to faceted engine's chamfer, but Claude flagged as structurally questionable — chamfer exists because silicone bonds to the cut edge (the bonding surface = thickness dimension); here silicone bonds to flat face (edge treatment is perimeter-located, not the bonding surface). Needs Michael's confirmation on mechanism and magnitude. Implemented as deferred TODO in code pending answer.
- **Three validated test cases define Phase 1C envelope:** Case A (full perimeter, Pz=2.0kPa) wind governs → 12mm mono/16mm lam; Case B (verticals only, Pz=2.0kPa) dead load governs → NO_COMPLIANT_THICKNESS both types (max available 23.5/23.4mm < required 25.63mm); Case C (full perimeter, Pz=0.5kPa) dead load governs → 10mm mono/lam. All three confirmed against hand calculations.
- **Git commits:** `d66ecede` (Table 4.1 relocation, no logic change); `0af6d56e` (Phase 1C build, engine/structural_glazing/, test suite). Table 5.3 typo fix committed earlier as `088b0fd`.
- **Updated Section 3:** folder structure now shows `engine/structural_glazing/` with three files, `engine/shared/table_4_1.py` with lookup functions.
- **Updated Section 10:** Phase 1C moved from NEXT to DONE (item 4 of V2.0 silicone sequencing).
- **Updated Section 12.11 & 12.12:** engineering logic confirmed, Michael's three answers pending (Scenario 3 scope, edge-polish deduction mechanism, rounding precedent in Duce's process).

### v1.8 — 3 July 2026 — Reverse-engineering silicone joint calculator
- **Phase 1B complete: Table 5.3 lookup module built.** `engine/shared/table_5_3.py` implements `load_table_5_3()` and `check_table_5_3()` with three-way status return (COMPLIANT / NON_COMPLIANT / NOT_PERMITTED). Handles AS 1288 Table 5.3 Note 2 (Laminated Toughened uses Toughened rows). `data/Table_5_3.csv` placed in the data folder. 10/10 tests passing in `tests/test_table_5_3.py`.
- **Updated Section 12.9 note:** module-split direction confirmed (was marked as pending confirmation, now resolved per v1.6 decision tree mapping). Phase 1A marked DONE. Phase 1C (structural glazing) to have its own build sequence.
- **Git repository linked to GitHub Desktop** for visual commit/history workflow.
- **CSV typo fix:** `Thicness Min` column header corrected to `Thickness Min` in `data/Table_5_3.csv`. **Code reference updated to match in `engine/shared/table_5_3.py` — completed and verified, 10/10 tests passing, committed as `088b0fd`.**

### v1.7 — 3 July 2026 — Reverse-engineering silicone joint calculator
- **Phase 1A silicone bite engine: core build complete.** Three files built inside `engine/silicone_bite/`: `constants.py` (Table 4.1 data, σs, 6mm floor, 2mm flat chamfer), `formulas.py` (seven pure functions plus `run_bite_calculation` entry point), `__init__.py` (exposes `run_bite_calculation`). `make_silicone_result()` added to `engine/shared/results.py`. All return paths go through `make_silicone_result()` — no raw dicts.
- **90° F-factor changed from 0.7071 to 0.5.** Supersedes the earlier "F-factor uniformly" decision from v1.5. Now uses Appendix F's value (F=0.5) at exactly 90°, Section 9's formula for >90°–160°. Change based on engineer input and AGG Technical Bulletin 1005 guidance. Updated in Section 12.3.
- **Chamfer allowance confirmed as flat 2mm** for all nominal thicknesses ≥6mm (both monolithic and laminated). Variable chamfer values below 6mm exist in Michael's spreadsheet but are unreachable by this engine due to the 6mm nominal floor. Placeholder dict replaced with single constant `CHAMFER_ALLOWANCE_MM = 2`.
- **Critical bug found and fixed in bite-to-thickness lookup.** Original `find_min_nominal_for_bite()` compared required bite against raw min_actual thickness from Table 4.1 — should compare against **usable bite** (min_actual after chamfer and mitre deduction). Bug caused under-specification of glass thickness for butt joints especially. Replaced with `find_min_nominal_for_usable_bite()` that calculates usable bite per candidate nominal thickness for the specific joint type. Old function retained as `_find_min_nominal_by_raw_thickness` for reference.
- **6mm bite floor confirmed as applied to required bite** (not to nominal thickness). If calculated bite < 6mm, it is floored to 6mm before the usable-bite lookup. This is the Dow Corning minimum contact surface requirement. Combined with the 6mm nominal thickness floor (applied after lookup), these are two separate constraints at different points in the chain.
- **Mitre angle helper added:** `calculate_mitre_angle(joint_angle)` returns `(180 - joint_angle) / 2`. Wired into `run_bite_calculation` alongside `usable_bite()`.
- **N/C pressure table decision confirmed:** silicone engine uses the existing `N_C_Tables.csv` via `engine/shared/data_loader.py` — same table as the wind load engine. No separate pressure table needed.
- **17/17 tests passing** in `tests/test_silicone_bite.py`, including two hand-calculated validated cases (Case A: 90° butt, N3 corner 2kPa, 600mm width → 10mm mono/lam; Case B: 130° mitred, same inputs → 10mm mono/lam). All existing wind load test suites unaffected.
- **Table 5.3 CSV received** from user — structure verified against AS 1288 screenshot, ready for Phase 1B implementation.
- **Git commit taken:** `e54a906` "Phase 1A complete: silicone bite engine with result constructor, 15/15 tests passing" (pre-fix), plus the lookup fix committed separately.

### v1.6 — 2 July 2026 — Reverse-engineering silicone joint calculator
- **Complete AS 1288 decision tree mapped for non-fully-framed glazing** — new Section 14 documents all branches: fully framed (4-edge), 2-edge/3-edge unframed (>160°–180°), faceted structural silicone (90°–160°), and flat structural glazing (no angle, structural silicone, no frame). Each branch specifies the applicable wind load support condition, silicone bite calculation (if any), human impact table, and bushfire applicability.
- **Human impact table split confirmed by expert**: Table 5.1 applies at exactly 90° (structural silicone treated as equivalent to framing for human impact); Table 5.3 applies for >90°–160° and all flat structural glazing cases (conservative treatment — silicone is structural for wind but treated as unframed for human impact).
- **Bushfire excluded from all non-fully-framed branches**: BAL 12.5/19/29 all require fully framed glazing — the entire non-framed decision tree is excluded. No new bushfire logic needed for any silicone/structural glazing branch.
- **3-edge confirmed as 2-edge for wind loads**: AS 1288 doesn't have a distinct 3-edge support condition; 3-edge panels are treated as 2-edge for wind load bending checks. Table 5.3's "maximum vertical butt joints" column distinguishes 3-edge (1 joint) from pure 2-edge (2 joints) for human impact.
- **Dead load / structural glazing module engineering spec confirmed complete** (Section 12.12 updated): Appendix F for wind bite, dead load shear formula, both feeding `max()`, Table 4.1 lookup, 6mm floor, Section 4 bending as 4-edge if all bites satisfied. Only remaining open question is auto-vs-toggle for dead load, deferred to UI phase.
- **Horizontal span scenario explicitly out of scope** (both horizontal edges unframed, only verticals framed).
- **Visualiser templates finalised**: ten fixed configurations verified against every decision tree branch (Section 14.1). Coverage confirmed complete including three new structural glazing templates (verticals sealed, horizontals sealed, all edges sealed). Visualiser applies to Mode 1/2 as well as silicone/structural glazing engines. To be built in a dedicated separate chat.
- **Updated Section 10 item 13** (Edge/Angle Visualiser) with full template set, coverage map, and design decisions.
- **Updated Section 12.12**: questions 1–3 and 5 resolved by this session's decision tree mapping; only question 4 (auto vs toggle) remains open, deferred to UI phase.
- **Fixed missing v1.4 changelog heading** that was lost during the v1.5 insertion.
- **Added new-chat prompt for visualiser build** to Section 0.

### v1.5 — 26 June 2026 — Resolving silicone calculator open questions and dead load scoping
- **Resolved Section 12.5 (B / governing panel dimension).** Confirmed directly with Michael (who built the original spreadsheet): the height-capping step in his Excel tool (`B = smaller of (larger width, height)`) was an error, not a deliberate design choice. **B is simply the larger of the two widths — height is irrelevant.** `calculate_governing_width()` code sample rewritten to drop the height parameter entirely. Section 12.5 reclassified from UNRESOLVED to RESOLVED.
- **Resolved Section 12.6 (monolithic minimum 6mm rounding).** Confirmed with Michael: the floor is applied to the **final nominal glass thickness, after the Table 4.1 lookup** (not to the required bite value beforehand). Rationale confirmed as seal-driven — Dow Corning structural silicone seals start at 6mm thickness. **Confirmed to apply to both monolithic and laminated glass** (previously an open sub-question). Section 12.6 reclassified from UNRESOLVED to RESOLVED.
- **New engineering content: Dead Load Bite Calculation.** A separate structural silicone formula, sourced from a structural glazing design/material considerations excerpt (source document not fully identified — see Section 12.11 for caveats), for sizing the silicone bite needed to carry the glass panel's own weight in shear, independent of wind load. Added as new Section 12.11, including the formula, worked-example verification, the physical reasoning (why dead load uses a much lower allowable stress than wind load — sustained load vs. transient load, silicone creep), and confirmation that glass density (2,500 kg/m³ / 25,000 N/m³) is consistent across annealed, toughened, heat-strengthened, and laminated glass (laminated treated as negligible-difference despite a lighter interlayer).
- **Critical scoping finding: some Duce panels have no structural frame on one or more edges**, meaning the silicone joint is sometimes the *sole* edge support for both wind load and dead load on that edge — not merely a corner-facet detail. This is the reason dead load bite needs to be in scope at all, not a hypothetical edge case. Documented in new Section 12.11.
- **New architectural direction (not yet finalised): the silicone/structural-glazing work should split into separate modules**, not one combined engine:
  - The existing faceted/corner glazing calculator (Section 9, F-factor formula, 90°–160° angles) — already scoped as `engine/silicone_bite/`, unchanged.
  - A new, separate module for flat structural glazing with no corner/angle (AS 1288 Appendix F territory, previously noted in Section 12.3 as "a possible distinct future mode") — covering wind load AND dead load bite for edges with no structural frame. User has indicated dead load calculations are used infrequently relative to wind load, but the exact UI/automatic-vs-toggle treatment is not yet decided.
  - **This split is directionally agreed but explicitly not finalised** — open sub-questions (module naming, whether the new module needs any angle input at all, whether wind + dead load both run automatically or dead load is a separate toggle, whether scope extends to flat butt-joint edges with no frame) are recorded in new Section 12.12 pending further discussion. Do not begin implementation of this third module until these are resolved.
- **New clarification on 4-edge support logic** (no spreadsheet/code impact, conceptual clarification only): confirmed that a 90°–160° facetted joint, once sized per Section 9, justifies treating that side of each panel as a structural edge (contributing toward 4-edge support per Clause 9.3.3.1's own wording). A 180° flat butt joint can never be treated as structural regardless of sizing — weatherseal only, per the AGG bulletin — so a panel with a flat joint and no frame on that edge is effectively unsupported there, not 4-edge. Added to Section 12.3 as a worked clarification.
- **Added new conceptual placeholder to Section 10: Edge/Angle Visualiser.** Not yet scoped. Two build-complexity versions discussed (simple clickable-edge diagram with colour-coded Framed/Silicone Joint labelling vs. a full geometric to-scale layout using trigonometry). Agreed as face-layer UI work, not core engine work, that should follow proof of the underlying edge-type/angle data model via plain form inputs first. **If built, it should also apply to Mode 1/2 (the wind-load engine), not just the silicone/structural-glazing modules** — support condition confirmation is useful there independently.

### v1.4 — 26 June 2026 — Redesigning app architecture for v2
- Restored full Sections 12 and 13, which were collapsed to single-paragraph stubs during the V1 refactor session (out of scope for that session, but the stubs broke the document's role as a standalone reference — any new chat reading this file would have been missing the silicone engineering detail and V2 architecture design)
- Updated Section 12.1 status: all three prerequisites (items 1–3) now marked complete
- Updated Section 12.8 heading from "Separate Mode" to "Separate Engine" for consistency with the two-engine terminology
- Updated Section 12.9 build sequence: prerequisites section now shows all items as DONE; placeholder package noted as ready to receive code
- Updated Section 13.1: marked the brain/face split as implemented (v1.3), not future
- Updated Section 13.3: corrected `wind_input.py` reference to actual location (`data_loader.py` / `get_pressures_from_nc_rating()`)
- Updated Section 13.6 sequencing: first three steps marked DONE, silicone engine marked NEXT

### v1.3 — 25 June 2026 — Unified versioning adopted (same-day follow-up)
- **Decision: "v1.3" is now the single shared version number for the tool itself, the EXE filename, and this document's own changelog, going forward.** Previously these were three separate numbering schemes (this document's changelog was independently at v1.2/v1.3; the EXE had been informally numbered v1/v2/v3 across rebuilds; the tool itself had no name of its own). From this point on, a version bump should move all three together — if the document's changelog advances, the EXE name should match, and vice versa.
- EXE rebuilt and renamed: the previous build (informally called "v3") is now `AS1288_Calculator_v1.3.exe`. Same build command as the previous rebuild, only the `--name` flag changed — no code or logic touched. Verified starting cleanly from the terminal post-rename.
- Confirmed `launcher.py` contains no hardcoded version string anywhere (its startup banner is version-agnostic), so no code changes were needed beyond the rebuild itself.
- All references to the EXE elsewhere in this document updated from the old "v3" naming to `AS1288_Calculator_v1.3.exe` (Section 3 folder structure, Section 3's `.spec` filename, Section 9 deployment status).
- This entry itself is what collapses the document's own version number and the tool's version number into the same sequence — this document is simultaneously "v1.3 of the project summary" and "the project summary as of the tool becoming v1.3."

### Engine-package refactor session (folded into v1.3 above) — 25 June 2026
- **Engine-package refactor completed and reclassified as a V1.0 update** (previously scoped as V2.0 item 3 — the user has moved it to V1.0 scope; it is no longer gated behind the silicone engine or any V2 work)
- Rewrote Section 1 to remove the "two-engine architecture is V2.0" framing — the engine/interfaces split described in old Section 13 is now built and live for the wind-load engine; the silicone engine remains the planned V2.0 occupant of the now-existing `engine/silicone_bite/` placeholder
- Rewrote Section 3 (Project Folder Structure) to describe the actual, current, built structure (`engine/shared/`, `engine/wind_load/`, `engine/wind_load/checks/`, `engine/silicone_bite/` [empty placeholder], `interfaces/flask_app/`, `tests/`) rather than a planned future one
- Added Section 3.1: refactor build log — sequence of moves, the four real bugs found and fixed during the move (missing `_fetch_k_row` and `C1_FACTORS` in formulas.py's first cut; `calculate_ar` and `get_nominal_thickness` missing from wind.py's imports; `get_pressures_from_nc_rating` never migrated out of `calculator.py` at all; the `DATA_DIR` relative-path break when `app.py` moved two folders deep instead of one; PyInstaller silently failing to bundle `engine/` because of bare-name imports behind runtime `sys.path.insert` calls, fixed by converting to proper absolute package imports)
- Added Section 3.2: Git introduced as the project's safety net (was previously absent) — `git init` performed, first commit taken before any refactor moves began, four milestone commits taken during the refactor, full history preserved including the now-deleted `src/` folder
- Updated Section 9 (Deployment): EXE successfully rebuilt from the new structure (`AS1288_Calculator_v1.3.exe`), verified working end-to-end (browser auto-opens, both direct-pressure and N/C-rating paths confirmed live), 31 July 2026 expiry date confirmed intact and carried over correctly
- Updated Section 10: refactor item (now "item 3" under V1.0, not V2.0) marked DONE; renumbered remaining V2.0 items accordingly
- Updated Section 11 (Validation Status): added `test_structural_consistency.py` as a third, now-complete test suite (Section 10 old item 2) — verifies every result-dictionary return path across both modes has an identical key set; documented one known unverified edge case (a genuine `ERROR` path in Mode 2 that may not be reachable through real inputs — confirmed non-blocking, re-confirmed deterministic via repeat runs)
- All three test suites (`test_runner.py` 19/19, `test_runner_2.py` 16/16, `test_structural_consistency.py` all green) now live in `tests/`, run against the new `engine.wind_load` package, not the old `calculator.py`
- `src/` folder (the old monolithic `calculator.py`, `app.py`, `launcher.py`, `templates/`, `static/`) deleted — fully superseded, recoverable via Git history if ever needed
- Sections 12 and 13 (silicone joint calculator engineering detail, V2 architecture design) left unchanged — out of scope for this update per explicit user instruction to treat them as periphery while focused on V1

### v1.2 — 26 June 2026 — Redesigning app architecture for v2
- Updated Section 10 item 1 status to DONE: result-dictionary constructors built and wired into all 16 return paths, 35/35 tests confirmed green
- Updated Section 11 (Validation Status) to reflect constructor completion and note item 2 (structural test) as next outstanding item

### v1.1 — 26 June 2026 — Redesigning app architecture for v2
- Rewrote Section 1 (Project Overview) to reflect two-engine architecture: wind-load and silicone-bite as separate engines, not "Mode 3" inside one calculator
- Added planned V2 package folder structure to Section 3 (engine/shared/, engine/wind_load/, engine/silicone_bite/) with dependency direction rules
- Completely restructured Section 10 (Pending Work) into three tiers: V1.0 finalisation (items 1–2), V2.0 sequenced scope (items 3–6), and conceptual/not-scheduled (items 7–11). Promoted file split to V2 prerequisite. Demoted Human Impact and record-keeping to conceptual only
- Updated Section 7.7 Safety Glass limitation reference from "flagged for V2.0" to "deferred"
- Updated Section 12.1 to reference engine-package architecture and engine/silicone_bite/ as target location
- Updated Section 12.8 point 1 from "Mode 3" to "its own engine"
- Added Section 12.8.1: simpler "check in Mode 2" cross-engine workflow (face-level pre-fill, bidirectional)
- Rewrote Section 12.9 (Build Sequence) with engine-package prerequisites and three-phase structure
- Added new Section 13: V2 Architecture Design — two-engine split, brain/face separation, shared foundation layer, cross-engine workflows, what not to build, sequencing summary
- Fixed stale cross-references (versioned data item number 5→6, removed all "Mode 3" references)
- Added changelog section and versioning rules

### v1.0 — 25 June 2026 — Baseline
- Initial comprehensive project summary covering V1.0 state, silicone joint calculator planning (Section 12), all engineering logic, validation status, and deployment status

---

## 0. How to Use This Document

Paste this entire document at the start of a new conversation with:

*"I am continuing development of the AS 1288 Glass Thickness Calculator for Duce Timber Windows and Doors. The attached document summarises the full current state of the project — architecture, every implemented rule, validation status, pending work, and V2 architecture planning (silicone joint calculator). We are now working on: [describe the new task]."*

This document is the authoritative reference for what currently exists. When adding a new compliance check or feature, look for opportunities to reuse the existing patterns described in Section 6 (Architectural Patterns) rather than inventing new ones — the codebase already has established, validated conventions for eligibility filtering, governing-thickness calculation, independent per-criteria search, and trace-building for reports.

**Standing verification discipline (added v1.14):** Claude Code's free-text summaries of what it did or found need independent spot-checking — diff the actual commit, grep for stale strings, re-run the real test suites and read raw output — before being trusted. Direct tool output has held up reliably; narrated prose summaries of that output have not always matched reality. This applies with particular force to anything touching frontend/DOM rendering, since the six pytest suites cannot exercise that at all (Section 8) — a live browser click-test with DevTools open (or, as of v1.14, Claude in Chrome driven directly from the chat) is mandatory before any UI-facing change is considered verified. Curl/HTTP-level checks remain adequate for non-DOM outputs (e.g. the downloadable TXT report) but not for on-screen rendering.

**To continue development, paste this into a new conversation under this project:**

*"I am continuing development of the AS 1288 Glass Thickness Calculator for Duce Timber Windows and Doors. The attached project summary (`AS1288_Full_Project_Summary.md`) contains the full current state of the project — currently v1.26, committed `bb433af`. Pathway 4 (structural glazing, Section 14.4/14.5) engine and UI are both built and, as of this session, the engine is GENUINELY complete against Section 14.4's own decision-tree text — the v1.24 "engine complete" declaration turned out to be premature (the Mode 1 ULS/SLS wind-bending check on the glass pane itself, specified in Section 14.4 since it was first written, was never wired in until v1.26). Five independent governing criteria now compute per subtype: silicone bite (dead load), silicone bite (wind load), ULS, SLS, and Table 5.1 (toggle-gated) — `max()` across active criteria, with `governing_criterion` naming which one won. The form now takes full ULS/SLS/N-C-rating wind input (mirrors Pathway 3), not the old single Pz field. Full eight-suite regression green (`test_runner` 19/19, `test_runner_2` 17/17, `test_structural_consistency` pass, `test_silicone_bite` 17/17, `test_table_5_3` 10/10, `test_structural_glazing` 6/6 untouched, `test_pathway3` 7/7 untouched, `test_pathway4` 11/11 — 127 individual checks, every existing test case's expected values recomputed from scratch, not assumed unchanged). A real engineering finding was made and documented, not worked around: no realistic full_perimeter geometry produces ULS/SLS governing the overall result (bite structurally dominates for this pathway's coupled geometry) — SLS can and does exceed ULS as a sub-criterion, confirmed and tested, but bite still wins overall in every case found. **Pathway 4's UI is now LIVE-BROWSER-VERIFIED** (Sahil directly, Claude in Chrome from claude.ai) — this closes the three-consecutive-session Chrome-tool gap that had been open since v1.25. None of the underlying engine figures (v1.22/v1.23/v1.24/v1.25/v1.26) have been independently hand-verified by Sahil yet — the browser check confirmed the UI renders and behaves correctly, not that the AS 1288 figures themselves are correct; treat those as still provisional until he confirms.

**One reachability finding from the live-browser pass, worth knowing before touching this pathway's UI again:** `HUMAN_IMPACT_INELIGIBLE` (returned by `make_pathway4_result()` for Monolithic Annealed/Heat-strengthened when the safety-glass toggle is ON) is **not reachable through the Pathway 4 UI at all** — `getP4GlassTypes()`/`buildP4GlassTypeCheckboxes()` filter those subtypes out of the checkbox list before submission is even possible, so the status can only be reached via a direct engine/API call (which `test_pathway4.py`'s test_7 and test_9 already exercise). This is not a bug or a regression — it's the same pre-existing Section 6.2 eligibility-filtering pattern Pathway 3 has always used (`getP3GlassTypes()` is identical), confirmed by direct comparison this session. No fix needed; just don't be surprised the status doesn't show up in a browser click-test.

**Pathway 4's UI is now fully built and verified, matching the bar Pathways 1/2/3 were held to.** This closes the four-pathway model completely — every pathway now has a complete, live-verified engine and UI. Two things remain open, both pre-existing and unrelated to this session's work: (1) independent hand-verification of the underlying AS 1288 figures by Sahil, across every pathway, not yet done; (2) copy-as-image was not explicitly re-confirmed for Pathway 4's new five-criteria rows this pass (the underlying function is unchanged and reused directly from Pathway 3, but the specific new rows weren't screenshotted). We are now working on: [describe the new task]."*

**To start the visualiser build chat**, paste this into a new conversation under this project:

*"I am continuing development of the AS 1288 Glass Thickness Calculator for Duce Timber Windows and Doors. The attached project summary (`AS1288_Full_Project_Summary.md`) contains the full current state of the project. Read Section 14 (AS 1288 Decision Tree) and Section 14.1 (Visualiser Template Coverage Map) first — they define the ten fixed visual templates we need to build, what each one represents, and how they map to the calculation decision tree. We are now building the visualiser component: an interactive panel diagram that lets the user select their glazing configuration from these ten templates, visually confirms which edges are framed vs. silicone-sealed, shows the angle between panels where applicable, and feeds the correct support condition, bite calculation requirements, and human impact table selection back to the calculation engine. This is face-layer UI work (HTML/CSS/JS in `interfaces/flask_app/templates/index.html`) — no Python engine changes are needed. The visualiser must work for both the existing Mode 1/2 wind-load engine and the upcoming silicone/structural glazing engines. Note: this is a distinct, separate scope from the four landing-page tile images (already done, v1.16) — those were single static images per pathway tile; this visualiser is a fuller interactive diagram tool."*

---

## 1. Project Overview

An internal tool for determining minimum glass thickness and checking glass compliance against wind loads under AS 1288, with additional layered checks for Safety Glass area limits and Bushfire Attack Level (BAL) requirements under AS 3959. Full Human Impact compliance (AS 1288 Section 5) is out of scope for V1.0; the Safety Glass checks are partial, clearly-flagged, user-declared previews of that future functionality. **Critically (confirmed and clarified v1.14): even when a Safety Glass check runs and governs, the tool has not performed a human impact risk assessment — the user must independently determine, under AS 1288 Section 5, whether safety glass is required for the application. The tool only applies the relevant table's thickness/area limits once the user has declared that determination via the toggle. See Section 14.7.**

The tool runs as a Flask web application, structured as a proper Python package: a self-contained calculation engine (`engine/wind_load/`) that knows nothing about Flask or HTML, and a thin web interface (`interfaces/flask_app/`) that imports from it. It has been distributed to a small internal testing group as a standalone Windows EXE (built via PyInstaller) as an interim measure. The longer-term goal is proper hosting with company-authenticated access (see Section 9).

**The engine/interfaces split (originally planned for V2.0) has been completed and is now live, reclassified as a V1.0 update.** The wind-load calculation engine lives in `engine/wind_load/`, sharing common infrastructure (CSV loading, the N/C rating lookup, the result-dictionary constructors) with `engine/shared/`. A second, independent engine (`engine/silicone_bite/`) and a third (`engine/structural_glazing/`) are built and tested (V2.0). A fourth, thin orchestration module (`engine/combined/`) is built and tested for Pathway 3 — see Section 12.13.

A separate structural glazing module — covering flat, angle-free glazing (AS 1288 Appendix F territory) and dead load bite sizing for edges with no structural frame — is built and tested (Phase 1C, v1.9), pending three confirmations from Michael before its UI is designed (Section 12.12).

A further mode, based on another existing company Excel calculator, has also been flagged as upcoming. The user is reviewing that spreadsheet independently before bringing it into a session, following the same process used for the silicone joint calculator (user explains current understanding → Claude checks logic against source/standard → open questions resolved together before any code is written). No details on this mode are available yet.

---

## 2. Technical Stack

- **Language:** Python 3.14.6
- **Core libraries:** pandas, Flask
- **Frontend:** HTML / CSS / JavaScript, no framework — vanilla JS, Tabler Icons (via CDN) for iconography
- **Packaging:** PyInstaller (`--onefile`), with a custom Duce icon
- **Image generation (client-side):** html2canvas (via CDN) — used for the "download result as image" feature; the clipboard-copy variant of this feature was removed v1.32 (Clipboard API secure-context requirement, permanently broken on the live HTTP site), download is now the sole image-export path
- **Version control:** Git
- **No database.** The application is fully stateless — every calculation is independent; nothing is persisted between sessions except what a user manually downloads as a TXT report.

---

## 3. Project Folder Structure (current, as built)

```
duce_glass_calc/
├── .git/
├── .gitignore
├── data/
│   ├── Wind_Load_Check_Tables_Full.csv      (wind load k1–k4 coefficients, in kPa)
│   ├── N_C_Tables.csv                        (N/C rating pressures, in kPa)
│   ├── Table_4_1_Minimum_Glass_Thickness.csv (actual→nominal thickness lookup)
│   └── Table_5_3.csv                         (Glass thickness and size restrictions for partially framed glazing)
├── outputs/
├── dist/
│   └── AS1288_Calculator_v1.3.exe              (latest built EXE — built from this new structure)
├── build/                                     (PyInstaller working files — not distributed)
├── duce_icon1.ico                             (EXE icon, copied to project root for the build)
├── engine/                                    ← the "brain" — zero Flask, zero UI
│   ├── __init__.py
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── data_loader.py                     load_table_data, load_nc_table,
│   │   │                                       load_nominal_thickness_table,
│   │   │                                       get_nominal_thickness,
│   │   │                                       get_pressures_from_nc_rating
│   │   ├── results.py                         make_mode1_result(), make_mode2_result(),
│   │   │                                       make_silicone_result(),
│   │   │                                       make_structural_glazing_result(),
│   │   │                                       make_pathway3_result()
│   │   ├── table_4_1.py                       TABLE_4_1_MONOLITHIC, TABLE_4_1_LAMINATED,
│   │   │                                       CHAMFER_ALLOWANCE_MM,
│   │   │                                       find_min_nominal_for_bite(),
│   │   │                                       find_min_nominal_for_usable_bite(),
│   │   │                                       usable_bite()
│   │   └── table_5_3.py                       load_table_5_3(), check_table_5_3()
│   ├── wind_load/
│   │   ├── __init__.py                        run_calculation(), run_compliance_check()
│   │   │                                       — the only two functions app.py calls
│   │   ├── constants.py                       GLASS_TYPE_THICKNESSES, C1_FACTORS, BAL_RULES,
│   │   │                                       SAFETY_GLASS_AREA_CAT1/2, SAFETY_GLASS_CATEGORY,
│   │   │                                       SAFETY_GLASS_INELIGIBLE, KPANE_SINGLE/DOUBLE/TRIPLE,
│   │   │                                       TABLE_AR_VALUES, TABLE_5_3_GLASS_TYPE_MAP,
│   │   │                                       UNFRAMED_EDGE_JOINT_COUNTS,
│   │   │                                       TABLE_5_3_SAFETY_GLASS_INELIGIBLE
│   │   ├── formulas.py                        calculate_ar, calculate_span, AR interpolation,
│   │   │                                       calculate_kpane, get_c1_factor,
│   │   │                                       calculate_uls_capacity, calculate_sls_capacity,
│   │   │                                       get_uls_k_values, get_sls_k_values,
│   │   │                                       BAL helpers, get_safety_glass_max_area
│   │   └── checks/
│   │       ├── __init__.py
│   │       └── wind.py                        check_glass_type (Mode 1),
│   │                                           check_pane_compliance (Mode 2),
│   │                                           check_table_5_3_thickness()
│   │                                           — Table 5.3 execution gated on
│   │                                           safety_glass_required AND
│   │                                           unframed_edge_condition (v1.14)
│   ├── silicone_bite/                         ← faceted/corner silicone (90°–160°), Phase 1A complete
│   │   ├── __init__.py                        exposes run_bite_calculation()
│   │   ├── constants.py                       σs, 6mm floor, 2mm chamfer (TABLE_4_1 moved to shared/)
│   │   └── formulas.py                        seven pure functions + run_bite_calculation
│   │                                           (imports Table 4.1 lookups from engine/shared/table_4_1.py)
│   ├── structural_glazing/                    ← flat structural glazing (Appendix F, dead load), Phase 1C complete
│   │   ├── __init__.py                        exposes run_structural_glazing_calculation()
│   │   ├── constants.py                       σ_dl, density, gravity constants; EDGE_POLISH_DEDUCTION_MM
│   │   │                                       = 2 (v1.18, Section 12.12 item 6) — separate named constant
│   │   │                                       from CHAMFER_ALLOWANCE_MM despite the same value, since the
│   │   │                                       physical justification differs (perimeter edge treatment
│   │   │                                       here vs. cut-edge bonding surface in the faceted engine)
│   │   └── formulas.py                        wind_bite, dead_load_bite, run_structural_glazing_calculation
│   │                                           (v1.18: Table 4.1 lookup now via the shared
│   │                                           find_min_nominal_for_usable_bite() usable-thickness search,
│   │                                           joint_type=None, chamfer_mm=EDGE_POLISH_DEDUCTION_MM —
│   │                                           replaces the old raw-thickness find_min_nominal_for_bite().
│   │                                           v1.19 BUG FIX: full_perimeter's wind_span_m was
│   │                                           max(width_m, height_m), wrongly inherited from Pathway 3's
│   │                                           unrelated Section 9 formula — AS 1288 Appendix F's B is the
│   │                                           SHORTER dimension. Fixed to min(width_m, height_m).
│   │                                           verticals_only's wind_span_m = width_m was already correct,
│   │                                           untouched.)
│   └── combined/                              ← Pathway 3 + Pathway 4 orchestration
│       ├── pathway3.py                        run_pathway3_calculation() — orchestrates silicone_bite +
│       │                                       wind_load + Table 5.1/5.3 for Pathway 3's single combined
│       │                                       calculation. Runs run_bite_calculation() once (no category
│       │                                       parameter exists on that function — it returns both
│       │                                       nominal_monolithic/nominal_laminated together), short-circuits
│       │                                       per broad category via those fields being None (not via the
│       │                                       function's overall status, which only reports
│       │                                       NO_COMPLIANT_THICKNESS when both categories fail at once).
│       │                                       Deliberately never passes unframed_edge_condition into
│       │                                       check_glass_type() — computes Table 5.1/5.3 independently
│       │                                       instead, to avoid a 4-edge+Table-5.3 combination
│       │                                       check_glass_type() was never built to keep mutually exclusive.
│       └── pathway4.py                        run_pathway4_calculation() (v1.18) — thin scenario-scope gate
│                                               over run_structural_glazing_calculation(). Only
│                                               scenario='full_perimeter' passes through to the engine;
│                                               'verticals_only' (a real, engine-capable configuration —
│                                               Case B) and 'horizontals_only' both return
│                                               CONFIGURATION_OUT_OF_SCOPE_V1 without calling the engine at
│                                               all. SUPPORTED_SCENARIOS_V1 = ('full_perimeter',) — the gate
│                                               lives here, not in the engine, which is untouched.
├── interfaces/
│   └── flask_app/
│       ├── app.py                             Flask server + report builder
│       │                                       build_report()'s human-impact footer now a single
│       │                                       clean conditional (v1.14) — see Section 14.7
│       │                                       /calculate_pathway3 route (v1.15) — calls
│       │                                       run_pathway3_calculation(), filters response to only
│       │                                       checked subtypes; build_pathway3_report() (v1.15)
│       │                                       reuses module-level format_trace_entry()/
│       │                                       active_checks_label(), promoted out of build_report()'s
│       │                                       closure for this reuse
│       ├── launcher.py                        EXE entry point (starts Flask, opens browser,
│       │                                       checks expiry — lives alongside app.py, see 3.1)
│       │                                       EXPIRY_DATE constant at line 12, comparison at
│       │                                       line 44, expiry message at line 45.
│       │                                       KNOWN BUG, QUEUED NOT YET FIXED (v1.17): line 45's
│       │                                       printed message hardcodes "(31 July 2026)" as a
│       │                                       separate string literal, NOT derived from
│       │                                       EXPIRY_DATE — bumping the constant alone will
│       │                                       silently leave the displayed message showing a
│       │                                       stale date. Fix drafted (derive via
│       │                                       EXPIRY_DATE.strftime(...)) but not yet applied.
│       ├── static/
│       │   ├── style.css                      .pathway-tile-image now includes object-fit: contain
│       │   │                                   (v1.16) — none of the four tile images are 16:9,
│       │   │                                   this scales each to fit without distortion/cropping
│       │   ├── duce_logo.png
│       │   └── Pathway_1.png / Pathway_2.png / Pathway_3.png / Pathway_4.png
│       │                                       (landing page tile artwork, added v1.16 —
│       │                                        replaces the v1.11 placeholder divs; Pathway 4's
│       │                                        tile remains disabled/"Coming soon" regardless)
│       └── templates/
│           └── index.html                     entire frontend — inputs, results, all JS
│                                               dynamic #human-impact-footer driven by
│                                               updateHumanImpactFooter() (v1.14), wired into
│                                               setSafetyGlass(), setP2SafetyGlass(),
│                                               showPathway(), showLanding()
│                                               #pathway3-view (v1.15): combined single form,
│                                               buildP3GlassTypeCheckboxes() (subset selection,
│                                               filters on P3_SG_INELIGIBLE when toggle ON),
│                                               angle-reactive #p3-edge-condition-row (hidden at
│                                               exactly 90°, shown >90°–160°), runP3Calculation()/
│                                               renderP3Results() (one card per selected subtype),
│                                               generateP3Report(). #legacy-calculator-view and
│                                               #silicone-engine-view (and their JS) removed entirely
│                                               in v1.15, fully superseded.
│                                               Pathway 3 angle-out-of-range message reworded (v1.16)
│                                               to redirect the user to Pathway 2 — client-side only,
│                                               inside runP3Calculation()'s angle<90||angle>160 guard.
├── tests/
│   ├── test_runner.py                         19 original validated test cases
│   ├── test_runner_2.py                       16 additional test cases (Bushfire, kPa, etc.)
│   ├── test_structural_consistency.py         verifies identical result-dict key sets
│   │                                           across every possible status, both modes
│   ├── test_silicone_bite.py                  17 silicone bite engine tests (Phase 1A)
│   ├── test_table_5_3.py                      10 Table 5.3 lookup tests (Phase 1B)
│   ├── test_structural_glazing.py             6 structural glazing engine tests (Phase 1C) — tests the
│   │                                           engine (run_structural_glazing_calculation()) directly,
│   │                                           unchanged in scope/structure by pathway4.py's existence.
│   │                                           Case A/C (tests 1/3) updated twice: v1.18 for
│   │                                           EDGE_POLISH_DEDUCTION_MM, then v1.19 for the wind_span_m
│   │                                           fix (Case A's governing load case flips wind→dead load).
│   │                                           Case B (test 2) unaffected by either. New Case D (test 6,
│   │                                           v1.20): same geometry, higher Pz (4.0kPa), closes the
│   │                                           wind-governs coverage gap left once Case A/C both landed
│   │                                           on dead load governing post-v1.19.
│   ├── test_pathway3.py                       7 Pathway 3 orchestration tests (v1.15) — bite governs,
│   │                                           wind governs, Table 5.1 at 90°, Table 5.3 at >90°
│   │                                           (2-edge and 3-edge variants), bite NO_COMPLIANT_THICKNESS
│   │                                           for one category only, human-impact-ineligible subtype
│   └── test_pathway4.py                       4 Pathway 4 orchestrator tests (v1.18) — full_perimeter
│                                               passes through to run_structural_glazing_calculation()
│                                               (cross-checked field-by-field against a direct engine
│                                               call); verticals_only and horizontals_only both confirmed
│                                               returning CONFIGURATION_OUT_OF_SCOPE_V1 with
│                                               nominal_monolithic/nominal_laminated still None (engine
│                                               never called); SUPPORTED_SCENARIOS_V1 locked at exactly
│                                               ('full_perimeter',)
|── AS1288_Calculator_v1.3.spec                 the ONLY currently-buildable .spec file (v1.17
│                                               verification: confirmed references files that
│                                               actually exist — interfaces\flask_app\launcher.py,
│                                               duce_icon1.3.ico)
└── [SIX STALE .spec FILES — QUEUED FOR DELETION, NOT YET REMOVED as of v1.17]
    AS1288_Calculator.spec, AS1288_Calculator_v0.1.spec, _v0.2.spec, _v1.spec, _v2.spec
    (all five reference the deleted src\ folder — will fail to build)
    AS1288_Calculator_v3.spec (references missing duce_icon1.ico — will fail to build)
```

**Important environment note:** the project folder has been relocated more than once during development. Python virtual environments (`.venv`) are NOT portable — they bake in the exact original path. If `pip`/`pyinstaller`/`pytest` commands fail with "system cannot find file specified" or "not recognized as a cmdlet" after moving the folder, delete `.venv` entirely and recreate it fresh in the current location:
```
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install flask pandas pyinstaller pytest
```
If shortcut commands like `pyinstaller`, `pip`, or `pytest` still fail to resolve after recreating, use `python -m pip` / `python -m PyInstaller` / `python -m pytest` instead, which bypasses broken launcher shortcuts. **Confirmed this session:** the six (now seven) test suites in this project are written to run directly as modules (`python -m tests.test_runner`, etc.) rather than requiring pytest at all — this is the more reliable invocation given the recurring `.venv`-portability issue.

**Dependency direction (the actual rule the structure above enforces):** a face imports from an engine; an engine never imports anything about a face; engines never import from each other. `interfaces/flask_app/app.py` imports only `run_calculation` and `run_compliance_check` from `engine.wind_load`, `run_pathway3_calculation` from `engine.combined.pathway3`, plus the CSV loaders from `engine.shared.data_loader` — nothing else inside `engine/` is touched directly from the face layer. `engine/combined/pathway3.py` (Section 12.13) is the one deliberate exception to "engines never import each other" — it is not itself an engine but a thin orchestrator that imports from multiple engines, which is why it lives in its own `combined/` package rather than inside any single engine's folder.

### 3.1 — How the Refactor Was Actually Carried Out (build log)

This refactor was done as a sequence of small, individually-verified moves, never changing logic and structure in the same step (per the safety rule first stated in the old v1.1/v1.2 versions of this document). Order of moves:

1. **`engine/shared/data_loader.py`** — the four CSV-loading functions, copied unchanged. Zero dependencies, safest possible first move.
2. **`engine/wind_load/constants.py`** and **`engine/wind_load/formulas.py`** — built together since both are dependency-free of the checks logic. Two real gaps found and fixed here: `_fetch_k_row` (an internal helper `get_uls_k_values` calls but wasn't in the original copy list) and `C1_FACTORS` (needed by `get_c1_factor` but missed from the constants import line) — both caught by attempting to actually import and run the functions, not just by visual inspection.
3. **`engine/shared/results.py`** — the two result-dictionary constructors, copied unchanged, verified by constructing a result and counting keys (21, matching the structural test's known-good count at the time).
4. **`engine/wind_load/checks/wind.py`** — `check_glass_type` and `check_pane_compliance`, the two largest functions. Required importing from constants/formulas/results.
5. **`engine/wind_load/__init__.py`** — `run_calculation` and `run_compliance_check`, the two public entry points. This was the first move tested as a genuine importable package (`from engine.wind_load import ...`), not just a loose file.
6. **All three test suites run against the new package** (temporary `*_engine_check.py` copies with only the import line changed) — 19/19, 16/16, and the full structural-consistency check all passed identically to the old `calculator.py`, proving the move preserved behaviour exactly.
7. **`interfaces/flask_app/`** — `app.py`, `static/`, `templates/` copied, imports updated. Two real gaps found here: `get_pressures_from_nc_rating` had never been migrated to the engine at all (it wasn't on the original list of functions to move, since it was overlooked, not the same kind of dependency-tracing miss as the earlier ones) — added to `engine/shared/data_loader.py`, the correct home alongside the other CSV-table lookup it most resembles; and `DATA_DIR`'s relative path (`'..', 'data'`) broke because `app.py` moved two folder levels deep (`interfaces/flask_app/`) instead of the original one (`src/`) — fixed to `'..', '..', 'data'`.
8. **`launcher.py`** — copied to sit directly alongside `app.py` in `interfaces/flask_app/` (a deliberate, lower-risk choice over moving it to the project root — the project root location would be conceptually "more correct" for a future second interface, but was judged not worth the added import complexity for a same-day deadline). No path changes needed since `app.py` is in the same folder.
9. **EXE rebuild** — the first build attempt failed at runtime (`ModuleNotFoundError: No module named 'engine'`), root-caused as PyInstaller's static analyser not knowing where `engine/` lived (`pathex=[]` in the Analysis block). Fixed by adding `--paths=.` to the build command. A second, deeper issue then surfaced: `engine/wind_load/__init__.py` and `engine/wind_load/checks/wind.py` were both using a runtime `sys.path.insert()` + bare-name-import pattern (`from formulas import ...` rather than `from engine.wind_load.formulas import ...`) — this works fine for a normal Python run but PyInstaller's static analysis cannot trace it, so those submodules were silently never bundled. Fixed properly (not patched around) by converting every such import in both files, and one in `formulas.py` itself, to full absolute package imports. This is the correct long-term fix — it also removes the need for the `sys.path.insert` hack entirely.
10. **Cleanup** — `src/` (the entire old monolithic structure) and the four temporary `*_engine_check.py` files deleted only after every above step was independently verified, and only after a Git commit captured the working pre-deletion state (see 3.2).

**Lesson reinforced repeatedly during this refactor:** a function "working" at import time does not mean it's been fully and correctly migrated — `_fetch_k_row`, `C1_FACTORS`, `calculate_ar`, `get_nominal_thickness`, and `get_pressures_from_nc_rating` were all real gaps that only surfaced when something was actually *called*, not merely imported. Verifying with a real test run (not just `import X; print('OK')`) caught every one of these before they reached an actual user.

### 3.2 — Git Introduced This Session (25 June 2026)

The project had no version control before that session. Git was set up specifically as the safety net for the refactor (in place of an earlier, rejected idea of duplicating the whole project folder into a separate `V1.1` copy — rejected because it would mean maintaining a second `.venv`, which has independently caused path-breakage problems multiple times already whenever the project folder itself was moved).

- `git init` performed in the project root.
- `.gitignore` created (excludes `.venv/`, `build/`, `__pycache__/`, `*.pyc`).
- First commit (`a22d07e`, 39 files) taken **before** any refactor moves began — the working, pre-refactor state, fully recoverable at any time even after `src/` was later deleted.
- Four commits total taken during the refactor, each at a genuine, tested milestone (engine package complete → interfaces/flask_app complete → import-style fix + EXE rebuild complete → cleanup complete). Commit messages describe what was verified at each point, not just what was moved.
- Recovering any deleted file is possible via `git show <commit>:<path> > recovered_file.py` or checking out an old commit temporarily — deleting `src/` was confirmed non-destructive before it was done.

---

## 4. Data Files (all units now kPa, see Section 7.9)

### Wind_Load_Check_Tables_Full.csv
315 rows. ULS and SLS wind load coefficients (k1–k4) per AS 1288. Columns: Wind Load Type, Glass Type, Glass sub-type 1, Nominal Thickness (mm), Support Condition, AR, k1, k2, k3, k4. AR values stored as strings without trailing zeros (`'5'` not `'5.0'`, `'1.25'` stays `'1.25'`).

### N_C_Tables.csv
20 rows. Wind classification pressures for AS 4055 (N1–N6, C1–C4 × General/Corner). Values are in kPa, not Pa.

### Table_4_1_Minimum_Glass_Thickness.csv
18 rows. Converts actual measured thickness → nominal thickness per AS 1288 Table 4.1. Uses broad glass type only (`Monolithic` or `Laminated`) — subtype irrelevant for this lookup.

### Table_5_3.csv
Glass thickness and size restrictions (minimum nominal thickness, maximum vertical butt joints, maximum panel width) per height band and glass type, for partially framed glazing. Height/width stored in metres. Glass Type values: `Annealed`, `Heat Strengthened`, `Toughened`, `Laminated`, plus the Note 2 key `Laminated Toughened` (mapped to the Toughened rows internally, per `TABLE_5_3_GLASS_TYPE_MAP`). **Confirmed (v1.15) via direct read: no Toughened or Laminated row has a joint maximum of 1** — only Annealed/Heat-Strengthened rows (height band 2–2.5m) do, and both those glass types are excluded from this table whenever safety glass is required.

### Safety Glass Area Table (AS 1288 Table 5.1)
Hardcoded in `engine/wind_load/constants.py` as `SAFETY_GLASS_AREA_CAT1` / `CAT2` dictionaries — not a CSV. Two categories: Monolithic Toughened/Toughened Laminated, and Laminated Annealed/Heat-strengthened Laminated. 4-edge only.

**Note for external/hosting-facing summaries:** the tool has four CSV reference tables in total (the three above plus Table_5_3.csv), plus several additional lookup tables (Table 5.1, the c1 factors, BAL rules, glass type/thickness lists) hardcoded directly in Python rather than loaded from files. All of it is read-only reference data — nothing is written back, and the application remains fully stateless regardless of whether a given table lives in a CSV or in code.

---

## 5. Glass Types and Available Thicknesses

```python
GLASS_TYPE_THICKNESSES = {
    ('Monolithic', 'Annealed'):           [4, 5, 6, 8, 10, 12, 15, 19, 25],  # 3mm removed — see 7.5
    ('Monolithic', 'Toughened'):          [4, 5, 6, 8, 10, 12, 15, 19, 25],
    ('Monolithic', 'Heat-strengthened'):  [3, 4, 5, 6, 8, 10, 12],
    ('Laminated',  'Annealed'):           [5, 6, 8, 10, 12, 16, 20, 24],
    ('Laminated',  'Heat-strengthened'):  [5, 6, 8, 10, 12, 16, 20, 24],
    ('Laminated',  'Toughened'):          [5, 6, 8, 10, 12, 16, 20, 24],
}
```

Laminated Heat-strengthened and Laminated Toughened use the **Laminated Annealed** rows from the wind load CSV directly (no separate rows exist for them), with pressures divided by a c1 factor per Clause 4.4.5 before lookup (see Section 7.3). Lives in `engine/wind_load/constants.py`.

---

## 6. Architectural Patterns (reuse these for new compliance checks)

These are the established conventions in the codebase. A new compliance check (e.g. a future acoustic or thermal requirement) should follow the same shape as Safety Glass and Bushfire below, rather than introducing a new pattern. All of the functions referenced below now live in `engine/wind_load/checks/wind.py`, `engine/wind_load/formulas.py`, `engine/wind_load/constants.py`, or `engine/combined/pathway3.py` — see Section 3 for exact file locations.

### 6.1 — The "governing thickness" pattern
Every check (ULS, SLS, Safety Glass, Bushfire) independently determines its own minimum thickness. The final answer is `max()` across all *active* checks — active meaning the check actually ran, not merely that its inputs were present (per v1.14, Table 5.1/5.3 only "activate" when the safety glass toggle is ON — see Section 14.7). This is deliberate — it prevents one check's result from masking another's, and avoids one check incorrectly assuming another's result as a starting point (see Section 7.6 for why independence matters). Pathway 3's orchestration (Section 12.13) follows this same pattern across bite/ULS/SLS/human-impact.

### 6.2 — Eligibility filtering pattern
Some checks restrict which glass types are even selectable (Safety Glass excludes Monolithic Annealed/Heat-strengthened; Bushfire excludes various types depending on BAL level + element type). This is implemented in **two places that must both be updated together**:
- **Backend (`engine/wind_load/checks/wind.py`):** an early-return check near the top of `check_glass_type` / `check_pane_compliance` that returns a dedicated ineligible status (`SG_INELIGIBLE`, `BAL_INELIGIBLE`) before running any calculation
- **Frontend (`interfaces/flask_app/templates/index.html`):** `buildGlassTypeCheckboxes()` (Mode 1), `buildPaneInputs()` (Mode 2), `buildP2GlassTypeCheckboxes()` (Pathway 2), and `buildP3GlassTypeCheckboxes()` (Pathway 3, v1.15) filter the dropdown/checkbox options so ineligible types never appear as selectable in the first place

**Note (confirmed live this session, v1.14):** toggling the safety glass switch resets the checkbox selection state (the eligible-types list changes, so previously-checked boxes are cleared) — this is expected behaviour given the eligibility list genuinely changes, not a bug, but worth knowing when demoing so it doesn't look broken.

**Critical lesson learned:** toggling a filter's state (e.g. `setSafetyGlass`) must explicitly call BOTH `buildGlassTypeCheckboxes()` AND `buildPaneInputs()` to refresh both modes' option lists. A bug existed where `setSafetyGlass` only refreshed Mode 1's list, leaving Mode 2's dropdown stale until the page was reloaded. Any new toggle must call all relevant rebuild functions. **As of v1.14, any new toggle must also call `updateHumanImpactFooter()`** if it affects whether a human impact check is active — see Section 14.7. **Confirmed live (v1.15) that Pathway 3's toggle correctly rebuilds `buildP3GlassTypeCheckboxes()` on both ON and OFF, restoring the full six-subtype list rather than leaving it stale.**

### 6.3 — "Applies only to specific panes" pattern (IGU-aware checks)
Bushfire only applies to the Outer/Single pane in an IGU, never Inner/Middle (AS 3959 only cares about the externally-facing surface). This is implemented via `is_bushfire_pane = pane_label in ('Outer', 'Single')` and gating both the eligibility check and the minimum-thickness check on this flag. Any future check with similar "only the exposed pane matters" logic should follow this exact pattern.

### 6.4 — Result dictionary consistency
**Every early-return path in `check_glass_type` and `check_pane_compliance` returns a dictionary with the exact same set of keys as the final success-path return.** This is enforced by `make_mode1_result()` / `make_mode2_result()` in `engine/shared/results.py` — every single return path in both functions calls one of these two constructors rather than building a raw dictionary, so a missing key is now structurally impossible. This is fully built and verified (see Section 10, Section 11) — `make_mode1_result()` guarantees 23 keys, `make_mode2_result()` guarantees 34 keys (both counts per the live `test_structural_consistency.py` output, confirmed this session), confirmed identical across every possible status. The same discipline extends to `make_silicone_result()`, `make_structural_glazing_result()`, and `make_pathway3_result()` (v1.15) — every engine follows this convention from its first version.

**Note confirmed this session (v1.14):** `make_mode1_result()` and `make_mode2_result()` are not required to carry an identical key *set* to each other — only internally consistent within each function across all its own statuses. `table_5_3_status` exists only in `make_mode2_result()`'s key set, by design — Mode 1 is a minimum-thickness search across candidates (no single-thickness pass/fail to report a status for), while Mode 2 checks one specific thickness and needs one. This was investigated and confirmed as correct, not a bug, during this session's footer diagnosis.

This same "one constructor, every path goes through it" discipline should be applied to any new engine/module from its very first version — it costs nothing extra to do it right from the start.

### 6.5 — Trace-building for reports
Every thickness tested during a search loop is recorded into a `trace` list (e.g. `uls_trace`, `sls_trace`, `sg_trace`, `next_compliant_trace`, `table_5_3_trace`) containing the k-values, formula substitution, calculated B value, and pass/fail result. This trace is NOT shown in the UI (kept clean) but IS rendered in full detail in the downloadable TXT report via `build_report()` in `interfaces/flask_app/app.py` (for Pathways 1/2) or `build_pathway3_report()` (for Pathway 3, v1.15, which reuses `format_trace_entry()`/`active_checks_label()` — promoted to module level in v1.15 specifically for this reuse). New checks should populate their own trace list following this same structure if step-by-step reporting is wanted.

### 6.6 — "Next compliant thickness" search (Mode 2 only)
When an input thickness fails one or more checks, the engine searches upward through the thickness list for the first thickness that passes ALL *active* checks simultaneously (not just the one that originally failed). This search is optimised: once a candidate thickness is confirmed to pass ULS, every thicker candidate skips re-checking ULS entirely (allowable span only increases with thickness, so re-verification is provably redundant) — see `uls_confirmed_passing` flag in `check_pane_compliance`.

---

## 7. Engineering Logic — Full Detail (Main AS 1288 Calculator)

### 7.1 — Calculation Modes
- **Mode 1 (Minimum Thickness Finder):** searches for the minimum compliant thickness for selected glass type(s).
- **Mode 2 (Compliance Checker):** checks whether a user-specified actual thickness complies; converts actual→nominal via Table 4.1 first.

### 7.2 — Aspect Ratio and Linear Interpolation (Clause 4.4.3)
**A major correctness fix, made following direct correspondence with an industry expert.**

Previous (incorrect) behaviour: AR was rounded UP to the next available table value (1, 1.25, 1.5, 1.75, 2, 2.5, 3, 5), and that row's k-values were used directly.

**Correct behaviour, now implemented:** AS 1288 Clause 4.4.3 permits — and the tool now performs — **linear interpolation** of k1, k2, k3, k4 individually between the two bracketing table AR values, proportional to where the actual AR sits between them. Verified against a real worked example from an AS 1288 expert (AR=1.4, between 1.25 and 1.5 rows) — the interpolated values reproduced the expert's figures to the decimal place.

- `get_ar_interpolation_bounds(actual_ar)` returns either `{'exact': True, 'ar': value}` (AR lands exactly on a table value, or AR ≥ 5.0 — in which case the AR=5 row is used directly, no interpolation) or `{'exact': False, 'ar_low': x, 'ar_high': y, 'fraction': f}`.
- `interpolate_k_values(k_low, k_high, fraction)` performs the blend.
- `get_uls_k_values` / `get_sls_k_values` take an `ar_bounds` parameter and internally fetch one row (exact match) or two rows + interpolate.
- **AR ≥ 5.0 rule:** there is NO upper out-of-scope cutoff. AR is capped at the AR=5 row regardless of how elongated the panel is.
- 2-edge support uses `AR = 'Independent'` always — no interpolation ever applies there.

### 7.3 — c1 Factor for Laminated Variants (Clause 4.4.5)
```python
C1_FACTORS = {
    ('Laminated', 'Annealed'):          1.0,
    ('Laminated', 'Heat-strengthened'): 1.6,
    ('Laminated', 'Toughened'):         2.5,
}
```
Effective pressure = `(k_pane × applied_pressure) / c1`. Monolithic glass is unaffected (c1 = 1.0 implicitly). Laminated Heat-strengthened/Toughened use Laminated Annealed's k-values from the CSV (no separate rows exist).

### 7.4 — IGU Load Sharing (k_pane)
**Mode 1 (equal-thickness assumption):** fixed constants — Single 1.0, Double 0.625 (`1.25/2`), Triple 0.4167 (`1.25/3`).
**Mode 2 (actual thicknesses):** `k_pane = min(1.25 × t_pane³ / Σ(ti³), 1.0)` — calculated per pane using all actual thicknesses submitted.

### 7.5 — Monolithic Annealed Minimum Thickness
**3mm Monolithic Annealed has been entirely removed** (a deliberate standards-driven decision, not a bug) — the glass type now starts at 4mm nominal in `GLASS_TYPE_THICKNESSES`. In Mode 2, if an actual thickness classifies as 3mm nominal for Monolithic Annealed specifically, the engine returns `status: 'INVALID'` with message *"Minimum thickness allowed by tool: 4mm..."* rather than proceeding.

This same 4mm-floor policy has since been confirmed as a deliberate, company-wide Duce decision — not specific to this calculator — and the same floor is being carried into the Silicone Joint Calculator's monolithic lookup table (Section 12.4).

A related, more general check also exists in Mode 2: if a classified nominal thickness is below the minimum thickness actually offered for that glass type (e.g. 3mm classifies fine under Table 4.1, but Monolithic Toughened's thickness list starts at 4mm), the engine returns `status: 'INVALID'` with the message *"No DTS solution for glass selection of [glass type] of thickness [X]mm available."* This check runs before the wind-load table lookup is ever attempted, which means the genuine `ERROR` status (wind-load table row missing) is harder to trigger than it might first appear — see Section 11 for the one known unverified case this produced in the structural test.

### 7.6 — Independent Minimum Thickness Per Criteria
**A major behavioural change.** Previously, SLS search started from the ULS minimum thickness (assuming SLS would never need a thinner glass), and Safety Glass search started from the ULS/SLS governing thickness. **This was changed: ULS, SLS, and Safety Glass each now search their OWN full thickness range independently** from the thinnest available option, and report their own true minimum. The final governing thickness is still `max()` of all three — this part hasn't changed. This surfaces cases where, e.g., SLS's true minimum is genuinely thinner than ULS's (previously masked since SLS never got the chance to check those thinner thicknesses).

### 7.7 — Safety Glass Area Check (Beta) — AS 1288 Table 5.1
- User-declared toggle only — does not assess whether required. **See Section 14.7 for the confirmed cross-pathway rule and footer wording (v1.14) — this section's gating behaviour is unchanged, only the footer messaging and the fact that Pathway 2/3's Table 5.3 now follows the identical gating rule are new.**
- **4-edge only.** Toggling it ON hides the 2-edge support option (shared logic with Bushfire — see `updateTwoEdgeAvailability()`, which hides 2-edge if EITHER Safety Glass OR Bushfire is on).
- Eligible: Monolithic Toughened, Laminated Annealed, Laminated Heat-strengthened, Laminated Toughened.
- Ineligible (returns `SG_INELIGIBLE`): Monolithic Annealed, Monolithic Heat-strengthened.
- Sequence: independent search (see 7.6) → governs if higher than ULS/SLS.
- Known limitation (deferred, not part of V2.0): **AS 1288 Clause 5.22** — for IGUs with human impact possible from both sides, both panes must comply and area limits get ×1.5; for one-side-accessible, only the accessible pane needs to comply at the standard limit. Current beta applies standard limits uniformly with no IGU-side-access distinction.

### 7.8 — Bushfire (BAL) Filter (Beta) — AS 3959
Six distinct rules — Window/Door × BAL-12.5/19/29 — each independently specifying eligible glass types and a minimum thickness:

| BAL | Window | Door |
|---|---|---|
| 12.5 | No restriction; conditional note (≤400mm from ground/structure within 18° → safety glass, 4mm min) | Safety-Glass-eligible types only, 4mm min |
| 19 | No restriction; conditional note (≤400mm condition → Mono Toughened, 5mm min) | Mono Toughened only, 5mm min |
| 29 | Mono Toughened only, 5mm min | Mono Toughened only, 6mm min |

- Implemented via `BAL_RULES` dict keyed `(bal_level, element_type)`, `get_bal_rule()`, `check_bal_eligibility()`, `get_bal_min_thickness()`.
- **Only applies to the Outer/Single pane** in Mode 2 (see Section 6.3) — Mode 1's equal-thickness assumption means this distinction is less visible there but the same `bal_level`/`bal_element_type` fields are only populated for the relevant pane.
- Toggling Bushfire ON hides 2-edge (same shared function as Safety Glass — see 7.7).
- Ineligible glass types are filtered from BOTH the Mode 1 checkbox list and Mode 2's Outer/Single pane dropdown (Inner/Middle panes are NOT filtered by Bushfire, only by Safety Glass if that's separately on).
- Conditional notes (the "if within 400mm..." text) are surfaced as a persistent on-screen warning, never enforced by the engine — the tool cannot verify site geometry.

### 7.9 — Pressure Units: Pa → kPa Conversion
**All wind pressures throughout the entire system are now in kPa, not Pa.** This was a deliberate, carefully-sequenced change:
1. `N_C_Tables.csv` values divided by 1000 (now store kPa directly)
2. `calculate_uls_capacity()` / `calculate_sls_capacity()` no longer divide by 1000 internally — both now expect kPa-scale input directly (parameter renamed `wind_pressure_uls_kpa`/`wind_pressure_sls_kpa` for clarity)
3. Six trace-building locations across the engine that built `'pressure_kpa': round(effective_uls / 1000, 4)` had the erroneous `/1000` removed (since the value is already kPa)
4. `index.html`: input field labels/tooltips/placeholders changed from Pa to kPa; `windLoadLabel` (feeding both result cards and copy-snippet) updated; Mode 2 "Effective ULS/SLS" display changed from `.toFixed(0)` (fine for Pa-scale numbers) to `.toFixed(4)` (needed for kPa-scale precision)
5. `app.py`'s `build_report()` input summary and "Applied pressures" block updated to kPa, removing a double-division bug that briefly existed
6. Both test runner files' pressure-resolution logic now divides legacy Pa-scale test case literals by 1000 before passing to the engine — **the test case data itself was NOT rewritten**, only the conversion point, to avoid touching 35+ test case dictionaries

**Side effect discovered and fixed:** extremely low pressures (e.g. 0.1 kPa) can cause `(pressure + k2)` to land at exactly zero, and `0 ** negative_exponent` returns Python's `inf` (infinity) rather than `NaN` — a different invalid-value pattern than the negative-base `NaN` case originally guarded against. Both `calculate_uls_capacity` and `calculate_sls_capacity` check for BOTH `NaN` and `inf`/`-inf` and raise a descriptive `ValueError` with the exact inputs that caused it. `app.py` catches this specific `ValueError` and returns `error_type: 'OUT_OF_SCOPE_CALCULATION'`; the frontend shows a clean message instead of a generic connection error. **Encountered live this session (v1.14):** a Pathway 1 test run at ULS 0.1kPa/SLS 0.05kPa hit exactly this guard and correctly displayed the clean out-of-scope message rather than crashing — confirms this handling is still working correctly.

---

## 8. Frontend Details Worth Knowing

### 8.1 — Result card structure
Black-green (PASS) / black-red (FAIL) themed cards. Collapsed accordion by default — click the footer to expand ULS/SLS/Safety Glass/Bushfire detail rows. `hasMode2Detail` flag controls whether a card is expandable at all (INVALID/ERROR/SG_INELIGIBLE/BAL_INELIGIBLE cards have no detail to show, so render as non-clickable). The FAIL footer reads as a single sentence: *"**Xmm GlassType** fails [checks] checks. Use **Ymm GlassType** instead."* with the failing thickness in red and the recommended one in green, both inline-emphasised via `<strong style="color:...">`. **Pathway 3's result cards (v1.15) follow the same pattern, one per selected subtype** — cards with status `BITE_NO_COMPLIANT_THICKNESS`, `HUMAN_IMPACT_INELIGIBLE`, or `HUMAN_IMPACT_NOT_PERMITTED` render non-clickable, same convention.

### 8.2 — Copy-as-image
Click the download icon beside any result footer to generate a separate, compact snapshot (NOT a screenshot of the visible card — a purpose-built hidden template via `buildSnapshotHTML()`) and save it as a PNG via `html2canvas` + `generateSnapshotCanvas()`/`downloadSnapshotAsImage()`. Includes the Duce logo (loaded from `/static/duce_logo.png`), all inputs, every active check's result, and the governing/recommended thickness emphasised. Works for both PASS and FAIL cards in both modes, and (v1.15) for Pathway 3's per-subtype cards, reusing the same two functions directly with no changes needed. **(v1.32: this used to also offer a copy-to-clipboard variant via `copySnapshotAsImage()`/`navigator.clipboard.write` — removed entirely, since it depended on the Clipboard API's secure-context requirement and was permanently broken on the live HTTP site. Download, which has no such dependency, is now the only image-export option.)**

### 8.3 — Icon font
Uses Tabler Icons via CDN: `https://cdnjs.cloudflare.com/ajax/libs/tabler-icons/3.35.0/tabler-icons.min.css`. **Note:** an earlier, incorrect URL (`.../2.47.0/iconfont/tabler-icons.min.css`) silently 404'd for an extended period without any visible error — icons just rendered as blank space. If icons ever stop appearing, check this exact URL first before assuming a CSS/caching issue.

### 8.4 — Known browser-cache gotcha
Code changes that were 100% correctly saved to disk did not appear in the browser despite hard refreshes (Ctrl+F5). The reliable fix: fully stop the Flask server (Ctrl+C), restart it, AND open a genuinely new browser tab (not reusing an old one). If something seems broken after a code change, do this full restart sequence before debugging further — verify the live DOM via browser DevTools (Elements tab, inspect the actual element) against the source file content before assuming a logic bug. **Note (v1.16):** stale Flask dev-server processes left running from earlier sessions (multiple `python.exe` bound to port 5000) can also cause connection issues or unpredictable behaviour when a new instance is started — check for and kill orphaned processes before assuming a code-level fault if the dev server seems unreachable or is behaving inconsistently.

### 8.5 — Browser extension false positives
A generic "Could not connect to the calculation server" error, or console exceptions reading *"A listener indicated an asynchronous response by returning true, but the message channel closed before a response was received"*, can be caused entirely by an unrelated browser extension (password manager, ad blocker, etc.) interfering with `fetch()` response handling — NOT a real server failure. Diagnostic: check the Network tab for the actual request's status code. If it shows `200`, the server succeeded and the error is a frontend display issue. Test in an Incognito window (disables extensions) to confirm. **Re-confirmed multiple sessions since**, including during Pathway 3's live verification (v1.15) and its live browser image/wording verification (v1.16) — this exact console pattern recurs on a background timer unrelated to any app action, and should not be investigated further once recognised.

### 8.6 — Browser click-testing via Claude in Chrome (added v1.14)
Live click-testing can be performed directly from a claude.ai chat using the Claude in Chrome browser extension, independent of Claude Code. Useful notes, accumulated across sessions:
- The extension operates its own Chrome tab group; `tabs_context_mcp` must be called once before any navigation.
- Element references (`ref_NNN`) returned by `find` go stale after any DOM re-render (e.g. a toggle click that changes which glass types are eligible) — re-`find` the element rather than reusing a stale ref, or the click will fail or silently hit the wrong element.
- The `find` tool's natural-language matching is not perfectly reliable when multiple pathway forms coexist in the DOM (all pathway forms exist simultaneously, hidden via `display:none` per the v1.11 architecture) — it can occasionally match a hidden element in the wrong pathway's form. When precision matters (e.g. confirming which pathway is actually visible), query the DOM directly via `javascript_tool` (`getComputedStyle(el).display`, `document.getElementById(...)`) rather than trusting `find`'s pathway attribution.
- Calling exposed page-global functions directly via `javascript_tool` (e.g. `window.showPathway(...)`) is riskier than clicking the actual UI element — an unexpected argument shape can leave the app in a broken all-hidden state with no visible error. Prefer clicking real elements; use direct JS calls only for read-only inspection (checking active toggle states, intercepting fetch calls to capture request/response payloads), not for driving navigation. **Clicking a real button element directly via `element.click()` in `javascript_tool` (rather than coordinate-based clicking) has proven reliable across sessions (v1.15/v1.16) for checkboxes and toggle buttons specifically** — distinct from calling internal page-global functions, which remains discouraged.
- Network request bodies/response bodies are not exposed by `read_network_requests` (URL/method/status only) — to inspect actual payloads, monkeypatch `window.fetch` before triggering the action, capture `args[1].body` and the cloned response text, then read `window.__capturedCalc` (or similar) afterward. **This pattern was reused successfully in v1.15 to capture Pathway 3's generated report text via a `fetch` interceptor.**
- **New (v1.16): `Page.captureScreenshot` can intermittently time out** (observed twice in one session) even while the page itself remains fully responsive to JS execution (`document.readyState`, DOM queries, clicks all continued working normally). Treat this as a possible transient CDP/tooling issue rather than a frozen page — fall back to JS-based DOM inspection (`getComputedStyle`, `textContent`, element attribute checks) rather than assuming the app has broken, and only conclude the app itself is unreachable if JS execution also fails (e.g. `document.readyState` hangs, or the page shows `ERR_CONNECTION_REFUSED` in its own body text) — the latter is a genuine "server not running" signal, distinct from a screenshot-only timeout.

---

## 9. Deployment / Hosting Status

**Current state:** distributed as a standalone EXE (PyInstaller, `--onefile`), now rebuilt from the new `engine/` + `interfaces/flask_app/` structure as `AS1288_Calculator_v1.3.exe`, to a small internal test group via a shared **OneDrive folder link** (confirmed v1.17 — a folder, not a direct file link, meaning testers browse to whatever's currently inside; renaming or replacing the EXE file does not break the shared link). Verified working end-to-end from the packaged EXE itself (not just the dev server) — browser auto-opens, both direct-pressure and N/C-rating calculation paths confirmed live. Has a hardcoded expiry date of **31 July 2026** in `launcher.py` (`EXPIRY_DATE`) — confirmed intact and unchanged through the refactor. Intentionally kept as a safeguard against the EXE being used indefinitely outside the test window / shared externally, pending a proper hosted solution; the user has also indicated this expiry now doubles as a practical limit on insider-copying exposure while a proper hosting/access-control solution is pending.

**New direction, decided v1.17: monthly EXE rebuild cadence with kill-switch expiry, for the remainder of the year.** `EXPIRY_DATE` will be bumped roughly monthly. **Two real bugs found ahead of this cadence, queued but NOT yet fixed** (see v1.17 changelog and Section 3's `launcher.py` annotation): the expiry message's displayed date is a separate hardcoded string, not derived from `EXPIRY_DATE` — will show stale if not fixed before the next bump; and six of seven `.spec` files in the project root are broken/stale (reference a deleted `src/` folder or a missing icon), leaving only `AS1288_Calculator_v1.3.spec` as currently buildable. **Also decided, not yet executed:** consolidate Pathways 1-3 (and Pathway 4, if its confirmations land in time) into a single V2 EXE release, expiry extended to end of August, rather than shipping several smaller incremental releases — accepting the tradeoff that a defect in the consolidated build surfaces for every tester at once, which raises the bar for pre-release verification (full seven-suite regression + complete live click-through of every included pathway, not a subset). One still-open housekeeping question: whether to delete superseded EXE versions from the OneDrive folder as new ones are added, or leave them accumulating (ambiguity-of-which-file risk if left unresolved) — not yet decided.

**Ruled out / blocked paths (confirmed via direct investigation):**
- **RemoteApp publishing on DUCERDG01:** confirmed NOT configured (no RD Connection Broker in the server pool), and explicitly NOT to be attempted, per IT: DUCERDG01 is the RDS *broker* only, not a host server, and is meant to be locked down to IT. Setting up a full RDS Deployment from scratch was judged too large and risky a change to existing services (Goldmine, Office) to attempt on a tight timeline.
- **Running anything persistent on DUCERDG01:** explicitly told not to by IT. The actual session host servers are `DUCERDS01/02/03`, which reboot nightly — any hosting solution must auto-restart after reboot, not rely on a manually-started process.
- **Self-service Azure AD / Microsoft 365 SSO setup:** confirmed (by direct attempt in the Azure portal) that the user does NOT have App Registration permissions in Duce's tenant — this requires a Global Administrator or Application Administrator, i.e. IT must perform this step. Once IT provides a Client ID, Tenant ID, and Client Secret, the SSO login code itself (using Python's `msal` library) is buildable without further IT involvement.

**Current direction:** IT has offered their developer contact (Jamal) to assist specifically with hosting/deployment (NOT redevelopment — the calculation engine is complete, tested, and not in need of rebuilding). Jamal has experience deploying similar tools on Azure for Duce previously. Jamal has requested a demo, the Python version, and confirmation of database usage — all answered (no database exists; engine fully stateless; four CSV reference tables plus some hardcoded lookup constants only; built with AI-assisted development with calculation logic independently validated against the standard).

**New this session (v1.16 timeframe): IT management company (SBS)'s Azure/M365-SSO hosting quote came back higher than expected.** The user is now separately consulting an additional contact (Brent) to discuss alternative hosting approaches given the quote, providing background on the tool's architecture and the SBS conversation to date. Outcome of that discussion not yet known — to be added to this section once resolved. Note: the relationship between this new contact and the existing Jamal/SBS engagement was not fully clarified as of this session — clarify and correct this section once known.

**Explicit constraint from the user:** does not want to become the long-term identity/access manager for this tool (i.e. avoid personally maintaining a shared password list indefinitely) — SSO tied to existing Duce Microsoft accounts is the preferred end state specifically so access management stays with whoever already manages staff accounts. A future record-keeping system (Section 10, conceptual item) was mentioned to Jamal only as a loose, non-committed possibility 6–12 months out, explicitly not a current requirement. **A separate, later possibility (raised this session, not yet scoped or committed) is that future tools may require more substantial database storage for sensitive company information such as pricing data — this is unrelated to the current tool's stateless architecture and is not a near-term requirement.**

---

## 10. Pending / Required Work — Sequenced

### V1.0 — complete (see prior versions for detail; items 1–3 all DONE)

### V2.0 — Engine Build Complete, UI/Integration Pending

4. ~~**Silicone Joint Calculator + Structural Glazing engines**~~ — **DONE.** Phase 1A (faceted/corner silicone), Phase 1B (Table 5.3 lookup), Phase 1C (flat structural glazing, Appendix F + dead load) all built and tested. ~~Three questions pending Michael confirmation~~ — **all three confirmed and implemented, v1.18** (edge-polish deduction, rounding discrepancy documented, Pathway 4 scenario scope gate). Section 12.12 fully resolved.
5. **Face-layer wiring.** The four-pathway landing page replaced the old tab-switch and carry-over models (v1.11). **Pathway 1, Pathway 2, and Pathway 3 are all fully DONE** — engine, UI, report generation, and copy-as-image, all live-verified in-browser, including the v1.14 retroactive gate fix and footer wording overhaul for Pathway 2, and Pathway 3's full orchestration engine and UI build (v1.15). **Pathway 4 (structural glazing) now has its engine + orchestrator built (v1.18, `engine/combined/pathway4.py`) but still has no UI — this is the only remaining item in this list.** All four landing-page tiles now show real artwork (v1.16); Pathway 4's tile remains disabled until its UI is built.
6. **Versioned standards data architecture** — unchanged from prior versions, can be done in parallel with item 5.

### Queued, Drafted, Not Yet Executed (added v1.17)

7. **Two real bugs found ahead of the monthly EXE cadence, fixes drafted, NOT yet run:** `launcher.py`'s expiry message hardcodes its displayed date separately from `EXPIRY_DATE` (needs deriving via `.strftime()` instead); six of seven `.spec` files are stale/broken and should be deleted, keeping only `AS1288_Calculator_v1.3.spec`. See v1.17 changelog for full detail and the prepared Claude Code prompt.
8. **Consolidated V2 EXE release** — bundle Pathways 1-3 (and 4, if ready) into a single release, expiry extended to end of August, replacing incremental per-feature releases going forward. Not yet scheduled; pending Pathway 4's UI or an explicit decision to ship without it (its engine/orchestrator are now done, v1.18). Requires a full eight-suite regression + complete live click-through of every included pathway before release, per the standing verification discipline (Section 0).
9. **Minor cleanup backlog, explicitly deferred, available whenever wanted:** Table 5.3's `fail_reason` naming collision (Section 12.9/v1.12); the still-missing permanent regression test for the Table-5.3-driven `NO_COMPLIANT_THICKNESS` path (flagged since v1.13); an in-app version/expiry indicator for testers; the stray `favicon.ico` 404. None of these are time-sensitive.

### Conceptual / Not Scheduled

The following items have been discussed but are explicitly **not committed to any version**. They are conceptual only and should not influence V2 architecture or scheduling. Revisit only in a dedicated future conversation if/when a concrete need arises.

10. **Full Human Impact Engine** replacing the beta Safety Glass check — proper AS 1288 Section 5 compliance, including the Clause 5.22 IGU ×1.5 area factor (see 7.7). May land in V3 or later, or may be re-scoped entirely. The beta Safety Glass check stays as-is for the foreseeable future.
11. **Client → Job → Stage → Proposal → Opening record-keeping backbone** — explored in detail in conversation but NOT committed to. The user explicitly does not want this built as a calculator-specific feature, but as shared infrastructure that multiple future tools would plug into. A client can have multiple jobs; a job can have multiple stages; each stage has its own independent chain of superseding proposal revisions (only the latest revision per stage is active/editable; creating a new revision auto-copies the previous one forward). Recommended storage if ever built: SQLite, not flat JSON files, specifically for fast cross-cutting queries. Explicitly NOT scheduled — user said "hold for now." Mentioned only briefly and loosely to the prospective hosting developer (Jamal) as a 6–12-month-out possibility, not a current requirement. **A related, separately-raised idea (v1.16 timeframe): future tools may need more substantial database storage for sensitive data like pricing — also not scheduled, mentioned only in passing during hosting discussions.**
12. **Third calculation mode (TBD)** — based on another existing company Excel calculator. User is reviewing it independently before bringing it to a session. No details yet.
13. **Excel add-in** — discussed and explicitly de-prioritised once the complexity was understood. Not actively planned; only worth revisiting as a thin layer over the existing API if a concrete need arises.
14. **Client → Job → Stage → Proposal → Opening record-keeping backbone** (moved from item 8) — explored in detail in conversation but NOT committed to. The user explicitly does not want this built as a calculator-specific feature, but as shared infrastructure that multiple future tools would plug into. Explicitly NOT scheduled — user said "hold for now."
15. **Edge/Angle Visualiser (new, conceptual, not yet scoped)** — an interactive diagram allowing the user to mark each edge of a glass panel as "Framed" or "Silicone Joint," and label the angle between adjacent panels, so the support condition and silicone engineering inputs can be visually confirmed rather than only entered as form fields. Two versions discussed, differing significantly in build effort: a **simple version** (a static shape with clickable, colour-coded edges and labelled corner angles — comparable in complexity to existing frontend widgets like the IGU pane diagrams, estimated a few hours of work), and a **full geometric version** (panels drawn to scale and laid out using real trigonometry based on width and inter-panel angles, forming an actual faceted shape the user can see from above, with validation that entered angles form a physically sensible configuration — a multi-day feature). Agreed as **face-layer UI work, not core engine work** — it doesn't block any engine's calculation logic, which needs the same edge-type/angle data regardless of whether it's entered via form fields or a visual diagram. Per the project's existing discipline (validate the engine before building UI), this should only be built after the underlying edge-type/angle data model is proven via plain form inputs. **If built, it should also apply to Mode 1/2 (the wind-load engine), not just the silicone/structural-glazing modules** — support condition confirmation is a Mode 1/2 concern too, independent of whether the silicone calculator is involved at all. **Updated in v1.6:** the simple fixed-template approach has been chosen — ten configurations verified against the full decision tree (see Section 14.1 for the complete coverage map). Templates use user-provided visual designs (PDF), not dynamically-resizing geometry. **To be built in a dedicated separate chat under this project** — see Section 0 for the ready-to-paste prompt. **Explicitly distinct from the four landing-page tile images completed in v1.16** — those are single static images per pathway tile on the landing page; this visualiser is a fuller interactive diagram tool used within a pathway's own form, not yet started.

---

## 11. Validation Status

**Confirmed v1.20, exact counts from raw test output — not a summary:**
- `test_runner.py`: 19/19 passing
- `test_runner_2.py`: 16/16 passing
- `test_structural_consistency.py`: Mode 1 result dict = 23 keys, Mode 2 result dict = 34 keys, both confirmed identical across every status within each mode (Mode 1 and Mode 2 key sets are NOT required to match each other — see Section 6.4 note). One Mode 2 `[UNVERIFIED]` case remains (genuine `ERROR` path possibly unreachable via real inputs — non-blocking, unchanged from prior versions).
- `test_silicone_bite.py`: 17/17 passing
- `test_table_5_3.py`: 10/10 passing
- `test_structural_glazing.py`: 6/6 passing — tests 1 (Case A) and 3 (Case C) updated twice: v1.18 for `EDGE_POLISH_DEDUCTION_MM`, then v1.19 for the `wind_span_m` fix (which also flipped Case A's governing load case from wind to dead load); test 2 (Case B, `verticals_only`) untouched by either change. New test 6 (Case D, v1.20) closes the `full_perimeter` wind-governs coverage gap left once Case A and Case C both landed on dead load governing post-v1.19 — same geometry, `pz_kpa=4.0`, wind governs (11.6095mm > 8.5417mm dead load), `nominal_monolithic=15mm`/`nominal_laminated=16mm`. Tests the engine directly, unaffected by `pathway4.py`'s existence.
- `test_pathway3.py`: 7/7 passing (added v1.15) — bite governs, wind governs, Table 5.1 governs at exactly 90°, Table 5.3 governs at >90°–160° (both 2-edge and 3-edge selector variants), bite `NO_COMPLIANT_THICKNESS` for one broad category only (other category's subtypes confirmed unaffected), a human-impact-ineligible subtype (confirmed returning bite/wind results with `human_impact_thickness_mm=None`, not a crash or silent skip)
- `test_pathway4.py`: 7/7 passing (4/4 added v1.18, +3 in v1.22) — test 1 rewritten (v1.22) for the new per-subtype return shape (cross-checked against a direct engine call, toggle defaulting OFF); tests 2-4 (scope gate) unchanged, since the `CONFIGURATION_OUT_OF_SCOPE_V1` branch's shape didn't change; new test 5 (toggle OFF — Table 5.1 not checked, `governing_thickness_mm == bite_thickness_mm` for all six subtypes); new test 6 (toggle ON, passing — Monolithic Toughened/Laminated Annealed, genuine FAIL-then-PASS Table 5.1 trace, bite still governs); new test 7 (toggle ON, `HUMAN_IMPACT_INELIGIBLE` — Monolithic Annealed/Heat-strengthened, confirmed non-crashing fallthrough, `governing_thickness_mm` still equals bite).

**Full regression: 82 test-function checks + 1 structural consistency check, all green** (as of v1.22's Table 5.1 wiring — eight suites total, up from 79 in v1.20; `test_structural_glazing`/`test_pathway3` untouched this session). **The v1.19 Case A/C, v1.20 Case D, and v1.22 Table 5.1 figures (see those changelog entries) have not yet been independently hand-verified by Sahil.**

**v1.22 note:** the Pathway 4 `full_perimeter` human-impact table decision (Table 5.1, reversed from Table 5.3 in v1.21 — Section 12.12 item 9, Section 14.7) is now genuinely wired into `engine/combined/pathway4.py` (not `engine/structural_glazing/`, which has no subtype concept and remains untouched). A genuine Table 5.1 `NON_COMPLIANT` was found to be unreachable with real stock data for any eligible subtype — documented in the v1.22 changelog and `test_pathway4.py`'s module docstring, not faked with synthetic dimensions.

**Live browser verification performed v1.14, via Claude in Chrome:**
- Pathway 2, safety glass toggle ON, 1800×1000mm, 2-edge, Monolithic Toughened, ULS 0.1kPa/SLS 0.05kPa: confirmed 6mm governing via Table 5.3 (accordion showed ULS 4mm, SLS 4mm, Table 5.3 6mm), correct new footer wording ("Table 5.3"), matches v1.12 hand calculation.
- Pathway 2, same inputs, toggle OFF: confirmed 4mm governing (Table 5.3 excluded), no footer message at all.
- Pathway 1, safety glass toggle ON, 2000×1500mm (3.0m² area), 4-edge, Monolithic Toughened, ULS 0.8kPa/SLS 0.4kPa: confirmed 5mm governing via Table 5.1 (matches TC-I logic: SG fails at 4mm, passes at 5mm), correct footer wording ("Table 5.1").
- Pathway 1, same inputs, toggle OFF: confirmed no footer message, footer disappears immediately on toggle (before recalculating).
- No console errors beyond the documented Section 8.5 false positive.

**Live browser verification performed v1.15, via Claude in Chrome (Pathway 3):**
- `#pathway3-view` confirmed active in live DOM (`getComputedStyle`).
- 2-edge/3-edge selector confirmed hiding/showing bidirectionally across the 90° boundary (90→130→90).
- Glass type checkbox list confirmed filtering 6→4 on toggle ON, restoring to 6 on toggle OFF.
- Subset selection (2 of 6 checked) confirmed producing exactly 2 rendered cards, not all six.
- Bite figures (10mm, both Monolithic Toughened and Laminated Annealed, 1200×600×600mm, 90°, ULS 2.0kPa) hand-verified against the Section 9 formula and Table 4.1 usable-bite search — exact match.
- Table 5.1 (90°) and Table 5.3 (130°, 2-edge) branches both confirmed rendering and correctly labelled.
- Human-impact footer confirmed switching table name (5.1→5.3) immediately on angle change, before recalculating.
- Copy-as-image confirmed producing a genuine 63,971-byte `image/png` in the real clipboard via `navigator.clipboard.read()`.
- Report generation confirmed via `fetch` interception, correct trace detail.
- No genuine console errors beyond the known Section 8.5 false positive.

**Live browser verification performed v1.16, via Claude in Chrome (landing page images) and manually by the user (Pathway 4 tile image):**
- Pathway_1/2/3.png confirmed loading without error (`naturalWidth`/`naturalHeight` populated, `broken: false`) and visually inspected against their tile boxes — Pathway_2 fills its box nearly edge-to-edge (near-16:9 source ratio), Pathway_3 shows moderate letterboxing, Pathway_1 shows the most pronounced letterboxing (portrait source image).
- Pathway 4's tile confirmed untouched (placeholder text, no `<img>`, disabled) prior to its own image being added.
- New Pathway 3 angle-validation wording confirmed rendering correctly at both angle=180 and angle=50, old wording confirmed fully absent in both cases.
- Pathway 4's image/description update verified manually by the user directly in-browser (a stale dev-server-process connectivity issue prevented an independent browser recheck for this specific piece from this chat).

---

## 12. Silicone Joint Calculator — Planning and Engineering Detail

### 12.1 — Provenance and Status

This will be a new, independent calculation mode — **structural silicone bite-length sizing for frameless/structural glazing joints**, addressing a different failure mode from the existing AS 1288 Section 4 bending checks. It originates from an existing Duce Excel tool (`Silicone_Joint_Calculator_2025.xls`), confirmed as **company-owned** (built by a Duce colleague, Michael; in active use by Duce staff) — not from any former employer, and not something Claude reverse-engineered from an external/unauthorised source. This distinction was explicitly checked and confirmed with the user before any work began on it, given the user's stated constraint that nothing from a previous employer's tools should be referenced or reused.

**Current status: engine built and tested (Phase 1A–1C complete, see Section 10 item 4). Pathway 3's orchestration of this engine alongside wind load and human impact is also complete (v1.15, Section 12.13).** It was built as `engine/silicone_bite/` and `engine/structural_glazing/` inside the engine-package structure, not added into the wind-load engine's files, so it carries zero risk to the existing V1.0 codebase and was tested independently before any integration was attempted.

### 12.2 — Authoritative Sources Consulted

- **AS 1288 Clause 9.3.3.1** (provided as a screenshot excerpt) — governs facetted glazing, included angles 90°–160°.
- **AS 1288 Appendix F** (provided as screenshot excerpts) — governs flat, angle-free structural silicone glazing (a different, simpler scenario — see 12.3).
- **AGG (Australian Glass Group) Technical Bulletin 1005 — Silicone Butt Joints, December 2021 V1.0** (provided as a PDF) — a supplier technical bulletin that explains and worked-examples both the Section 9 and Appendix F formulas, and adds practical detail (IGU bite-sharing, minimum bite/glueline, fin glazing) not present in the clause text alone.
- **AS 1288 Table 4.1** (the real nominal/minimum thickness values, provided directly by the user — see Section 4 for the full table) — used to verify the silicone spreadsheet's lookup tables row-by-row.

### 12.3 — Core Formula (Confirmed)

**For facetted glazing, included angle 90°–160° (AS 1288 Clause 9.3.3.1 / Section 9):**

```
t = (F × B × Pz) / σs
```
where:
- `t` = minimum required structural silicone bite, in mm
- `F` = factor for facet angle = `1 / (2 × cos(γ/2))`, where γ = obtuse included angle between adjacent panels, in degrees
- `B` = width of each panel, in metres (distance between vertical silicone joints) — **but see 12.5 for an unresolved nuance in how Duce's spreadsheet actually derives B**
- `Pz` = design wind pressure, in kPa
- `σs` = ultimate limit stress in silicone = **0.21 MPa**, confirmed as the standard's own stated design constant (matches AS 1288 Appendix F's `0.210`, same value, same units — N/mm² ≡ MPa)

Scope is strictly 90°–160° inclusive. Above 160°, there is no structural support gained from the silicone joint at all — confirmed via the AGG bulletin (*"there is no support gained from the silicone... known as a weatherseal"*) — and the glass must be designed as two-edge supported instead, with its own different (and more conservative) deflection limit for IGUs (span/150 vs span/60 for monolithic).

**AS 1288 Appendix F (separate, simpler formula — for flat/angle-free structural glazing only):**

```
T = (Pz × B) / 2        (tension load, N/mm)
t = T / 0.210            (bite, mm)
```

Algebraically equivalent to `t = 0.5 × Pz × B / 0.21` — confirmed by direct substitution and cross-checked against Appendix F's own worked example (2.0m × 1.2m panel, 2.0kPa, giving t=5.7mm — reproduced exactly).

**Resolved discrepancy:** Appendix F and Section 9 are **not** two competing formulas for the same 90° case — they cover genuinely different physical geometries. Appendix F has no angle term at all because it describes a single flat plane of structural glazing (e.g. Figure F.1's straight vertical strip) with no corner or facet involved. Section 9's F-factor formula is specifically for facetted glazing — two adjacent panels meeting at an angle γ — and 90° is simply the tightest (most acute) case within Section 9's valid range, not a boundary case borrowed from Appendix F. The AGG bulletin's own wording supports this reading directly (90° butt joints "designed as per AS 1288 Appendix F for structural glazing" vs facetted angles 90°–160° "designed as per Section 9").

**Decision made by the user:** since Duce's existing spreadsheet (and presumably Duce's real-world use case) always involves an actual angle/corner input, **the tool will use the Section 9 F-factor method for angles >90°–160°, and Appendix F's F=0.5 at exactly 90°.** This is a hybrid approach based on engineer input and the AGG Technical Bulletin 1005's own guidance (which treats 90° butt joints as Appendix F territory and faceted angles >90° as Section 9 territory). An earlier decision to use the F-factor formula uniformly for all angles including 90° has been superseded. Appendix F's flat/angle-free formula for non-cornered structural glazing (a separate physical scenario entirely) was built as a separate module — see Section 12.12 and Section 10 item 4.

**Angle scope — confirmed strict.** The tool will only accept angles in the 90°–160° inclusive range. Angles outside this range are explicitly **out of scope**, not a "handled differently" case — outside this range the silicone joint provides no structural edge support at all (per the AGG bulletin, it becomes a weatherseal only, and the glass would need 2-edge-supported design with a different, stricter deflection limit for IGUs). The tool validates and rejects out-of-range angles with a clear message rather than silently producing an answer (`ANGLE_OUT_OF_RANGE` status). Building a 2-edge/weatherseal-only pathway for angles outside 90–160° is explicitly not planned — this is why the pathway is instead pointed to Pathway 2 directly (v1.16 wording change, see Section 14.7's introduction and the v1.16 changelog).

**"Closer than 1200mm to corner" input — relabelled.** This input is not a silicone-specific concept; it is the same Corner-vs-General distinction already used by the main calculator's N/C rating lookup (Section 4, `N_C_Tables.csv`). In the Silicone Joint Calculator mode, this is presented as **"Corner / General"**, consistent with the existing N/C pattern, rather than as a separate "closer than 1200mm?" Yes/No toggle that obscures the connection.

### 12.4 — Glass Thickness Lookup (Fully Resolved)

The Duce spreadsheet's existing lookup tables (columns O–Y, rows 31–49, for monolithic and laminated separately) were initially confusing — each nominal thickness appeared **twice**, with values that didn't immediately correspond to the real Table 4.1. This was fully traced and resolved by cross-checking against the real Table 4.1 values (Section 4) row-by-row:

- **The second row of each pair is the real, correct Table 4.1 minimum actual thickness** (confirmed exact match for every row checked: 3.8, 4.8, 5.8, 7.7, 9.7, 11.7, 14.5, 18, 23.5 for monolithic).
- **The first row of each pair is the *previous* nominal size's real minimum thickness, plus 0.1mm, relabelled under the next size up.** This exists purely as a workaround for Excel's `LOOKUP` function, which requires an ascending, gapless search range — without these filler rows, a required bite that falls in the gap between two real thresholds could resolve to the wrong nominal size. This is **not** hidden extra engineering logic or an extra safety margin — confirmed via direct numeric comparison against the real Table 4.1 values, not assumed.
- AS 1288's own clause text (Table 9.1 notes, provided as a screenshot) independently corroborates the underlying principle: *"if a bite thickness for silicone is calculated to be 7.2mm then the next available glass thickness of 8mm (minimum thickness = 7.8mm) will have to be selected"* — i.e., the comparison must always be made against the worst-case **minimum actual thickness** for a candidate nominal size, never the nominal label itself, because the nominal label overstates what's actually guaranteed to be received. The user independently re-derived and confirmed this exact principle during the session (verified for the case of a required bite just above a size's true minimum forcing a jump to the next nominal size up).

**Built design** — a single shared Table 4.1 source table plus a simple ascending search, replacing the four wide spreadsheet tables entirely, now live in `engine/shared/table_4_1.py`:

```python
TABLE_4_1_MONOLITHIC = {4: 3.8, 5: 4.8, 6: 5.8, 8: 7.7, 10: 9.7,
                          12: 11.7, 15: 14.5, 19: 18, 25: 23.5}
TABLE_4_1_LAMINATED = {5: 4.6, 6: 5.6, 8: 7.6, 10: 9.6, 12: 11.6,
                         16: 15.4, 20: 19.4, 24: 23.4}
# Monolithic 3mm deliberately excluded — Duce floors monolithic at 4mm
# minimum company-wide (same policy as the main AS 1288 calculator, Section 7.5),
# confirmed by the user as due to lack of confidence in 3mm's performance.

def find_min_nominal_for_bite(required_bite_mm, thickness_table):
    """
    Returns the smallest nominal thickness whose minimum actual thickness
    still satisfies the required bite. Returns None if no available size
    in the table satisfies the requirement (mirrors the spreadsheet's "N/A").
    """
    for nominal in sorted(thickness_table):
        if thickness_table[nominal] >= required_bite_mm:
            return nominal
    return None

def usable_bite(minimum_actual_mm, chamfer_allowance_mm, mitre_angle_deg=None):
    """
    Converts a glass thickness into usable silicone bite length.
    If mitre_angle_deg is given, stretches the bite along the diagonal cut
    (a mitred edge provides more usable bite per mm of nominal glass than
    a butt edge of the same thickness).
    """
    if mitre_angle_deg is not None:
        import math
        return minimum_actual_mm / math.cos(math.radians(mitre_angle_deg)) - chamfer_allowance_mm
    return minimum_actual_mm - chamfer_allowance_mm
```

This is a verified, like-for-like replacement — checked row-by-row against the real Table 4.1 data, not a reconstruction from inferred patterns. **Critical bug found and fixed during Phase 1 (v1.7):** the original `find_min_nominal_for_bite()` compared required bite against raw min_actual thickness — should compare against usable bite (after chamfer and mitre deduction). Replaced with `find_min_nominal_for_usable_bite()`, which is what's actually live today (see Section 12.9/v1.7 changelog). Chamfer allowance is a flat 2mm constant (`CHAMFER_ALLOWANCE_MM`) for all nominal thicknesses ≥6mm (both monolithic and laminated) — variable chamfer values below 6mm exist in Michael's spreadsheet but are unreachable due to the 6mm nominal floor.

**Note confirmed v1.15, relevant to Pathway 3's orchestration:** `run_bite_calculation()` has no glass-type/category parameter at all — a single call computes and returns both `nominal_monolithic` and `nominal_laminated` together. Nothing subtype-specific (no c1 factors, no glass_subtype input) feeds into the bite formula anywhere — bite is purely a geometry/silicone-bonding calculation, indifferent to whether the glass is Annealed, Toughened, or Heat-strengthened within its broad category. This confirms Section 12.9's original description of the split as category-only, not subtype-level.

### 12.5 — B (Governing Panel Dimension) — RESOLVED

The spreadsheet derived B via two chained steps:
1. `P5 = larger of (Width 1, Width 2)` — the "governing width"
2. `P7 = smaller of (P5, Height)` — capped against height
3. `B = P7 / 1000` (metres)

Neither AS 1288 Clause 9.3.3.1 nor the AGG bulletin's text describes this height-capping step — both define B simply as "width of each panel." This was flagged as unverified pending direct confirmation from Michael (who built the spreadsheet).

**Resolved (direct confirmation from Michael):** the height-capping step was **an error in the spreadsheet, not a deliberate design choice.** Michael confirmed only the greater width needs to be checked — height is irrelevant to B. The Excel tool has it wrong.

**Final rule: `B = max(Width 1, Width 2)`.** No height parameter is needed at all. Live code:

```python
def calculate_governing_width(width_1_mm, width_2_mm):
    """
    Determines B (governing panel dimension) for the silicone bite formula.
    Per AS 1288 Section 9 / Clause 9.3.3.1, and confirmed directly with
    Michael (who built the original spreadsheet): B is simply the larger
    of the two widths. Michael confirmed the existing spreadsheet's
    height-capping step (B = min(larger_width, height)) was an error,
    not a deliberate design choice — do not replicate it.
    """
    return max(width_1_mm, width_2_mm)
```

**Note for awareness, not for action:** this means the existing Excel spreadsheet may be silently under- or over-stating B (and therefore the required bite) for any historical calculation where height happened to be smaller than the governing width. This is a separate concern from building the new tool correctly and is not part of this project's scope to audit or correct.

### 12.6 — Monolithic and Laminated Minimum 6mm Rounding — RESOLVED

The user asked: if the calculated required bite for monolithic glass comes up as less than 6mm, should the result always be rounded up to 6mm regardless of what the lookup table would otherwise return?

Two genuinely different possible rules were identified, with different implications for *where* in the calculation a floor would need to be applied:

1. A silicone-joint constraint, applied to the **required bite value itself**, before the Table 4.1 lookup (`required_bite = max(calculated_bite, 6.0)`).
2. A separate Duce practice minimum, applied to the **final nominal thickness answer**, after the lookup.

**Resolved (direct confirmation from Michael): interpretation 2 is correct.** The floor is applied to the **final nominal glass thickness, after the Table 4.1 lookup**. Rationale confirmed as seal-driven: Dow Corning structural silicone seals start at 6mm thickness, so glass thinner than 6mm nominal is not a usable option regardless of what the bite calculation alone would suggest.

**Also resolved: this floor applies to both monolithic and laminated glass**, not monolithic only (previously an open sub-question). This is live in the engine as `apply_thickness_floor()`, called after both monolithic and laminated lookups in `run_bite_calculation()`.

### 12.7 — Other Gaps Identified But Not Yet Addressed (from the AGG bulletin, not currently in the spreadsheet or any plan)

These were identified during source review but are not part of the current build plan — listed here so they aren't lost, in case they become relevant later:

- **Minimum bite/glueline of 6mm and joint aspect ratio 1:1 to 3:1 (Dow Corning manual)** — partially related to 12.6 above; the aspect ratio constraint specifically is not handled anywhere yet.
- **IGU gap rule:** for glass thicker than 12mm, the gap between panes must be a minimum of half that thickness — not implemented anywhere.
- **IGU bite-sharing:** for double glazing, the maximum available silicone bite is the *combined* thickness of inner and outer panes, but each individual pane must still independently satisfy the minimum silicone constraints (e.g. a 6+6mm IGU gives 12mm combined bite, but each pane must still individually be ≥6mm). The engine as built is single-glazing only — no IGU-aware bite-sharing logic exists yet for the silicone calculator specifically (distinct from the main calculator's unrelated IGU load-sharing logic in Section 7.4). This is also why IGU is a deliberate scope exclusion for Pathways 2 and 3 (Section 14.2/14.3).
- **Glass fins** — a related but distinct use case, with its own minimum fin thickness rules (15mm monolithic single-glazed, 19mm double-glazed due to PEF rod clearance). Out of scope; noted only for awareness.
- **Faceted IGUs** — the bulletin states the load path is far more complex and recommends contacting AGG Technical directly for design; mitred glass is explicitly not an option for faceted IGUs. Out of scope.

None of these are blocking — they're simply not yet part of the scoped build. Revisit only if Duce's real use cases require them.

### 12.8 — Integration Architecture: Separate Engine with Optional Carry-Over — **SUPERSEDED, v1.11**

**This entire section (12.8 and 12.8.1) describes a design that has been replaced.** See the v1.11 changelog entry for the architecture that replaced it (the four-pathway landing page), and Section 12.13 (v1.14/v1.15) for Pathway 3's current, further-refined orchestration design. The content below is retained for historical record and because it documents real, still-relevant engineering reasoning (e.g. why silent recalculation was rejected, Section 12.8's discussion of what Mode 1/2 needs that the silicone form doesn't collect) — but do not build toward the carry-over/check-in-Mode-2 mechanism described below.

#### (Historical, superseded) Original design follows:

A key architectural question was resolved in a later exchange: **does the silicone bite calculation replace, or merely supplement, the existing Mode 1/2 bending checks (ULS, SLS, Safety Glass, Bushfire)?**

**Resolved: it supplements, and the two live as genuinely separate engines by default, but with an explicit user-initiated bridge between them.** This was a deliberate hybrid, chosen over two simpler alternatives that were considered and rejected:
- *Fully standalone, no bridge at all* — simplest to build, but would silently reintroduce the exact "one check masks another / user has to manually remember to check everything else" risk that Section 6.1's `max()`-across-checks pattern was specifically designed to eliminate for the main calculator.
- *Fully integrated as a fifth automatic check inside Mode 1/2's engine* — architecturally the "purest" fit with Section 6.1, but a much larger build (Mode 1/2 would need to learn about facet angle, corner/general, and joint type as new core inputs, even for users who never touch the silicone feature).

**The agreed design:**

1. **The Silicone Joint Calculator runs as its own engine** (see Section 13 for the two-engine architecture), with its own inputs (Height, Width 1, Width 2, Angle [90–160° only], Corner/General, ULS, Joint Type) and produces its own bite-driven minimum nominal thickness, fully independently of Mode 1/2.
2. **The result screen offers an explicit "carry this result over to Mode 1 / Mode 2" action.** This is opt-in, not automatic.
3. **If the user takes that action:** Mode 1/2 is pre-filled with the inputs that genuinely overlap — Height, Width 1, Width 2, and the ULS wind pressure value — and **support condition defaults to 4-edge** (since the silicone joint is now being treated as a structural edge, consistent with the 90°–160° scope). Everything else Mode 1/2 needs that the silicone mode never asked for (glass type/subtype, SLS-specific pressure if different from ULS, Safety Glass toggle, Bushfire/BAL settings, IGU configuration, etc.) is filled in manually by the user, exactly as in any normal Mode 1/2 run.
4. **Mode 1/2 then includes the carried-over bite thickness as one more entry in its existing governing-thickness comparison** — the final reported governing thickness becomes `max(ULS, SLS, SG, BAL, silicone_bite)`, with the bite thickness shown in the breakdown/accordion detail alongside the other checks, consistent with the existing trace-building pattern (Section 6.5) — i.e. it should be traceable in the report back to the angle/corner-or-general/joint-type inputs that produced it, not just appear as a bare number.
5. **If the user does not carry the result over, Mode 1/2 behaves exactly as it does today** — entirely unaffected by the existence of the silicone mode.

**Support condition is not locked.** Once carried over, support condition defaults to 4-edge but remains user-editable, including switching to 2-edge. Changing it is treated the same way as changing any other carried-over field (see below) — it is not a special-cased "locked" input.

**Invalidation behaviour on edited inputs — resolved, with a specific mechanism:**

The carried-over bite thickness is tied to the exact inputs it was calculated from. If the user edits any of the following fields *inside Mode 1/2* after carrying a result over:
- Height
- Width 1 / Width 2
- ULS (wind pressure)
- Support condition (specifically, changing away from 4-edge)

...the tool must show a warning **before** the edit is allowed to take effect — e.g. *"Changing this value will remove the carried-over Silicone Bite result (Xmm) from the governing thickness calculation, since it was calculated using the original inputs. Continue?"* If the user confirms, the edit proceeds **and the silicone bite entry is dropped entirely** from the governing-thickness list — not recalculated, not left stale, simply removed, so Mode 1/2 reverts to behaving as if the carry-over had never happened (ULS/SLS/SG/BAL only). If the user cancels, the field reverts and the bite entry remains.

**Deliberately rejected alternative: silently recalculating the bite thickness when a shared input changes.** This was considered and rejected because Mode 1/2 was never shown the silicone-specific inputs (angle, corner/general, joint type) and has no way to re-prompt for them mid-edit — a silent recalculation would risk reusing stale values for inputs the user has no visibility into at that point. Dropping the entry and requiring the user to return to the silicone mode for a fresh number is the more honest and lower-risk behaviour.

**Scope of the watched-fields list — settled at exactly the four above.** Other Mode 1/2 inputs (glass type/subtype, IGU configuration, Safety Glass toggle, Bushfire settings) do not trigger the warning, even though some of them affect which nominal thickness from Table 4.1 ultimately governs — because they don't change whether the underlying *bite requirement* itself is still valid, only what final answer it's being compared against. That comparison is exactly what Mode 1/2's existing `max()` logic is already designed to handle correctly regardless of glass type, so no special-casing is needed there.

### 12.8.1 — Simpler Cross-Engine Check: "Check in Mode 2" (Added) — **SUPERSEDED, v1.11**

**Decided in a later session, alongside the carry-over bridge above; superseded along with it — see 12.8's superseded notice.** The most common real-world question after a bite calculation is: *"does this bite-driven thickness also pass wind load?"* The carry-over bridge (12.8 above) answers this by folding the bite result into Mode 1/2's governing `max()`, but there is a simpler, complementary workflow that answers the question more directly.

**The "check in Mode 2" pattern:** The silicone engine's result screen offers a button (label TBD — e.g. "Check wind compliance") that:
1. Takes the bite engine's output thickness (e.g. 12mm)
2. Reads the shared input fields that are already filled in (span, width, wind pressure, glass type, glazing config)
3. Switches the UI to Mode 2 (compliance checker), pre-filling those shared inputs plus the bite output as the "actual thickness" to check
4. The user reviews, optionally adjusts Mode 2-specific fields (glass subtype, IGU config, Safety Glass, Bushfire), and clicks Calculate
5. Mode 2 returns its normal PASS/FAIL result against wind load

**This is a face-level orchestration, not an engine concern.** In code, it's a single JavaScript function in `index.html` (e.g. `verifyInMode2()`) that reads the current bite result, reads the shared input fields, switches the view, and fires the `/calculate` request with `mode: 2`. No new Python code is needed — the wind engine's Mode 2 already accepts exactly these inputs.

**Pre-fill-and-review, not auto-run.** The user sees the pre-filled Mode 2 form and can review/adjust before calculating. This is deliberate: the user might want a different glass type for the wind check than the bite calc assumed, or might want to toggle bushfire on.

**Relationship to the carry-over bridge:** These are complementary, not competing. "Check in Mode 2" answers "does this specific thickness pass wind?" — a quick, targeted check. The carry-over bridge answers "what's the true governing thickness across all checks including silicone?" — a more comprehensive answer. Both are useful; neither replaces the other.

**Works in both directions.** The same pattern supports "check bite for this thickness" — if Mode 1 finds a wind-driven minimum that's thinner than what the joint needs, a button could pre-fill the silicone engine the same way. And any future engine (e.g. the third mode, once scoped) slots into the same cross-check pattern without new plumbing — the face already knows how to carry inputs between engines.

### 12.9 — Build Sequence (historical — all phases through Pathway 3 are DONE; Pathway 4's orchestrator is now built too (v1.18), UI is next)

Following the same Phase 1 discipline used for the main calculator (standalone, validated calculation engine before any GUI/integration), and reflecting the two-engine architecture decided in Section 13:

**Prerequisites — ALL COMPLETE:**
- ~~Section 10 items 1–2 (V1.0 finalisation: result-dictionary constructor + structural test)~~ — DONE
- ~~Section 10 item 3 (engine-package refactor)~~ — DONE.

**Phase 1 — Standalone silicone engine (no UI, no integration): DONE.**

1. ~~Build `engine/silicone_bite/` inside the now-completed package.~~ — **DONE.** `constants.py`, `formulas.py`, `__init__.py` built. `make_silicone_result()` added to `engine/shared/results.py`.
2. ~~Build and test each function independently~~ — **DONE.** All seven functions built, plus `run_bite_calculation` entry point. 90° uses F=0.5 (Appendix F), >90°–160° uses F-factor formula (Section 9). Angle validation rejects outside 90–160°. Joint type normalisation accepts 'butt'/'mitred'/'mitre'. N/C pressure lookup uses existing `N_C_Tables.csv` from `engine/shared/data_loader.py`.
3. ~~Validate against worked examples~~ — **DONE.** AGG bulletin example (130°, 1400mm, 2.03kPa → F=1.183, bite=16.01mm) verified. Two hand-calculated cases validated (Case A: 90° butt, 600mm, N3 corner 2kPa → 10mm; Case B: 130° mitred, same inputs → 10mm). 17/17 tests passing.
4. ~~Apply result-dictionary-constructor discipline~~ — **DONE.** `make_silicone_result()` in `engine/shared/results.py`. All return paths (PASS, ANGLE_OUT_OF_RANGE, INVALID, NO_COMPLIANT_THICKNESS) go through it. Key-set consistency verified by test 15.
5. ~~Resolve Sections 12.5 and 12.6 with Michael~~ — **DONE.** Both resolved (see 12.5, 12.6).

**Critical fix applied during Phase 1:** `find_min_nominal_for_bite()` was comparing required bite against raw min_actual thickness. Replaced with `find_min_nominal_for_usable_bite()` which compares against usable bite (after chamfer and mitre deduction). This correctly accounts for the 2mm chamfer reducing the available silicone contact surface. Additionally, required bite is floored at 6mm (Dow Corning minimum contact surface) before the usable-bite lookup. The 6mm nominal thickness floor is applied separately, after the lookup.

**Phase 1B (Table 5.3 lookup): DONE**, 10/10 tests. **Phase 1C (structural glazing module): DONE**, 5/5 tests. See v1.8 and v1.9 changelog entries respectively.

**Phase 2 — Standalone UI (usable without Mode 1/2): DONE, v1.10 (superseded in navigation model by v1.11, form/route retained).**

6. Built the silicone engine's own standalone UI flow — superseded same day by the four-pathway landing page (v1.11), which re-housed the form/route under what became Pathway 3.

**Phase 3 — Cross-engine wiring: SUPERSEDED by v1.11's four-pathway model, fully realised in Section 12.13 (v1.14 design, v1.15 build).**

The original items 7–9 here (building the "check in Mode 2" button, the fuller carry-over bridge, then integrating) described the now-superseded 12.8/12.8.1 approach. Pathway 3's actual combined calculation (Section 14.3) does not use either mechanism — it runs bite + wind + human impact as one single server-side request per Section 12.13's build plan, now built and live-verified (v1.15).

### 12.10 — Clarification: When a Silicone Joint Counts as a Structural Edge (Conceptual)

Recorded here for reference since it affects how the silicone engine's output should be interpreted by Mode 1/2 and Pathway 3.

**AS 1288 Clause 9.3.3.1 confirms directly:** once a facetted joint (90°–160°) is sized per Section 9, that side of each panel may be treated as a structural edge for the purposes of the Section 4 bending/deflection check — this is the explicit basis for Pathway 3's 4-edge wind support treatment (Section 14.3).

**Worked example confirming the boundary case:** for a fixed window with two glass panels meeting at 180° (i.e. co-planar, not a real corner), with a silicone butt joint between them and structural framing on the three remaining edges of each panel — the 180° joint **cannot** be treated as structural regardless of how it is sized, since 180° sits outside Section 9's 90°–160° scope and the AGG bulletin confirms angles beyond 160° provide no structural benefit at all (weatherseal only). Each panel in this configuration is correctly **3-edge supported**, not 4-edge, for the Mode 1/2 bending check — the silicone engine does not apply to this case at all; it belongs to Pathway 2 (Section 14.2), not Pathway 3. **This is exactly the case Pathway 3's v1.16 angle-out-of-range message now redirects the user toward.**

**General rule:** a silicone joint contributes a structural edge only when (a) it sits within the 90°–160° facetted range and (b) it has been sized per Section 9. A flat/180° joint, or an unsized joint, contributes nothing structurally and that edge must be treated as unsupported (or supported by whatever frame, if any, exists on that side) for the bending check.

### 12.11 — Dead Load Bite Calculation

**Why this matters for Duce specifically:** raised because **some Duce panels have no structural frame on one or more edges** — the silicone joint is sometimes the *only* edge support present, for both wind load and dead load. This is not a hypothetical edge case; it is a real configuration Duce builds. Where a frame exists on a given edge, dead load is carried mechanically by that frame and this calculation does not apply to that edge. Where no frame exists, the silicone joint must be checked for both wind load (Section 9, already scoped) and dead load (this section) on that edge.

**Source:** a structural glazing design/materials considerations excerpt provided by the user (image only — title, publisher, and edition not independently confirmed). Formatting and content (DOWSIL product references: 983, 993N, 795, 995) are consistent with a Dow Corning / DOWSIL technical design guide, and the AGG Technical Bulletin 1005 (Section 12.2) separately confirms a "Dow Corning Asia Pacific Manual" as a real, existing reference document — but the excerpt's exact source has not been independently verified against that manual or any other authoritative copy. The formula is treated as plausible and dimensionally verified (see below) but not confirmed against a primary source.

**The formula, as provided:**

```
Minimum Bite (m) = [2,500 kg/m³ × 9.81 m/s² × Glass Thickness (m) × Glass Cross Area (m²)]
                    / [(2 × Height (m) + 2 × Width (m)) × Allowable Design Stress (Pa) for DL]
```

where:
- `2,500 kg/m³` = specific mass of float glass (≈ 25,000 N/m³ specific weight) — **confirmed consistent across annealed, toughened, and heat-strengthened glass** (toughening is a thermal process, not a compositional one, so density is unaffected). Laminated glass is treated as negligibly different despite a lighter interlayer (PVB ≈ 1,070 kg/m³) — standard industry practice, slightly conservative.
- `9.81 m/s²` = gravitational acceleration
- `Glass Thickness (m) × Glass Cross Area (m²)` = glass volume (m³); combined with density and gravity this gives the panel's weight in Newtons
- `2 × Height + 2 × Width` = panel perimeter (m) — the total bonded silicone length the weight is distributed across
- `Allowable Design Stress (Pa) for DL` = **7,000 Pa**, stated in the source excerpt as the maximum allowable design stress for dead load for DOWSIL 983, 993N, 795, and 995 structural sealants. Notably much lower than the wind load allowable (210,000 Pa / 0.21 MPa, Section 12.3) — this is expected and physically correct: wind load is a brief, transient stress, while dead load is permanent and sustained for the life of the installation. Silicone undergoes creep under sustained stress, so a far more conservative allowable is required to prevent gradual joint elongation/failure over years of service.

**Physical basis:** wind load puts the joint in **tension** (force perpendicular to the glass, pushing/pulling it away from the frame) — this is what Section 9's formula addresses. Dead load puts the joint in **shear** (gravity pulling the glass down, parallel to the glass plane, dragging against the bonded perimeter) — a different loading direction, different failure mode, and (per the formula above) a different, much lower allowable stress. Both are real, independent checks on the same joint.

**Worked example (verified, from the source excerpt):** a 1.219m × 2.438m monolithic glass lite weighing 14.8 kg/m² → panel weight 43.97 kg → perimeter 7.314m → with 7,000 Pa allowable dead load stress, minimum bite = 9mm. Independently recalculated and confirmed correct (8.41mm raw result, rounding to the next available size per the same worst-case-minimum-actual-thickness principle as Section 12.4).

**Important conceptual distinction confirmed — "4-edge bonded" vs. "supported on all 4 edges":** even though gravity only pulls the glass downward, the **entire bonded perimeter participates in resisting that load**, not just the bottom edge — the glass is a rigid body, and the silicone bond at every edge (top, bottom, both sides) shares in resisting the panel's tendency to drop. The formula's use of full perimeter reflects this. The source excerpt itself flags a caveat: *"if the horizontal frame members will not be supporting the glass or will deflect under the deadload of the glass, just consider 2 × Height (m) in the denominator"* — i.e., if the top and bottom are not reliably contributing, drop them from the perimeter and use only the two vertical sides, which produces a more conservative (larger) bite requirement. This is exactly what `sealed_edges='verticals_only'` does in the built engine.

**Once the required bite is known, the same Table 4.1 worst-case-minimum-actual-thickness lookup principle from Section 12.4 applies** to convert it into a nominal glass thickness — no new lookup mechanism is needed, just a second bite value (alongside the wind load bite) feeding the same `find_min_nominal_for_bite()` logic, with the governing (larger) of the two driving the final answer. This is built and tested — see Section 10 item 4 and the v1.9 changelog.

### 12.12 — Structural Glazing Module Scope and Precision Policy (FULLY RESOLVED — v1.18)

**Module architectural decisions — all confirmed and built:**

1. **Module identity and naming.** — **Resolved.** `engine/structural_glazing/`, separate module from `engine/silicone_bite/`. Physics, inputs, applicable clause all differ (no angle term, Appendix F not Section 9, different allowable stress, different failure mode).
2. **Does the new module need any angle input?** — **Resolved: No.** Flat glazing only. Angles belong to the faceted engine.
3. **Does the new module calculate both wind + dead load?** — **Resolved: Yes.** Appendix F wind bite, dead load shear formula, `max()` governs, then Table 4.1 lookup, 6mm floor.
4. **Automatic vs. toggled dead load check.** — **Deferred to UI phase** (Pathway 4's UI, not yet started — Section 10 item 5). Presentation decision, calculation logic identical either way.
5. **Scope: 180° flat joint weatherseals?** — **Resolved.** Weatherseal only, no structural bite. Bushfire excluded. Horizontal-span scenario (horizontals unframed, verticals framed) out of scope.

**Precision and deduction policies — all three confirmed by Michael and implemented, v1.18:**

6. **Thickness deduction for frame-bonded glazing.** — **RESOLVED, v1.18: 2mm flat deduction, all nominal thicknesses, both glass types.** Michael confirmed edge polishing does reduce usable contact thickness. Implemented as `EDGE_POLISH_DEDUCTION_MM = 2` in `engine/structural_glazing/constants.py` — deliberately a separate named constant from `CHAMFER_ALLOWANCE_MM` (`engine/shared/table_4_1.py`) despite the identical value, since the physical justification differs (perimeter edge treatment here vs. cut-edge bonding surface in the faceted engine). Applied via the shared `find_min_nominal_for_usable_bite()` search (reused, not duplicated — see v1.18 changelog), replacing the old raw-thickness `find_min_nominal_for_bite()` call. The 6mm nominal floor still applies afterward, unchanged.
7. **Rounding before Table 4.1 comparison.** — **RESOLVED, v1.18: no code change — confirmed as an expected discrepancy.** Duce's manual process rounds to 2 decimal places before comparing (e.g. 6.0277→6.03); this tool deliberately does not (Section 12.12 item 7, locked in v1.9 as a liability decision). The tool will occasionally be stricter than Duce's existing manual precedent near a boundary — documented, not fixed, per the original policy.
8. **Scenario 3 (horizontals sealed only) scope.** — **STILL OUT OF SCOPE at the engine level** (`horizontals_only` returns `CONFIGURATION_OUT_OF_SCOPE`, unchanged, confirmed by test 4 of `test_structural_glazing.py`). **Separately, v1.18 added an orchestrator-level scope gate for Pathway 4** (`engine/combined/pathway4.py`, `SUPPORTED_SCENARIOS_V1 = ('full_perimeter',)`): only `full_perimeter` is exposed as a user-facing Pathway 4 scenario in this version. `verticals_only` — a real, already-built and tested engine capability (Case B) — is also gated out at the orchestrator for now, since Duce's real-world build frequency for it as a *pathway option* is unconfirmed; the engine itself is untouched and remains fully capable of computing it. If a future session confirms `verticals_only` (or `horizontals_only`, pending separate engine-level scoping) should be user-facing, only the orchestrator's `SUPPORTED_SCENARIOS_V1` tuple needs to change.

**Implementation status:** Phase 1C engine (`engine/structural_glazing/`) built and tested since v1.9, now with the edge-polish deduction applied (v1.18). New orchestrator `engine/combined/pathway4.py` (v1.18) gates Pathway 4 to `full_perimeter` only. Three structural-glazing test cases (Case A/B/C, plus Case D added v1.20) and four `test_pathway4.py` cases all green — see the v1.18/v1.19/v1.20 changelog entries for the recomputed figures (not yet independently hand-verified by Sahil). **This closes Section 12.12's original three items fully.**

9. **Human impact table for `full_perimeter` — REVERSED, v1.21: Table 5.1, not Table 5.3.** This reverses the rule previously stated here and in Section 14.7 ("Table 5.3 applies... for... all flat structural glazing cases"). **`full_perimeter` now uses Table 5.1** (4-edge framed equivalent). `verticals_only` and `horizontals_only` are unaffected and remain under Table 5.3, since they genuinely lack support on all four edges — the reversal applies only to the one scenario that is actually sealed on all four sides.

   **The reasoning, recorded in full (not just the conclusion) so a future reader understands why this changed:** Pathway 4's `full_perimeter` configuration is glass silicone-bonded continuously around all four edges to a frame member. The frame itself does not mechanically retain the glass the way a standard framed window does (no rebate gripping the glass by its own rigidity) — instead, the continuous structural silicone bond *is* the retention mechanism, transferring load from the glass to the frame. This is mechanically the same support condition as the 90° structural silicone butt joint already confirmed for Table 5.1 in Pathway 3 (Section 12.10) — glass-to-glass there, glass-to-frame here, but in both cases a continuous structural silicone bond provides genuine edge support equivalent to mechanical framing, just via adhesive bond rather than a rebate. Since a 90° joint is accepted as providing the same structural support as a fully framed edge, and full-perimeter sealing provides that same continuous silicone support on all four sides, it should be treated as 4-edge supported for Table 5.1 purposes on the same basis — not as a separate or weaker case that defaults to Table 5.3's more conservative treatment.

   **Confirmation source:** confirmed directly by Sahil, based on consultation with two named external experts — **Adam Davies** (Australian Glass and Window Association, AGWA) and **Siddharth Kumaran** (Viridian Glass; formerly AGWA's primary structural engineer and a co-author/contributor to the AS 1288 standard's drafting). This confirmation was given in direct response to the specific `full_perimeter`, silicone-bonded-to-frame configuration described above — not a general analogy applied afterward by this project. Conversation dated 10 July 2026.

   **Related clarification — this does NOT reopen the bushfire exclusion (Section 14.5 rule 1):** AS 3959's "fully framed" requirement for BAL 12.5/19/29 eligibility means genuine *mechanical* frame support on all four edges — a different definition of "framed" than Table 5.1's structural-equivalence basis. Table 5.1 asks whether the edge behaves *structurally* like a framed edge (which a continuous silicone bond satisfies). AS 3959 asks whether there is an actual mechanical frame member providing the sealing/radiant-heat performance the bushfire provisions depend on (which silicone bonding does not provide, regardless of its structural adequacy). These are two different standards answering two different questions — Table 5.1 applying and the AS 3959 exclusion still applying are both correct simultaneously, not contradictory. `full_perimeter` remains bushfire-excluded, unchanged.

   **Implementation status: WIRED, v1.22.** `run_pathway4_calculation()` (`engine/combined/pathway4.py`) now runs Table 5.1 per subtype when `safety_glass_required=True`, for `full_perimeter` only, and folds it into `max(bite, table_5_1)` per subtype. `run_structural_glazing_calculation()` itself (`engine/structural_glazing/`) is untouched — it still only computes wind bite, dead load bite, and the governing Table 4.1 lookup, since Table 5.1 is per-subtype and that function has no subtype concept. See the v1.22 changelog entry for the full investigation, the subtype-mismatch finding, and the found-but-unreachable-with-real-data Table 5.1 `NON_COMPLIANT` fact. **Not yet hand-verified by Sahil.**

### 12.13 — Pathway 3 Combined Calculation — Build Sequence and Outcome (v1.14 design, v1.15 build — COMPLETE)

This section superseded, for Pathway 3 specifically, the old carry-over-bridge/check-in-Mode-2 approach described in Section 12.8/12.8.1 (already marked superseded by v1.11's landing-page redesign). Pathway 3 does not carry results between separate Mode 1/2 screens — it runs one combined server-side calculation per Section 14.3. **This section now describes a built and fully live-verified feature, not a plan.**

**Per-glass-category flow, as built and confirmed correct (v1.15):**
1. Run `run_bite_calculation()` **once for the whole pathway invocation** — confirmed this function has no category parameter at all; it returns `nominal_monolithic` and `nominal_laminated` together in a single call. (This corrected an earlier assumption in the original build plan that bite would be called once per category — verified against the actual function signature before any orchestration code was written.)
2. **Short-circuit at the broad-category level, driven by the actual returned fields, not by the function's overall status:** if `nominal_monolithic` is `None`, every Monolithic subtype fails entirely at this stage; independently, if `nominal_laminated` is `None`, every Laminated subtype fails. **Critical distinction confirmed this session:** `run_bite_calculation()`'s own `status` field is binary — it only returns `NO_COMPLIANT_THICKNESS` when *both* categories fail simultaneously; `status='PASS'` is returned whenever *at least one* category succeeds, even if the other category failed. Pathway 3's per-subtype gating therefore reads `nominal_monolithic`/`nominal_laminated is None` directly, never the bite function's own `status` string, to correctly handle the mixed case (one category passes, the other doesn't).
3. For glass types clearing step 2: run the existing Mode 1 wind search (`check_glass_type`, `support_condition='4-edge'`, `safety_glass_required=False`) — returns ULS and SLS as separate figures.
4. Run the angle-appropriate human impact check, gated on the safety glass toggle per Section 14.7:
   - Angle == 90° exactly → Table 5.1 (no joint-count concept)
   - Angle >90°–160° → Table 5.3, with its own 2-edge/3-edge selector (confirmed necessary — Duce's real configurations can have either 2 or 3 joints depending on layout, same as Pathway 2's selector)
   **Deliberate design decision, confirmed correct and unchanged since v1.14's design session:** `unframed_edge_condition` is never passed into `check_glass_type()` for this pathway. `check_glass_type()`'s Table 5.1 check fires whenever `support_condition == '4-edge'`, and its Table 5.3 check fires whenever `unframed_edge_condition` is set — independently, with no logic to prevent both firing at once. Every prior caller only ever paired `unframed_edge_condition` with `support_condition='2-edge'`, so this never collided before Pathway 3's >90°–160° case (4-edge wind support + Table 5.3 human impact, together for the first time). Rather than add a new conditional branch to the already-validated `check_glass_type()`, Table 5.1/5.3 are computed independently inside `pathway3.py` instead — ULS/SLS come from `check_glass_type()` with human impact switched off entirely, and Table 5.1 (a small local re-implementation reusing the shared `get_safety_glass_max_area()` formula) or Table 5.3 (reusing the existing standalone `check_table_5_3_thickness()`) are computed separately and combined via `max()`.
5. Governing = `max(bite, ULS, SLS[, human_impact if toggle ON])`.

**Confirmed via direct `Table_5_3.csv` read (v1.15):** no Toughened or Laminated row has a joint maximum of 1 — every such row caps at 2 or has no restriction; only Annealed/Heat-Strengthened rows (height band 2–2.5m) have a joint max of 1, and both those glass types are already excluded from this branch whenever safety glass is required. This means the 2-edge/3-edge selector cannot currently produce different results for any glass type actually eligible to reach Table 5.3 in this pathway — confirmed as a fact about the standard's current data, not a defect in the selector's wiring, which is correctly threaded through regardless.

**Orchestration location, confirmed and built:** `engine/combined/pathway3.py`, `run_pathway3_calculation()` — not `app.py`, not inside `silicone_bite/` or `wind_load/`. Rationale: engines don't import each other (Section 13.1), so the sequencing logic above can't live inside any single existing engine; and it's engineering decision-making (short-circuiting, angle-based branching, `max()` across results), not presentation, so it doesn't belong in `app.py` either.

**Result structure:** `make_pathway3_result()` added to `engine/shared/results.py`, following the existing constructor discipline (Section 6.4) — every return path uses it. Fields include per-subtype `governing_thickness_mm`, `bite_thickness_mm`, `uls_thickness_mm`, `sls_thickness_mm`, `human_impact_thickness_mm` (`None` if toggle off or subtype ineligible), and `status` (`PASS` / `BITE_NO_COMPLIANT_THICKNESS` / `HUMAN_IMPACT_INELIGIBLE` / `HUMAN_IMPACT_NOT_PERMITTED`), plus trace fields per subtype and check.

**Test suite built:** `tests/test_pathway3.py`, 7 hand-calculable cases — bite governs, wind governs, Table 5.1 governs at exactly 90°, Table 5.3 governs at >90°–160° (both 2-edge and 3-edge selector variants, confirmed producing identical results per the CSV finding above), bite `NO_COMPLIANT_THICKNESS` for one broad category only (with the other category's subtypes confirmed proceeding unaffected), and a human-impact-ineligible subtype (confirmed still returning bite/wind results with `human_impact_thickness_mm=None`, not a crash or silent skip).

**UI built (v1.15):** single combined form (height, width 1/2, angle [90–160 validated], corner/general, joint type, wind pressure, safety glass toggle), `buildP3GlassTypeCheckboxes()` for subset subtype selection (only checked subtypes are calculated/rendered — matches the Mode 1 checkbox convention used everywhere else in the tool), an angle-reactive 2-edge/3-edge selector (`#p3-edge-condition-row`, hidden at exactly 90°, shown for >90°–160°), one Calculate action posting to `/calculate_pathway3`, one result card per selected subtype with its own bite/ULS/SLS/human-impact breakdown, report generation (`build_pathway3_report()`), and copy-as-image (reusing `buildSnapshotHTML()`/`copySnapshotAsImage()` directly, no changes needed).

**Full seven-suite regression green** (74 checks total, zero regressions) and **full live browser verification performed via Claude in Chrome** — see Section 11 for the complete verification list. **No bugs found.** This closes Pathway 3 fully.

**Sequenced build plan (completed):**
1. ~~Pathway 2 retroactive safety-glass gate fix + human-impact footer wording overhaul (v1.14, commits `345f70e` and `9c11a9d`)~~ — **DONE.**
2. ~~Build `engine/combined/pathway3.py` + `tests/test_pathway3.py`, full seven-suite regression~~ — **DONE (v1.15, commit `053ed17`).**
3. ~~Pathway 3 UI — form, route, report, copy-as-image~~ — **DONE (v1.15, commit `84b168b`), fully live-verified.**

**What's still genuinely open:** nothing remains for Pathway 3 itself. The only remaining gap in the entire four-pathway model is Pathway 4's UI — no longer blocked (Section 12.12 fully resolved, `engine/combined/pathway4.py` built, v1.18) but not yet started.

---

## 13. V2 Architecture Design — Two-Engine Split

### 13.1 — Core Principle: Separate the Brain from the Face

**Now implemented.** The engine/interfaces split is live as of v1.3. The calculation engine (`engine/wind_load/`) is a self-contained Python package that knows nothing about Flask or HTML. The web interface (`interfaces/flask_app/`) imports from it and handles all presentation. This separation was originally planned for V2.0 but was reclassified and completed as a V1.0 update (see Section 3 for the built structure and Section 3.1 for how the refactor was carried out).

**The rule:** the calculation engine is a self-contained Python package that knows nothing about Flask, browsers, or HTML. You hand it numbers and settings; it hands back a result dictionary. All faces (web app, desktop GUI, future record-keeping system if ever built) share the exact same brain. Engineering logic is written and validated once, not per-face.

**Dependency direction:** dependencies only point inward (toward the data). A face imports from an engine; an engine never imports anything about a face; the two engines never import from each other. They share through a common foundation layer below them. The day `import flask` appears inside a calculation file is the day something landed in the wrong place. **The one deliberate exception, confirmed v1.14 and built v1.15:** `engine/combined/pathway3.py` (Section 12.13) is not itself an engine — it's a thin orchestrator permitted to import from multiple engines, since Pathway 3 genuinely needs to sequence outputs from `silicone_bite` and `wind_load` together and that sequencing logic has nowhere else correct to live.

### 13.2 — Two-Engine Architecture (now three, plus one orchestration module)

The silicone bite calculator is not a "check" inside the existing wind-load engine — it's a second engine addressing a different failure mode (sealant joint sizing vs. glass bending under wind). Different physics, different inputs, different governing equation. It belongs *beside* the wind-load engine, not inside its check list. The structural glazing engine is a third, same reasoning. `engine/combined/` (built, v1.15) is not a fourth engine but a thin orchestrator over the first three, specific to Pathway 3.

**Engine selection vs. mode selection — two levels (historical framing, largely superseded by the four-pathway model but still descriptive of what's happening under the hood):**
- **Engine selection** is the top-level switch: "I'm sizing glass for wind" vs. "I'm sizing a structural joint." The face (web app / EXE) owns this switch — now expressed as pathway selection (Section 14) rather than an explicit engine-selector tab.
- **Mode selection** is internal to each engine: Mode 1 / Mode 2 within the wind engine; bite mode / structural glazing mode within the silicone/structural-glazing engines.

The user first picks a pathway, and the pathway's face code calls whichever engine function(s) it needs. Each engine owns its own modes internally. The face doesn't reach into an engine's mode logic — it just calls `run_calculation()`, `run_bite_calculation()`, `run_structural_glazing_calculation()`, or `run_pathway3_calculation()`, with the inputs the user provided.

### 13.3 — Shared Foundation Layer

Wind pressure is an input to *both* the wind and silicone engines — the silicone formula is driven by the same wind pressure as the bending checks. This makes the wind-pressure resolution logic (direct kPa entry or N/C rating lookup) genuinely shared infrastructure, not wind-engine-specific code. It lives in `engine/shared/data_loader.py` (specifically `get_pressures_from_nc_rating()`).

The result-dictionary constructors (`make_mode1_result()`, `make_mode2_result()`, `make_silicone_result()`, `make_structural_glazing_result()`, `make_pathway3_result()`) also live in `engine/shared/results.py` — every engine benefits from the same "one constructor, every path goes through it" discipline that prevents the missing-key bug class (Section 6.4).

The versioned data loader (`engine/shared/data_loader.py`) reads CSVs and is consumed by every engine. Table 4.1 (`engine/shared/table_4_1.py`) and Table 5.3 (`engine/shared/table_5_3.py`) are shared lookups, each consumed by more than one engine/pathway.

### 13.4 — Cross-Engine Workflows (Face-Level, Historical — Superseded by Pathway 3's Combined Calculation)

The two workflows described in Section 12.8/12.8.1 ("check in Mode 2" and the carry-over bridge) were the original cross-engine wiring plan, both superseded by v1.11's four-pathway model. Pathway 3 (Section 14.3, Section 12.13) achieves the same underlying goal — combining bite, wind, and human impact into one answer — via a single server-side orchestration function rather than face-level, user-initiated bridging between separately-run engines. **This is a cleaner outcome than either original workflow, now built and live-verified:** the user gets one combined result in one request, with no manual "carry over" step and no risk of a stale carried-over figure.

### 13.5 — What NOT to Build

The architecture is designed for the engines and faces that exist today (wind-load, silicone, structural-glazing, the Pathway 3 orchestrator; the four-pathway web app + EXE), not for speculative future requirements. Specifically:

- **Do not pre-build an API layer for record-keeping.** Record-keeping is conceptual only (Section 10 item 8). When it arrives, wiring it in is an addition (it calls the existing engine functions like everything else), not a rewrite — but only if the brain/face split is held in the meantime.
- **Do not pre-shape a base class around a Human Impact engine.** Full Human Impact is deferred (Section 10 item 7) and its exact shape is unknown. The beta Safety Glass/Table 5.3 checks stay as checks inside their respective engines for now. Designing an abstraction for a requirement you don't fully understand usually produces the wrong abstraction.
- **Do not over-abstract.** This is a solo engineer maintaining an internal tool, not a ten-person team. The structure is "enough separation that new pathways slot in cleanly and each engine is reusable." If any layer ever feels like ceremony rather than help, that's a signal to collapse it.
- **Do not build the interactive edge/angle visualiser.** Explicitly descoped from V2 as of v1.17 (Section 10 item 15, Section 14.6) — retained in this document for reference only, in case revisited in a future, separate version.

### 13.6 — Sequencing Summary

```
V1.0 finalisation (result constructor + structural test + refactor) — ALL DONE
        │
        ▼
Silicone + structural glazing engines built (Phase 1A–1C) — ALL DONE
        │
        ▼
Four-pathway landing page: Pathway 1, Pathway 2, Pathway 3 — DONE, fully verified live
        │
        ▼
Pathway 4 UI (unblocked as of v1.18 — Section 12.12 fully resolved, orchestrator built — not yet started)
        │
        ▼
Versioned data (can overlap with any of the above)

Separately, ongoing (not gated on the above):
Monthly EXE rebuild cadence with kill-switch expiry — decided v1.17, two bugs
queued (launcher.py message string, stale .spec files), not yet fixed
        │
        ▼
Consolidated V2 EXE release (Pathways 1-3, plus 4 if ready), expiry to end
of August — decided v1.17, not yet executed
```

Restructuring and adding features happen in separate, verified steps — never together. A red test after a move means the move broke something; a red test after a feature addition means the feature broke something. This discipline continues for all future work.

---

## 14. AS 1288 Decision Tree — Non-Fully-Framed Glazing

This section documents the complete decision tree for determining glass thickness under AS 1288 when the glazing is not fully framed on all four edges. Mapped through a systematic back-and-forth, verified against the standard's clause text, the AGG Technical Bulletin 1005, and expert input on human impact table selection. Each branch specifies the applicable wind load support condition, silicone bite calculation (if any), human impact table, and bushfire applicability.

### 14.1 — Branch 1: Fully Framed (4-Edge Supported)

All four edges are structurally framed (timber, aluminium, or equivalent). This is the V1.0 baseline — already built and validated.

- **Wind load:** 4-edge supported, Section 4 (ULS and SLS independently, governing = larger of the two)
- **Human impact:** Table 5.1 (4-edge area limits, currently implemented as beta Safety Glass check), **only when the safety glass toggle is ON — see Section 14.7 (v1.14)**
- **Silicone bite:** Not required — no silicone joint exists
- **Bushfire:** BAL 12.5/19/29 applies (already implemented in V1 beta)
- **Governing thickness:** `max(ULS, SLS[, Safety Glass/Table 5.1 if toggle ON][, BAL if applicable])`

### 14.2 — Branch 2: 2-Edge / 3-Edge Unframed (Angle >160°–180°, Weatherseal Only)

One or both vertical (or horizontal) edges are unframed. If a silicone seal exists on the unframed edge(s), the angle between adjacent panels is >160° — the seal is a **weatherseal only** and provides no structural edge support (per AGG bulletin: "there is no support gained from the silicone... known as a weatherseal").

3-edge is treated as 2-edge for wind loads — AS 1288 does not have a distinct 3-edge support condition.

- **Wind load:** 2-edge supported, Section 4
- **Human impact:** Table 5.3 ("Glazed panels with unframed side edges"), **only when the safety glass toggle is ON — see Section 14.7 (v1.14; this correction supersedes the unconditional wording in prior versions of this section).** Table 5.3 applies three simultaneous constraints per row: minimum nominal thickness, maximum number of vertical butt joints, and maximum panel width — all varying by height band and glass type. The "maximum vertical butt joints" column distinguishes 3-edge (1 unframed edge = 1 joint) from pure 2-edge (2 unframed edges = 2 joints). Table 5.3 can act as a gate — if a configuration exceeds the allowed joint count for its height/glass combination, it is rejected, not just penalised with thicker glass. Note per Table 5.3 footnotes: "height" = span per Clause 1.4.51; toughened values also apply to laminated toughened (Note 2). **This is the pathway that Pathway 3's angle-out-of-range message (v1.16) now directs the user toward.**
- **Silicone bite:** Not required — seal is weatherseal only, not structural
- **Bushfire:** **Not allowed.** BAL 12.5/19/29 all require fully framed glazing. If a user selects a BAL level AND specifies any unframed edges, the tool should reject the combination upfront.
- **Governing thickness:** `max(wind load as 2-edge[, Table 5.3 result if toggle ON])`

### 14.3 — Branch 3: Faceted Structural Silicone (90°–160°)

Two panels meet at an angle γ between 90° and 160° inclusive. Structural silicone is used at the joint and must be sized per AS 1288 Section 9 (Clause 9.3.3.1). Once the bite is properly sized, the joint counts as a structural edge — the glass may be treated as 4-edge supported for the Section 4 bending check (per the clause's own wording).

- **Wind load:** 4-edge supported, Section 4 — **conditional on** the actual glass thickness satisfying the calculated silicone bite requirement
- **Silicone bite:** Section 9, F-factor formula: `t = (F × B × Pz) / σs` where F = 1/(2·cos(γ/2)). Produces a minimum bite thickness → Table 4.1 lookup → minimum nominal glass thickness. 6mm floor applies to final nominal thickness (both monolithic and laminated).
- **Human impact, only when the safety glass toggle is ON (v1.14 — see Section 14.7; this correction supersedes prior versions' unconditional wording):**
  - If angle = **exactly 90°** → **Table 5.1** (structural silicone at 90° treated as equivalent to framing for human impact — confirmed by expert)
  - If angle = **>90° to 160°** → **Table 5.3** (conservative — silicone is structural for wind but treated as unframed for human impact, since near-flat joints don't provide the same physical restraint as a tight corner). Needs its own 2-edge/3-edge selector for the Table 5.3 joint-count lookup — **built and live-verified as of v1.15 (Section 12.13); confirmed via direct CSV read that this selector cannot currently produce different results for any glass type eligible to reach Table 5.3 in this branch, since the only rows with a joint max of 1 belong to already-ineligible glass types.**
- **Bushfire:** **Not allowed.** BAL requires fully framed glazing.
- **Governing thickness:** `max(silicone bite, wind bending as 4-edge[, human impact per applicable table if toggle ON])`
- **Status: fully built and live-verified as of v1.15** — orchestration engine (`engine/combined/pathway3.py`), UI, report generation, and copy-as-image all complete. See Section 12.13 for the full build/verification detail.

### 14.4 — Branch 4: Flat Structural Glazing (No Angle, Structural Silicone, No Frame)

A single panel with no frame on one or more edges, with structural silicone providing edge support. No angle between panels — this is AS 1288 Appendix F territory, not Section 9. Dead load bite sizing also applies where the silicone is carrying the panel's weight (typically on vertical edges or bottom edges with no mechanical support below).

- **Wind load:** 4-edge supported, Section 4 — **conditional on** all edges having adequate structural silicone bite
- **Silicone bite (wind):** Appendix F: `t = 0.5 × Pz × B / σs` (σs = 0.21 MPa). No angle term.
- **Silicone bite (dead load):** Shear formula from Section 12.11: `Minimum Bite = (2,500 × 9.81 × thickness × area) / (perimeter × 7,000 Pa)`. Applies to edges where silicone is carrying dead load (no frame behind). If horizontal frame members are not supporting the glass, use only `2 × Height` in the denominator instead of full perimeter.
- **Governing bite:** `max(wind bite, dead load bite)` → Table 4.1 lookup → minimum nominal glass thickness. 6mm floor applies (both monolithic and laminated).
- **Human impact — REVERSED, v1.21 (Section 12.12 item 9):** `full_perimeter` (sealed on all four edges) now uses **Table 5.1** — the continuous silicone-to-frame bond on all four sides is treated as structurally equivalent to mechanical framing, same basis as Pathway 3's 90° silicone joint. `verticals_only`/`horizontals_only` (genuinely unsupported on some edges) remain on **Table 5.3**, unchanged. Either table, **only when the safety glass toggle is ON — see Section 14.7 (v1.14)**. **Not yet wired into the engine** — this is a documented decision only; `engine/structural_glazing/` has no human-impact-table logic at all yet.
- **Bushfire:** **Not allowed, for every scenario including `full_perimeter`.** AS 3959's "fully framed" requirement means genuine mechanical frame support, a different question from Table 5.1's structural-equivalence basis — the v1.21 Table 5.1 reclassification does not reopen this exclusion (Section 12.12 item 9).
- **Governing thickness:** `max(governing bite, wind bending as 4-edge[, human impact result if toggle ON])`
- **Dead load scope:** primarily single panels siliconed to surfaces or two-panel stacks (Duce's typical use case). Each joint carries only the weight of the panel immediately above it — loads do not accumulate cumulatively through a stack. Engineering spec complete (Section 10 item 4), edge-polish deduction now applied (v1.18); this pathway's UI is not yet built (Pathway 4, greyed out, now with real tile artwork as of v1.16, orchestrator built v1.18, still disabled pending UI — Section 12.12 fully resolved).

### 14.5 — Key Rules Across All Branches

1. **Bushfire (BAL 12.5/19/29) requires fully framed glazing** — the entire non-framed decision tree (Branches 2, 3, 4) is excluded. No new bushfire logic needed for any silicone/structural glazing branch.
2. **3-edge defaults to 2-edge for wind loads** — AS 1288 does not define a distinct 3-edge support condition.
3. **A sealed edge at >160° is always a weatherseal, never structural** — no bite calculation applies, and the edge does not count as a support for wind load or human impact purposes.
4. **Structural silicone only earns its status as a structural edge when**: (a) the angle is within 90°–160° (faceted, Section 9) OR the edge has structural silicone with no angle (flat, Appendix F), AND (b) the bite has been properly sized per the applicable formula.
5. **Dead load only applies where there is genuinely no frame on an edge** — if a frame exists on any edge, it carries the dead load mechanically on that edge and no dead-load bite calculation is needed for that edge.
6. **The `max()` across all active checks pattern (Section 6.1) applies to every branch** — no check's result should mask another's, and only genuinely active checks participate (v1.14 — see Section 14.7).
7. **Horizontal span scenario (both horizontals unframed, only verticals framed) is explicitly out of scope** for this tool.
8. **Human impact tables (Table 5.1/5.3) are user-declared, not automatic, in every branch** (v1.14) — see Section 14.7.

### 14.6 — Visualiser Template Coverage Map — **EXPLICITLY DESCOPED FROM V2, v1.17**

**This entire feature is now out of scope for the current V2 update, per user decision (v1.17).** The section below is retained unmodified for historical reference and in case this is revisited in a future, separate version — do not build toward it under the current scope.

Ten fixed visual templates (user-provided PDF designs, not dynamically resizing), verified against every branch of the decision tree above.

Ten fixed visual templates (user-provided PDF designs, not dynamically resizing), verified against every branch of the decision tree above. The visualiser guides the user to select their glazing configuration; the tool then uses the selection to determine the correct support condition, bite calculation requirements, and human impact table.

**Note (v1.16): this is a distinct, separate scope from the four landing-page tile images completed in v1.16.** Those are single static images per pathway tile on the main landing page (`Pathway_1.png` through `Pathway_4.png`). The visualiser described in this section is a fuller, interactive diagram tool used within a pathway's own form to confirm edge/angle configuration — not yet started, to be built in a dedicated separate chat per Section 0.

**Design decisions:**
- Fixed templates chosen over dynamic resizing — simpler to build and maintain
- 3-edge shares 2-edge templates when no seal or weatherseal (the distinction is captured by the butt-joint count input feeding Table 5.3, not by a separate visual)
- 3-edge with seal defaults to 180° (weatherseal) unless the user is specifically calculating bite thickness at 90°–160°, in which case it branches to the faceted templates
- Verticals sealed: dead load distributes across vertical joints, wind span is horizontal
- Horizontals sealed: dead load distributes across horizontal joints, wind span is vertical
- All edges sealed: dead load distributes across full perimeter, 4-edge if all bites satisfied
- Visualiser applies to Mode 1/2 (wind-load engine) as well as silicone/structural glazing engines
- **To be built in a dedicated separate chat under this project** — see Section 0 for the ready-to-paste prompt

**Coverage map:**

| Template | Source | Configuration | Wind support | Bite calc | Human impact |
|---|---|---|---|---|---|
| Row 1 left | PDF 1 | Fully framed, height as span | 4-edge | None | Table 5.1 |
| Row 1 right | PDF 1 | Fully framed, width as span | 4-edge | None | Table 5.1 |
| Row 2 left | PDF 1 | 2-edge, horizontals framed | 2-edge | None | Table 5.3 |
| Row 2 right | PDF 1 | 2-edge, verticals framed | 2-edge | None | Table 5.3 |
| Pair 1 (front + plan) | PDF 1 | 180° butt joint (weatherseal) | 2-edge per panel | None | Table 5.3 |
| Pair 2 (front + plan) | PDF 1 | 90° corner, structural silicone | 4-edge if bite OK | Section 9 | Table 5.1 |
| Pair 3 (front + plan) | PDF 1 | 90°–160° faceted, structural silicone | 4-edge if bite OK | Section 9 | Table 5.3 |
| New left | PDF 2 | Verticals sealed, horizontals open | 2-edge on verticals | Appendix F + dead load | Table 5.3 |
| New middle | PDF 2 | Horizontals sealed, verticals open | 2-edge on horizontals | Appendix F + dead load | Table 5.3 |
| New right | PDF 2 | All edges sealed, no frame | 4-edge if all bites OK | Appendix F + dead load | Table 5.3 |

**Source files:** `Height.pdf` (first seven templates) and `Height__2_.pdf` (three structural glazing templates) — both provided by the user, stored in uploads.

### 14.7 — Human Impact Table Gating — Confirmed Rule (v1.14)

Confirmed in v1.14: in every pathway, Table 5.1 and Table 5.3 are user-declared checks, not automatic ones. They only run when the safety glass toggle is set to Yes. This closes an inconsistency: Pathway 1's Table 5.1 was always correctly gated this way, but Pathway 2's Table 5.3 (built in v1.12) ran unconditionally regardless of the toggle. Table 5.3 gating was retrofitted to match in v1.14, and the same rule was confirmed applying to Pathway 3 once built (v1.15).

**Which table applies, per pathway/scenario, updated v1.21:**
- Pathway 1 (fully framed): Table 5.1.
- Pathway 2 (2-edge/3-edge unframed): Table 5.3.
- Pathway 3 (faceted structural silicone): Table 5.1 at exactly 90°, Table 5.3 for >90°–160° (Section 12.13).
- **Pathway 4 (flat structural glazing) — REVERSED, v1.21 (Section 12.12 item 9), WIRED v1.22:** `full_perimeter` (sealed on all four edges) now uses **Table 5.1**, not Table 5.3 as previously documented — the continuous silicone-to-frame bond on all four sides is structurally equivalent to mechanical framing, the same basis already accepted for Pathway 3's 90° silicone joint (Section 12.10). `verticals_only`/`horizontals_only` remain on Table 5.3, since those scenarios genuinely lack support on some edges. See Section 12.12 item 9 for the full reasoning and confirmation source (Adam Davies, AGWA; Siddharth Kumaran, Viridian Glass/AS 1288 contributor). **Genuinely wired in as of v1.22** — `run_pathway4_calculation()` (`engine/combined/pathway4.py`) runs Table 5.1 per subtype for `full_perimeter` when the toggle is ON; `run_structural_glazing_calculation()` itself remains untouched (no subtype concept). Not yet hand-verified by Sahil.

The gating rule above (toggle-controlled, off by default) applies unchanged regardless of which table a given pathway/scenario selects.

| Pathway | Toggle OFF | Toggle ON |
|---|---|---|
| 1 (Fully Framed) | No human impact check. Governing = max(ULS, SLS[, BAL]). | Table 5.1 runs. Governing = max(ULS, SLS, Table 5.1[, BAL]). |
| 2 (Partly Framed, Exposed Edges) | No human impact check. Governing = max(wind as 2-edge). | Table 5.3 runs. Governing = max(wind as 2-edge, Table 5.3). |
| 3 at exactly 90° | No human impact check. Governing = max(bite, wind as 4-edge). | Table 5.1 runs. Governing = max(bite, wind as 4-edge, Table 5.1). |
| 3 at >90°–160° | No human impact check. Governing = max(bite, wind as 4-edge). | Table 5.3 runs (2-edge/3-edge selector applies). Governing = max(bite, wind as 4-edge, Table 5.3). |

**Critical clarification, confirmed directly by Sahil in v1.14:** even when the toggle is ON and a human impact table governs, **the tool has not performed a human impact risk assessment.** The toggle only declares that the user has already determined — via their own AS 1288 Section 5 assessment — that safety glass is required. Whether safety glass is actually required for a given application remains entirely the user's determination, in every case, regardless of toggle state. This is why the v1.14 footer wording says the check "has been applied... as declared by the user" rather than anything implying the tool assessed applicability.

**Footer message, all pathways (v1.14):**
- **Toggle OFF:** no human impact message displayed at all.
- **Toggle ON:** *"Safety glass requirements (Table 5.1 / Table 5.3, whichever applies) have been applied to the thickness selection as declared by the user. This tool does not assess whether safety glass is required for this application. The user is responsible for determining applicability in accordance with AS 1288 Section 5 and relevant building codes."*

This rule and wording apply identically on-screen (`#human-impact-footer`, driven by `updateHumanImpactFooter()`) and in the downloadable TXT report (`build_report()`'s footer conditional for Pathways 1/2, `build_pathway3_report()` for Pathway 3), **confirmed live for all three pathways as of v1.15** — Pathway 3's footer correctly re-derives the table name (5.1 vs 5.3) from the current angle both on toggle and on pathway entry, matching the same immediate-update behaviour already confirmed for Pathways 1/2.

**Related, v1.16:** Pathway 3's angle-out-of-range validation message (client-side, for angles outside 90–160°) now explicitly directs the user to Pathway 2 rather than just stating the input is unsupported — reinforcing the Branch 2/Branch 3 boundary described in Section 14.2/14.3/12.10, since angles beyond this range genuinely belong to Pathway 2's weatherseal-only territory, not a variant of Pathway 3.

---

*End of document.*
