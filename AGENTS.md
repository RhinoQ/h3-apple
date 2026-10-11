# Working rules

- Keep one product runtime. Develop changes on candidate branches, preserve
  unrelated edits, and validate the installed wheel before a release.
- Use an explicit project Conda interpreter for Python and its `-m pip` for installs.
- Local commits are autonomous. Publish only within the user's authorized scope.
  Downloads above 20 GB require explicit consent.

## Documentation style

Maintain these rules in both the research and product AGENTS.md files.
Update both copies together.

- Serve users and contributors: installation, requirements, interfaces, examples,
  measured performance, quality limits, development and licenses.
- Write concise, idiomatic English. Lead with a concrete user benefit and the
  shortest working example. Link optional and technical details.
- Explain what the product delivers and what we contributed. Describe reused
  community ideas/code and our improvements plainly; retain precise attribution.
- Keep research IDs, internal process, abandoned features and same-version
  reinstall advice out of introductory copy. Keep research process, maintenance
  records and collaboration rules internal; link technical evidence from
  contributor documentation.
- Show attractive, representative media with its actual generation and
  post-processing settings. Performance headlines must name the measured
  configuration, hardware and timing scope. A faster configuration's time must
  not imply that a showcase's extra processing is included.
- Use one recommended installation path. Apply the same style to README, guides,
  release notes and benchmark pages, and verify every published link.
- Keep homepage usage to installation, generation and optional super-resolution.
  Put mode choices, decoder settings and model directories in advanced documentation.
- Concision must preserve reproducible inputs, configuration, source identities,
  measurements, failures, review scope, upstream attribution and licenses.
- Before delivery, keep affected documentation, examples and CLI/API help
  consistent with actual behavior and defaults. Remove stale guidance and code
  confirmed to have no remaining callers or entry points. Preserve required
  compatibility guards and versioned historical evidence.
