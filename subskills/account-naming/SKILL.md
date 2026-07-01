# Subskill: account naming + call triage

A model reads each call and says which buying company it is about, whether it is a real
customer/prospect call or internal, and which of the seller's people spoke. This is what lets the
linker join calls to deals and decide scope. It runs between normalize (Phase 3) and the final link
(Phase 6). Host-agent-first.

## Why this exists

`link.py` will not silently drop a call. Until every substantive call has been read and named, it holds
the conservation gate open and lists the unnamed calls. Titles lie and speech-to-text garbles names, so
a model must read the body of each call, not the filename.

## Steps (host-agent mode, the default)

1. First link pass, to find what needs naming:
   ```
   python3 scripts/link.py --workdir <dir>
   ```
   It writes `analysis/naming_worklist.json` (the calls to name) and reports the gate. A failed gate
   here is expected on the first pass.

2. Emit one naming task per call:
   ```
   python3 scripts/build_tasks.py naming --workdir <dir>
   ```
   This writes `analysis/tasks/naming/<call_id>.json`, each with a filled `prompts/account_naming.md`
   prompt and an `out_path`.

3. For each task, spawn a subagent given `task.prompt`. It returns ONE JSON record (the shape in
   `prompts/account_naming.md`). Write that record to `task.out_path`
   (`analysis/naming_out/<call_id>.json`). Run in parallel batches.

4. Collect the records into `analysis/call_company.json`:
   ```
   python3 scripts/merge_scores.py --workdir <dir>
   ```

5. Re-run the linker. The gate now passes and calls are joined to deals:
   ```
   python3 scripts/link.py --workdir <dir>
   ```

## Gate

Every substantive call has a record in `analysis/call_company.json`, and the second `link.py` run shows
no unaccounted calls. Calls the model marks `internal` or `postsale` are kept as context and excluded
from scoring; `external_customer` and `partner` presale calls are the scored set.

## Notes

- Be accurate on `org_participants` and `technical_explainers` (who carried the technical work on the
  call), and infer the `se_stage`. Phase 7 scores the technical explainers, and the stage decides which
  moves are due, so both must be right.
- The model must not invent a company. Genuinely unclear calls get `company: null`, `bucket: unknown`,
  and are reported, not guessed.
- API alternative: loop the same `analysis/tasks/naming/*.json` prompts through `engine/llm.py` and
  write each result to its `out_path`, then run `merge_scores.py` and the second `link.py`.
