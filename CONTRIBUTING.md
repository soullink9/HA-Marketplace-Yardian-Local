# Contributing to Yardian Local

Thanks for helping. This page is for anyone changing the code: where things live, the rules the code keeps,
how to check a change, and how to release one.

## Ground rules

- **Local only.** The integration talks to the controller's address the user enters, and nothing else. No cloud
  calls, update checks or analytics.
- **Every start has a duration.** Nothing may start a zone without a run time. That's what lets the controller stop
  a zone on its own when Home Assistant is down; it is the project's main safety promise.
- **Never water twice in a day.** The blueprint decides a day is handled from the automation's `last_triggered` and
  the integration's **Last watering** sensor. `async_mark_start` saves that time immediately (not with the usual
  delay) so it survives a power cut. Keep both when changing either side.
- **No helpers.** Users set everything in the UI; settings the integration needs (run times, flow rates) are its own
  number entities.
- **Saved data must keep loading.** `.storage/yardian_local.<entry_id>.water` holds `{"water": {zone: total},
  "last_start": iso}`; `async_load` in `coordinator.py` also reads a bare `{zone: total}` file. Entity unique IDs
  (`<yid>_<key>`) must never change, or users lose their entities and Energy history.
- **One dependency.** `pyyardian`, required in `manifest.json` as a minimum version (`>=`), never an exact pin.
  Home Assistant Core ships it for its own Yardian integration, so Core's version is the one installed, and
  `hassfest` fails on an exact pin. Raise the minimum only when the code needs something newer.

## Where things live

The [Development](docs/Development.md) page has the full file map. The usual places to make a change:

| To change | Look in |
|---|---|
| Poll interval, save timing, defaults | `custom_components/yardian_local/const.py` |
| Polling, the water estimate, saved data, last watering | `coordinator.py` |
| What a kind of entity shows | the platform file: `switch.py`, `number.py`, `sensor.py`, `binary_sensor.py`, `button.py` |
| Actions | `services.py` (`notify`), `switch.py` (`start_irrigation`); describe them in `services.yaml` and `translations/en.json` |
| Setup form | `config_flow.py`, labels in `translations/en.json` |
| The schedule, skips, recovery and notifications | `blueprints/automation/yardian/yardian_lawn_schedule.yaml` (its header comment maps the flow) |

**Adding an entity:** add the class to the matching platform file with a new, permanent `key`, read its value from
`coordinator.data` (or a coordinator attribute for Home Assistant-side values), and list it on the
[Entities and Actions](docs/Entities-and-Actions.md) page.

**Changing the start time calculation:** it exists twice in the blueprint (the `schedule` trigger and the `start_ts`
variable). Change both the same way; `tests/test_blueprint.py` fails if they differ.

## Checking a change

You need Python 3.13 or newer (Home Assistant 2026.9 itself runs on 3.14, which is what the workflows use).

```sh
pip install -r tests/requirements.txt
```

| Command | Time | When |
|---|---|---|
| `ruff check custom_components tests` and `ruff format custom_components tests` | seconds | every change |
| `python3 tests/test_blueprint.py` | seconds | any blueprint change |
| `python3 tests/test_release.py` | seconds | any change to `scripts/` or the release workflows |
| `python3 scripts/build_package.py` | seconds | before a release: builds `dist/yardian_local.zip`, checks it installs, and copies the blueprint next to it |
| Install on a test Home Assistant and run one zone for a minute | a few minutes | before every release |

Gitea's runner runs ruff, the blueprint check, the release tests and the zip build on every push
(`.gitea/workflows/test.yml`). On GitHub the same checks run plus Home Assistant's `hassfest` and the Marketplace's
own checks, which come from GitHub and can only run there. [tests/README.md](tests/README.md) lists what each test
checks. There are no automated tests against a real or simulated controller yet; a pull request adding them is
welcome.

Code style: `ruff` settles formatting and import order (see `pyproject.toml`). Every module, class and function has a
docstring, and comments say why, not what.

## Documentation

[README.md](README.md) is the front page, and every other page lives in [`docs/`](docs). When a change alters
something a page describes, update that page in the same commit.

## Standards for every change

- **Readable over clever.** Write code a newcomer can follow on the first read. Prefer a few plain lines with a named
  variable to a dense one-liner, a nested conditional expression, or a trick that needs a comment to decode.
- **Comment the why.** Every function and class has a docstring. Comments explain why the code does something
  non-obvious (a quirk of the device or service, a Home Assistant rule, a deliberate trade-off), not what each line
  does.
- **Keep names consistent.** Follow the names already used in the integration: the same words for
  the same things, Home Assistant's conventions for entities and config entries, `snake_case` for Python names and
  `camelCase` for JavaScript.
- **Keep the docs in step.** When you change a function, class or behaviour, update its docstring, its comments and the
  pages under `docs/` (and the README) that describe it in the same commit.
- **Keep the tests green.** Every change keeps existing behaviour and passes all of the tests. When you
  fix a bug, add the situation that caused it to the tests so it stays fixed.
- **No new dependencies without approval.** Don't add a third-party library (to a `manifest.json`, a
  `requirements.txt` or CI) without asking in an issue first. This page says what it already depends on and why.

### Test layout

The tests use these names:

```
tests/
  stubs.py                stand-ins for Home Assistant and the libraries the integration uses
  test_integration.py     the real integration against the stand-ins and a fake device or service
  test_<subject>.py       any other checks (test_engine.py, test_blueprint.py, test_live_proxy.py)
  test_<subject>_soak.py  a long simulation: it takes a length as an argument, and CI runs a short one
  fake_<service>.py       a fake device or service, when it's too big to live inside the test
  requirements.txt        what the tests need beyond Python, if they need anything
```

Every `test_*.py` is a plain script, not a pytest suite: run it with `python3` from the repository root, and it
exits non-zero if any check fails.

### The Marketplace

`hacs.json` at the root is the Marketplace's file: the name it lists and the oldest Home Assistant version the
integration works with. Keep that version in step with the README's requirements.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/): a type, an optional scope, then a short summary in
the imperative.

```
feat: add a diagnostics download
fix: keep the last value when the service is briefly unreachable
refactor: split the coordinator's update into steps
docs: explain the safety settings
test: cover a reply with a missing field
chore: update the CI actions
```

## Releasing

Gitea is the main copy of this repository. It push-mirrors to GitHub, which is the public copy: the Marketplace
installs from GitHub's releases, so every link in the docs and release notes points there.

1. Bump `version` in `custom_components/yardian_local/manifest.json`. Versions go up together: there is only this
   one (the blueprint has no version of its own).
2. Add the release to the top of [CHANGELOG.md](CHANGELOG.md), under a heading `## X.Y.Z (date)` (move what's under
   `## Unreleased` into it).
3. Run the checks above, and try the release on a real controller.
4. Commit and push to Gitea, then publish with Gitea's **Release** workflow (`.gitea/workflows/release.yml`),
   either way:
   - **Actions → Release → Run workflow**, and enter the version without the `v` (for example `1.2.1`). It
     creates the tag `v1.2.1` on the commit it releases.
   - or push a version tag: `git tag v1.2.1 && git push origin v1.2.1`.

   The workflow checks the version matches the manifest and `CHANGELOG.md` (`scripts/release_notes.py`), runs every
   check, builds `yardian_local.zip` and checks it installs as `custom_components/yardian_local/`
   (`scripts/build_package.py`), and publishes the release on Gitea with the zip, the blueprint
   (`yardian_lawn_schedule.yaml`) and notes: install steps, then that version's changelog section
   (`scripts/publish_gitea_release.py`). A version with a suffix (`-beta`) is published as a pre-release. If any
   check fails, nothing is published. Running it again for the same version updates the release and replaces its
   files.

5. Gitea's push mirror then sends the commits and the new tag to GitHub, at its next push (every 8 hours). Every push
   from it starts GitHub's own **Release** workflow (`.github/workflows/release.yml`), which publishes each version
   tag that has no GitHub release yet: the same checks, then the same files (the builds are repeatable, byte for
   byte), title and notes, so GitHub's releases match Gitea's. The Marketplace picks it up from GitHub. If GitHub is
   down, the mirror catches up later; the Gitea release is already done. Don't make releases or tags on GitHub
   itself: the mirror deletes tags Gitea doesn't have, and GitHub follows Gitea on its own.

The Gitea workflows use no actions (`actions/checkout` and the like download from GitHub): each job runs in a plain
image from Docker Hub (`python:3.14-bookworm`) and fetches the code from Gitea with git, so testing and releasing
keep working when GitHub can't be reached. Only the checks' packages (`tests/requirements.txt`) come from PyPI. When
the runner's jobs can't reach Gitea at its public address (a runner on the same Docker network as Gitea, say), set
an Actions variable `GITEA_INTERNAL_URL` to the address they can reach (`http://gitea-server:3000`); both workflows
and the publish script use it.

Keep every tag on Gitea: the push mirror makes GitHub's tags match Gitea's, so a tag missing from Gitea is deleted on
GitHub, and the GitHub release on it turns into a draft.

## Reporting bugs

Open an issue with your Home Assistant version, the Yardian Local version, your controller model, what you did and
what you expected. Two things help most: the log (**Settings → System → Logs**, search for `yardian_local`) and, for
anything the controller reports, the diagnostics file (**Settings → Devices & services → Yardian Local → ⋮ →
Download diagnostics**; identifiers are removed). For a schedule problem, add the automation's trace
(**Settings → Automations**, open it, ⋮ → **Traces**).

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
