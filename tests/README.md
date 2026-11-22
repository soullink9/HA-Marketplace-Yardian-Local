# Tests

Run everything from the repository root. Each test is a plain Python script, not a pytest suite: it prints what it
checks and exits non-zero if anything failed. These are the commands the Test workflow runs:

```sh
pip install -r tests/requirements.txt
python3 tests/test_blueprint.py
python3 tests/test_release.py
python3 tests/test_integration.py
```

| Script | What it checks |
|---|---|
| `test_blueprint.py` | Static checks for the watering blueprint |
| `test_integration.py` | The integration's own code against stand-ins for Home Assistant and a fake controller (`stubs.py`): `yardian_local.notify` only ever calls `notify.` actions, malformed controller answers mark entities unavailable instead of crashing, damaged saved water totals and restored settings are ignored, and the diagnostics file holds no identifiers or network details |
| `test_release.py` | The release scripts in `scripts/`: the version check and notes, building and checking the zip, publishing to a fake Gitea server, and working out which releases GitHub still needs |

[CONTRIBUTING.md](../CONTRIBUTING.md#checking-a-change) says which to run for which change, and how long each takes.
The blueprint check reads the file without running it, the integration check runs against stand-ins rather than Home Assistant, and nothing here talks to a controller, so try changes on a
real Home Assistant and a real controller too.
