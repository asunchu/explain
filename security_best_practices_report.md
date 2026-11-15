# Explain security review

Review date: November 8, 2026.

## Executive summary

The review found one medium-priority dependency issue and two low-priority hardening gaps.
No critical issue or confirmed remote exploit was found in the reviewed Explain paths.
The Remotion dependency audit does contain high-severity upstream advisories.
The severity below reflects the demonstrated exposure in this repository.

Address finding 1 before publishing the new installer.
Include findings 2 and 3 in the same release if practical.
This report does not certify that the project is free of vulnerabilities.
No implementation fixes, commits, pushes, or changes to the live installation occurred during this review.

| ID | Severity in Explain | Finding | Priority |
| --- | --- | --- | --- |
| 1 | Medium; upstream advisories include High | The video toolchain contains vulnerable dependencies | Before publication |
| 2 | Low; conditional local attack | Installation preserves unsafe permissions on an existing interpreter pointer | Next installer release |
| 3 | Low; supply-chain hardening | Python installation lacks locally pinned artifact hashes | Next installer release |

## Scope and method

The review covered the current working tree on `codex/explain-installation-doctor`, including its untracked implementation files.
It covered the Bash bootstrap, Python installer, repair transactions, shortcuts, runtime builder, JavaScript renderer, React video example, and static HTML examples.
The project has local command-line tools and static pages, without an application backend.

The review used the security skill's general frontend and React guidance.
The skill has no matching Python CLI or Bash reference.
Those components received a direct review of execution, file permissions, paths, downloads, and rollback behavior.

Checks included source inspection, live advisory queries, installed dependency checks, existing tests, and an isolated permission reproduction.
The local reproduction used a temporary home and a harmless executable.
It did not change the user's active configuration.
No large memory-exhaustion payload was run.

## Critical findings

None confirmed within the checked scope.

## High findings

No high-severity attack against Explain itself was confirmed.
Finding 1 includes upstream high-severity advisories that still need attention.

## Medium findings

### 1. The video toolchain contains vulnerable dependencies

**Rule:** REACT-SUPPLY-001, dependency and supply-chain hygiene.

**Evidence:**

- [package.json](./examples/explain-video/package.json#L19) pins the Remotion packages to `4.0.532`.
- [package-lock.json](./examples/explain-video/package-lock.json#L3812) pins `zod` to `4.5.4`.
- [package-lock.json](./examples/explain-video/package-lock.json#L2623) pins `fast-uri` to `3.1.8`.
- Both transitive versions also exist in the active local video runtime.
- [install_runtime.py](./scripts/install_runtime.py#L499) installs this video lockfile with `npm ci` and disables its automatic audit.
- [validate.yml](./.github/workflows/validate.yml#L28) audits the diagram projects, but has no video audit step.

The live production audit reported 11 affected package entries: ten high and one moderate.
These entries represent five advisory records, rather than eleven independent flaws.
Most high entries inherit the same Zod advisory through Remotion packages.

**Impact and prerequisites:**

Zod can consume excessive memory while validating oversized invalid collections.
The advisory lists `4.6.6` as patched. [Zod advisory](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)

The fast-uri advisories concern URI normalization, equivalence, and scheme handling.
They list `3.1.9` as patched for the installed major version.
An application must use the affected behavior in a security-sensitive path for these flaws to cause harm.
Sources: [scheme decoding](https://github.com/advisories/GHSA-w74x-v6f9-j3xg), [path equivalence](https://github.com/advisories/GHSA-xhq7-xmqj-769h), [host confusion](https://github.com/advisories/GHSA-wjr9-j795-jxcr), [suffix scheme injection](https://github.com/advisories/GHSA-333x-w4r6-6crp).

The reviewed render scripts use fixed local files.
Captions use normal JSX escaping in [index.jsx](./examples/explain-video/src/index.jsx#L149).
No path from an attacker-controlled URL to an unsafe DOM operation was found.
Optional Remotion Studio adds HTTP routes, but the inspected routes include origin checks or input limits.
The review did not establish a remotely exploitable validation path through those routes.

**Recommended fix:**

Upgrade the aligned Remotion packages to a release with patched dependencies.
The current npm audit suggests `4.0.541`; verify its resulting dependency tree before choosing it.
Regenerate the lockfile.
Add a video dependency audit to CI.
Repeat the video render and decode checks after the update.

**Interim mitigation:** Keep render inputs trusted and local.
Do not expose Studio or a new rendering API to untrusted clients without a separate review.

**Confidence:** High that the vulnerable versions are present.
Their exploitation through Explain remains unconfirmed.

## Low findings

### 2. Installation preserves unsafe permissions on an existing interpreter pointer

**Rule:** Protect execution configuration from modification by other accounts.

**Evidence:**

- [install.py](./scripts/install.py#L117) preserves an existing file's mode in `add_file`.
- [install.py](./scripts/install.py#L224) requests `0600` for `launcher-python`, but that mode only applies to new files.
- The [launcher](./skills/explain/scripts/explain#L3) reads that pointer and executes its named interpreter.
- It does not check the pointer's ownership or write permissions before execution.

**Impact and prerequisites:**

Another local account could replace the interpreter path if existing file or directory permissions permit access.
The next `explain` command could then execute an attacker-selected program with the invoking user's rights.
This requires an already unsafe state location.
It is not a remote attack or a demonstrated exposure in the current installation.

**Reproduction:**

An isolated fixture created the existing pointer with mode `0666`.
The core installer completed without blockers and retained `0666`.
The fixture then replaced the pointer with a harmless executable's path.
The launcher ran that executable when invoked with `doctor --help`.
The result is saved in state-permission-repro.json (`output/reviews/security-2026-11-08/state-permission-repro.json`, local evidence).

The current user's actual pointer is owned by the user and has mode `0600`.
Its checked home and state directories are owned by the user and have mode `0755`.
These checked paths do not permit other accounts to write.

**Recommended fix:**

Enforce private permissions on execution state, including existing files.
Reject state locations writable by other accounts.
Validate the interpreter pointer before execution.
Define the policy for ACLs and shared directories explicitly.
Include symlink and concurrent replacement cases in the regression tests.

**Interim mitigation:** Keep the state directory under the user's protected home.

**Confidence:** High; the conditional execution path was reproduced.
The test simulated an unsafe permission setup without using a second local account.

### 3. Python installation lacks locally pinned artifact hashes

**Rule:** Verify downloaded dependency artifacts before trusting their contents.

**Evidence:**

- [requirements.lock.txt](./examples/explain-video/requirements.lock.txt#L1) pins 16 package versions without artifact hashes.
- [install_runtime.py](./scripts/install_runtime.py#L507) runs pip without `--require-hashes` or `--only-binary`.
- Its [requirements parser](./scripts/install_runtime.py#L277) accepts exact versions but does not support hash entries.
- The later [version check](./scripts/install_runtime.py#L302) checks package metadata, rather than downloaded artifact identities.

**Impact and prerequisites:**

A version pin does not independently approve a particular wheel or source archive.
Installation still trusts the configured package source for the artifact's contents.
A selected source distribution can also execute build code and resolve build dependencies.
No malicious Python package or compromised source was found during this review.

This is a hardening gap, rather than proof of a current exploit.
Pip recommends local hashes and binary-only installation for a more secure installation process. [Official pip guidance](https://pip.pypa.io/en/stable/topics/secure-installs/)

**Recommended fix:**

Record approved SHA-256 hashes for each supported platform's wheels.
Support those hashes in the requirements parser.
Require hash checking during installation.
Use binary-only installation where supported wheels exist.
Fail clearly when a supported platform lacks an approved artifact.

**Interim mitigation:** Keep the exact versions and use a trusted package source over HTTPS.

**Confidence:** High that artifact hashes are absent.
No evidence of tampering was found.

## Checks that passed

- All 126 Python tests passed during this review.
- All 15 diagram renderer tests passed during the delegated review.
- Repository validation and `git diff --check` passed.
- The evaluation suite validated 23 case definitions; live model trials were not run for this security review.
- The Pele production audit reported zero known vulnerabilities.
- The Pele PNG example audit also reported zero, including development dependencies.
- OSV returned no known advisories for the 16 exact Python requirements.
- A credential-pattern scan found no matches in 106 tracked and nonignored untracked text files.
- The scan excluded Git history and ignored outputs.
- All 311 package entries across the three npm lockfiles include HTTPS URLs and integrity values.
- The diagram renderer disables links, images, and custom icon markup.
- It limits source size, expanded edges, output size, dimensions, and render time.
- Its exclusive output creation preserves an existing destination file.
- Reviewed static examples use fixed data and safe text insertion.
- Installer subprocess calls use argument arrays, without shell evaluation of supplied arguments.
- Repair backups use private per-run directories and files.
- Checked package symlink escapes and ambiguous installations block changes.
- Rollback checks preserve unrelated concurrent edits in the tested cases.

Raw npm audit results and the permission reproduction are saved in the local evidence folder (`output/reviews/security-2026-11-08`, local evidence).
That folder remains ignored by Git.

## Limits and remaining trust

This was a source review and targeted test pass on macOS, not a formal penetration test.
The Linux installer was not executed during this review.
The review did not scan historical commits or all ignored media outputs.
It did not verify all hosting headers on the published website.
Missing hosting controls were not treated as demonstrated vulnerabilities without evidence.

The installer trusts the selected Explain source, system package managers, npm packages, and browser downloads.
Its Python virtual environment separates dependencies but does not restrict their operating-system privileges.
Package installation and video source execution use the current account's permissions.
The diagram worker provides resource limits, not an operating-system sandbox.
These trust boundaries remain relevant even after the listed fixes.
