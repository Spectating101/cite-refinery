# External topic discovery (pilot)

Run `PYTHONPATH=src python -m cite_refinery.external_knowledge_cli 'renewable energy'` or `cite-refinery-topics 'renewable energy'` after installing this branch. `--with-openalex` requests OpenAlex in addition to Wikidata; provider errors (including 429 responses) are reported as partial coverage.

This is a **read-only navigation source**, not a fourth authority layer. Returned labels and topic IDs **must not be imported as observed Practical problems, Academic evidence, Program solutions, qualified cross-layer links, or validated interventions**. The researcher must inspect actual studies, agencies and implementations separately.

Sources: [Wikidata MediaWiki API](https://www.wikidata.org/w/api.php), [OpenAlex Topics API](https://docs.openalex.org/api-entities/topics). Wikidata structured data is CC0; OpenAlex metadata access may be rate-limited. No bulk crawling, background refresh, credentials, or promotion is performed. The first experiment is to compare additional relevant source leads against the frozen semantic landscape, recording both false positives and genuinely new evidence.
