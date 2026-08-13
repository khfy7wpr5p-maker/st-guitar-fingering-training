# Safety

- Parse untrusted XML with `defusedxml`.
- No network DTD/schema fetching.
- Reject unsupported string numbers, fret ranges, missing tuning, malformed durations, and impossible physical mappings.
- Permit a source XML pitch differing by exactly +12 semitones only when the complete selected stream consistently demonstrates written-guitar octave notation; store this mode explicitly.
- Never infer left-hand finger numbers from string/fret alone.
- No user upload or teacher correction is automatic training consent.
- Copyrighted/rights-unclear source files remain outside Git.
- Training/evaluation split is by source family, never by individual event.
- A validation result is not a production-quality claim.
- A true sealed benchmark requires fresh, separately controlled material not inspected during development.
