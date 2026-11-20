# F6 · Program edit: a copy-paste error in the recipe

**Mirrors:** editing and downloading PLC programs. **Plant:** someone edited the recipe-loading section "to fix silo 2", copied the line above, and forgot to change the index. The program was downloaded without comparing it to the last good backup.

**Inject:** upload `plc/faults/F6_batching_bad_edit.st` in OpenPLC (Programs → Upload) instead of `batching.st`, and start the PLC. In the soft-PLC: `python -m lab.run_softplc --f6`. **Repair:** upload `plc/batching.st` again.

## 0. Symptom (HMI)

- **No alarm at all.** The batch runs and completes normally.
- The Mixer HMI's batch table gives it away:

| | A | B | C | D | E |
|---|---|---|---|---|---|
| Recipe 1 (`R1_A…E`) | 800 | **500** | 400 | 200 | 100 |
| Target this batch | 800 | **800** | 400 | 200 | 100 |
| Actual | 796 | **796** | 396 | 196 | 95 |

The batch is 2 280 kg instead of about 2 000 kg, with 300 kg too much Material B. On a real line, quality would find it downstream, not the PLC.

## 1. Check the I/O

All I/O is healthy: silo 2 weighed exactly what the PLC asked for. The weighing system worked; the request was wrong.

## 2. Program online

- The target comes from step 5 (LOAD_RECIPE). Online, `TargetKg[2]` is 800 while `RecipeKg[2]` (= `HMI_R1_B`) is 500.
- In the program: `TargetKg[2] := RecipeKg[RecipeBase + 1];`. It should be `+ 2`.

## 3. Configuration (version control)

Compare the running program with the last known-good copy:

```
git diff --no-index plc/batching.st plc/faults/F6_batching_bad_edit.st
```

Exactly one logic line differs (the test `tests/test_st_consistency.py` checks this too).

## 4. Repair and prove

1. Restore the correct line (upload `plc/batching.st`), compile, start.
2. Run one test batch. The targets now match the recipe (800 / 500 / 400 / 200 / 100).

## Recording script (about 3 min)

1. "No alarm. The batch finished. But look at the table: recipe says 500 kilos of B, the target says 800."
2. "The scales are right: silo 2 gave exactly what it was asked for. So the request is wrong. That's the program."
3. Show the LOAD_RECIPE lines: "Silo 2 loads recipe entry plus one. Copy-paste from the line above."
4. Run the diff: "Against the last good backup, one line changed."
5. Upload the good program, run a batch: "Targets match the recipe."

**Lesson:** the PLC does exactly what it's told. Before you download an edit, compare it with the last good backup and run a test batch.
