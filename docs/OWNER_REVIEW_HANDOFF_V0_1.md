# Owner-review handoff: completion pass

This pass closes the intake-to-owner-to-curator handoff. It does not complete the
solver workspace, verify an actual owner, launch a public service, or alter the
Commons/Public-Good ownership boundary. `main` and the consolidation branch are
unchanged by this stacked branch.

## What changed

The existing `prototype/review.html` now accepts both
`problem-owner-intake-review/v0.1` and `problem-review-pack/v0.1`. Intake-specific
questions and proposed-work decisions have their own visible fields. The earlier
owner/reviewer/solver flow remains supported.

A curator can generate a **single HTML file** containing the minimum-necessary
review pack and the same tested UI. No account, JSON editing, API integration,
remote fonts, or application server is needed by the recipient. The page does not
send anything automatically. It has no network transport and the generated page
blocks connections through Content Security Policy. A public-source link, when
present, opens only on an explicit user click.

Answers can be saved as a draft file and reopened. Incomplete drafts remain
undecided. Changing an answer after preparing a final response invalidates the
old export; a failed file load also clears the previous review and export state.
There is no silent localStorage persistence of potentially sensitive responses.

## Issuing a review

From an editable repository installation:

```sh
python -m pip install -e .
problem-intake owner-review \
  pilot/intake/yzu-yongfeng-after-school.v0.1.json \
  --steward YOUR_CURATOR_ID \
  --out /your/private/pilot/issued-review.json \
  --html-out /your/private/pilot/owner-review.html
```

Keep `issued-review.json` in the curator's private working area. Share the HTML
only through an agreed channel. This tool neither sends nor publishes the file.
The browser can also load the issued JSON through the normal review page.

For a non-editable installation, supply `--assets-dir` pointing to the matching
repository `prototype/` assets. The generator fails explicitly when assets are
missing; it does not produce a broken page that silently references them.

The source listing in the example remains **unconfirmed**. It is a demonstration
input, not an institutional endorsement, current verified demand, or permission
for direct activity with participants.

## Returning a review

The owner selects currentness and role answers, reviews the formulation, marks
proposed work as useful to explore / do not proceed / not assessed, and supplies
corrections or resource information. Final decisions are confirm, reframe,
stale, already resolved, or decline. A negative review is a valid result.

`Prepare response` validates the answers but does not send them. `Save completed
review` creates a JSON file; the recipient returns that file through the agreed
channel. They do not have to read or edit JSON.

```sh
problem-intake validate-owner-review returned-review.json \
  --original /your/private/pilot/issued-review.json --require-complete

problem-intake record-owner-review returned-review.json \
  --original /your/private/pilot/issued-review.json \
  --actor YOUR_CURATOR_ID \
  --receipt-ref YOUR_PRIVATE_RETURN_REFERENCE \
  --out /your/private/pilot/owner-return.json
```

**Use the retained original**, not another purported original supplied with the
response. Every non-response field must match it: case identity, formulation,
rubric, proposed work, source, and instructions. This catches stale or substituted
versions even when a problem ID is unchanged. Hashes check consistency; they are
not signatures and do not establish who completed the review.

The receipt is exclusive-create (no overwrite), private-mode on POSIX systems,
and `pending-curator-decision`. It explicitly does not verify respondent identity,
confirm the owner, open work, commit funding, or grant authority. Those remain
separate human/operations decisions. Do not put real receipts in the public repo.

## Validation improvements

- Fixed decision choices; a response cannot supply its own permission list.
- Non-empty rubric; binary integer scores, not strings, booleans or out-of-range values.
- Actual booleans for currentness, owner-role agreement and material reframing.
- Draft structure validity is separate from completed-return admissibility.
- Work decisions must reference known, unique IDs and cannot conflict.
- Stale needs / incorrect owner roles / material reframing cannot coexist with confirmation.
- Private source locators are omitted from review packs.
- HTML-significant characters in embedded data are escaped; rendering uses text nodes.

## Reproduction and evidence boundary

```sh
python -m unittest discover -s tests -v
python -m pip install playwright==1.58.0 jsonschema==4.25.1
python -m playwright install chromium
python scripts/check_owner_review_contracts.py
python scripts/check_owner_review_browser.py --out /tmp/owner-review-proof
```

The dedicated GitHub workflow tests actual file:// and HTTP loading, file
upload/download, draft recovery, all five final decisions, malformed input,
script injection, legacy audiences, desktop/mobile layout, and the real CLI
return path. Screenshots and synthetic test returns are stored as short-lived
artifacts. All completed test responses are **synthetic**, not conversion data.

`--in-memory` exists for managed browsers that disallow local navigation. It
exercises DOM/file controls but is not evidence of URL or file:// loading. The
normal CI path must run without that switch before claiming the full handoff.

## Next operating step

Use the offline file in one curator/owner rehearsal; verify identity through the
existing trusted relationship. Process a real correction or decline before
opening any solver work. Then finish the next concrete seam: owner-approved
project brief -> contributor workspace -> artifact -> independent review.
Do not expand grant discovery, payments, or institutional tenancy for this pass.
