# Git receipt

The active Windows repository is `D:\Final Year Project`, branch `main`. The original local implementation tip `4c55dad` was imported with its history and both original local branch tips are retained under `migrated/`. Two in-progress local oracle files were preserved from the active worktree, then included with the verified oracle repair. The independent historical workspace was preserved separately and its Python harness was ported.

| Commit | Purpose |
| --- | --- |
| `4abe358` | Preserve byte-checked fixture and fix Python 3.12 regression portability. |
| `450dbeb` | Prevent false certificates caused by narrow intervals and floating-point cancellation. |
| `dcd2e7b` | Port historical and Stage 26 verification, pin the environment, and correct switching aggregation. |
| `3b50437` | Require the Stage 26 smoke to perform and replay both acquisition types. |

This report is in the final documentation commit. Its hash is available with `git log -1 --oneline -- preflight_reports`.

The new private remote is `origin` at [Upeka-Wihanga/robust-food-carbon-certification-fyp](https://github.com/Upeka-Wihanga/robust-food-carbon-certification-fyp). The proposed unsuffixed name was taken. The existing GitHub repositories were left untouched. The private remote receives the active `main` branch. Raw inputs, the locally archived review ZIPs, caches, and generated outputs are excluded.
