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
- Treat full article text as restricted unless a license clearly allows the intended use.
- Summarize and transform; do not reproduce full articles or paywalled material.
- Treat market data rights separately from API access. API availability is not permission to redistribute raw quotes.
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

## Sample data

The bundled sample records are synthetic. They demonstrate the schema and workflow, not real-time market claims. Replace them with real source URLs before publishing content.
