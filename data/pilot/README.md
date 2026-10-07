# Pilot data — NOT FOR EVALUATION

These are the two pilot runs from ticket E1-15 (`schedules/pilot.yaml`), kept to check the
testbed's repeatability before the corpus run. **This data is never used for evaluation.**

Pilot data may be used to develop the EPIC-3 normalizers (C-19), but **never** to tune detectors
(record §7.1: detectors are tuned on training-split or benign calibration data only) and **never**
to compute any reported metric. The repeatability report is in `docs/pilot/repeatability.md`.

`run1/` and `run2/` are the two runs (git-ignored; large pcaps). Only this README is committed.
