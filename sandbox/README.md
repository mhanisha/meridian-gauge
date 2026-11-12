# Sandbox and test runner (guide step 1)

**Owners:** Neetu (container, `Dockerfile`, start/stop), Keerthana (test logic, `runner.py`).

A sealed Docker container where xarray's tests run with no network, plus one function that
reports exactly which tests passed. The same runner has two modes:

- **Answer-key mode:** find the tests that fail before the change and pass after it.
- **Grade mode:** apply a model's patch, then the hidden tests, and write `result.json`.

Done when (see the guide for detail):
- [ ] xarray's tests run with `--network none --memory 4g --cpus 2 --user 1000:1000`
- [ ] answer-key mode on `b3f5db3728` keeps tests that fail before and pass after
- [ ] grade mode marks the real commit's change solved and an empty patch not solved
