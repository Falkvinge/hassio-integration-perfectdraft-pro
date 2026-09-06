## Context

`sensor.py` loads `keg_catalog.json` once at import and resolves the machine's reported product ID through it:

```python
_KEG_CATALOG: dict[int, str] = _load_keg_catalog()

def _get_keg_name(data: dict) -> str | None:
    product_id = _get_keg_product_id(data)
    if product_id is None:
        return None
    return _KEG_CATALOG.get(product_id)
```

The lookup is generic, so growing the catalog needs no code change. `_load_keg_catalog` already swallows `OSError`/`ValueError` and degrades to an empty dict, so a malformed file costs the `Keg` sensor its value but does not break the integration.

The upstream file has 86 entries. @brettjenkins' fork has 114. A content-level tree diff between `master` and the fork confirms the catalog is the only substantive difference in `custom_components/`: `keg_detection.py`, `sensor.py`, `coordinator.py`, `api.py` and `const.py` are byte-identical, and the `config_flow.py` / `strings.json` / `translations/en.json` differences are all the fork lacking our September reauth work. GitHub's "38 ahead / 46 behind" is misleading — the merge-base is `17c0551`, from before v0.1, because the GitHub mirror's history was rewritten at some point.

Provenance of the added data, from the fork's commit `0982d20`: the product IDs cannot be queried in bulk from the PerfectDraft API, so each was observed directly from a machine with that keg fitted. The same mapping drives the seemy.beer tap sign in production.

## Goals / Non-Goals

**Goals:**

- Every keg the PerfectDraft app can select resolves to a name, including discontinued kegs that may still be sitting in a machine.
- The four factually wrong names on `master` are corrected.
- The `entities` spec describes the `Keg` and `Keg Product` sensors, which PR #2 shipped unspecified.
- The diff is legible: only real data additions, no reformatting noise.

**Non-Goals:**

- Any change to how an unmapped ID is reported. It stays `None` (sensor unknown).
- Any change to catalog loading, caching, or file format.
- Normalising the eleven styling-only name differences.
- Adopting the fork's `hacs.json` or manifest version.

## Decisions

**Take the fork's file wholesale rather than merging entry-by-entry.**
The fork's version is a strict superset of ours except for the four corrections, and it preserves our formatting convention (no indentation, numeric key order). Copying the file gives the same result as a hand-merge with less room for transcription error, and the resulting diff is reviewable line-by-line anyway. Alternative considered: cherry-pick `0982d20`. Rejected because the histories share only a pre-v0.1 merge-base, so a cherry-pick would drag in unrelated context and conflict; the file is self-contained data and copying it is cleaner than fighting git.

**Accept the four name corrections, reject the eleven styling changes.**
The corrections fix real errors: `32814` displays a beer that no longer exists under that name, and three entries carry shop-listing cruft (`Short Date`, `6L Keg`, a 2024 best-before date) that is not part of the beer's name. The styling differences (`Trooper`/`TROOPER`, `St`/`Saint Feuillien`) are cosmetic, the current spellings match the shop, and changing them would churn the diff for no user benefit. This matches the fork author's own reasoning.

**Close the spec gap in this change rather than deferring it.**
PROJECT_HYGIENE §3 says every changed line must trace to the request, which argues for touching only the catalog. But the catalog's behaviour cannot be specified without a `Keg name sensor` requirement to attach it to, and none exists — PR #2 added two sensors and the catalog file without updating `openspec/specs/entities/spec.md`. Writing the requirement is therefore a prerequisite of specifying this change, not a drive-by. Alternative considered: a separate `spec-sync-pr2` change. Rejected as ceremony for two requirements that this change needs anyway.

**Verify against real machine data before trusting the additions.**
The names are asserted, not verifiable from our side — we have one machine and cannot confirm 28 IDs we have never seen. The mitigation is not to re-verify each entry (impossible) but to bound the blast radius: confirm the file parses, confirm entry count and key ordering, confirm no existing ID changed except the four intended, and confirm our own machine's current keg still resolves correctly. A wrong name in an entry nobody has is inert.

**No version bump beyond patch.**
Adding catalog data changes no behaviour contract and no requirement that existing users depend on. `0.3.2` is the honest number. Note that the fork is at `0.4.1` and PR #2 briefly set `0.4.0`; `0f3b4c2` deliberately renumbered to `0.3.1` because no `v0.4.0` tag was ever cut. Continue from `0.3.1`.

## Risks / Trade-offs

**A backported name is wrong for an ID we cannot check** → Worst case is a mislabelled `Keg` sensor, which is strictly better than the blank it shows today. The provenance is credible (observed from machines, running in production on seemy.beer) and the four corrections it makes to our own data are independently checkable against shop listings. Accept.

**Hand-editing 114 JSON entries introduces a syntax error or duplicate key** → Copy the file rather than retyping entries, then assert `len(json.load(...)) == 114` and that Python's parse succeeds. A duplicate key would silently collapse and change the count, so the count assertion catches it.

**The four corrections surprise a user whose automation matches on the `Keg` sensor's string** → Real but unavoidable; the current strings are wrong. Three of them contain a 2024 best-before date or a pack size, which no sane automation would match deliberately. Call the corrections out in the release notes.

**The catalog keeps drifting as PerfectDraft adds products, and nothing records where these names came from** → Out of scope here, but worth its own change. Today the only record that these entries were measured rather than guessed is a commit message on someone else's fork. Options for later: a `_meta` key in the catalog, or making an unmapped ID surface the raw product number so users can report gaps.

## Open Questions

- Should the release notes list all 28 additions, or just the four corrections and a count? Leaning toward the latter with a link to the diff.
