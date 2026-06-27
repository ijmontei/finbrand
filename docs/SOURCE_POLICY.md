# Source Policy

## Principle

Use automation for discovery and verification, not for copying. Every publishable story should include a source trail and enough original commentary to stand apart from a headline recap.

## Source hierarchy

| Priority | Source class | Use |
| --- | --- | --- |
| High | SEC EDGAR, BLS, Federal Reserve, FRED, issuer IR | Primary evidence and factual grounding |
| Medium | Licensed market data providers | Market reaction, price move, volume, sector context |
| Medium | GDELT, RSS, broad news indexes | Discovery, article velocity, corroboration hints |
| Low | Unofficial convenience libraries | Research aid and prototype fallback |

## Usage notes

- Store source URL, retrieval time, source type, license note, and provenance metadata on every item.
- Archive ingested source snapshots locally so later fact, rights, and editorial reviews can reconstruct what the system saw.
- Use a declared `SEC_USER_AGENT` for SEC EDGAR API access and respect SEC fair-access expectations.
- Use `FRED_API_KEY` for FRED observations and keep series citations attached to macro claims.
- Use `BLS_API_KEY` when available for better BLS API limits, and keep series IDs attached to inflation or labor claims.
- Treat full article text as restricted unless a license clearly allows the intended use.
- Summarize and transform; do not reproduce full articles or paywalled material.
- Keep owned-audience briefs source-cited and original; do not turn the newsletter into republished article excerpts.
- Treat GDELT and broad news indexes as discovery only; they do not clear the primary-source gate by themselves.
- Treat market data rights separately from API access. API availability is not permission to redistribute raw quotes.
- Treat imported market-data CSV rows as internal enrichment until the provider license explicitly allows the intended commercial display or redistribution.
- Record source/provider terms reviews before treating third-party data as publishable. API access alone is not a usage grant.
- Keep official source excerpts short and cite the source in the editor-facing package.
- Treat platform monetization as an editorial quality constraint: every draft needs original framing, owned visuals, and human judgment beyond a headline recap.
- Rotate editorial formats and style variants, but keep every variant anchored in the same source trail.

## Publishing gates

A story should not move to "ready" unless it has:

- At least one primary or first-party source, or a human override.
- A chartable signal.
- A caveat.
- Original commentary and visual transformation, not a templated recap.
- No individualized advice language.
- Clear disclosure metadata if paid promotion, sponsorship, affiliate, or referral compensation exists.
- No blocking approval checks; warning-level approval needs editor notes.
- A manual publish packet marked ready; auto-posting remains disabled.

## Human overrides

Primary-source overrides are exceptions, not normal workflow. They require an editor name, a specific reason, and an evidence URL or internal evidence reference. An override may downgrade the primary-source gate from blocked to needs-review, but it does not clear rights, claim, platform, advice-language, or disclosure checks.

## Source Terms

Use source-terms reviews to document provider rights. `approved_publish` means the reviewed terms allow the intended display or derived-data use, subject to recorded restrictions. `internal_only` means the data can help detection but should not appear in published output. `prohibited` blocks publication until the source is removed or replaced. `needs_review` keeps the story in rights review.

## Sample data

The bundled sample records are synthetic. They demonstrate the schema and workflow, not real-time market claims. Replace them with real source URLs before publishing content.
