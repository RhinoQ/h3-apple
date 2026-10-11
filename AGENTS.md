# Working rules

- Keep one product runtime. Develop changes on candidate branches, preserve
  unrelated edits, and validate the installed wheel before a release.
- Use an explicit project Conda interpreter for Python and its `-m pip` for installs.
- Preserve experimental inputs, measurements and failures. Keep research records
  separate from user documentation; link reproducible evidence where useful.
- Local commits are autonomous. Publish only within the user's authorized scope.
  Downloads above 20 GB require explicit consent.

## Documentation style

- Write concise, idiomatic English. Lead with a concrete user benefit and the
  shortest working example. Link optional and technical details.
- Explain what the product delivers and what we contributed. Describe reused
  community ideas/code and our improvements plainly; retain precise attribution.
- Keep research IDs, internal process, abandoned features and same-version
  reinstall advice out of introductory copy.
- Show attractive, representative media with its actual generation and
  post-processing settings. Performance headlines must name the measured
  configuration, hardware and timing scope. A faster configuration's time must
  not imply that a showcase's extra processing is included.
- Use one recommended installation path. Apply the same style to README, guides,
  release notes and benchmark pages, and verify every published link.
