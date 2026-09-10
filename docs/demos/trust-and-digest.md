# Explain trust and package digests

Use the GUI or `bcgov-find-extension` to compare the security extension's:

- source repository and exact revision;
- generated package-tree digest and file inventory;
- declared capabilities and generated policy result;
- named marketplace or domain review evidence.

Explain that the digest identifies the exact bytes presented for installation,
while the review status identifies evidence about that exact revision. A
publisher declaration is not the same as generated scan output or human
review. Use the terms **marketplace reviewed**, **domain reviewed**,
**unreviewed candidate**, and **unreviewed** precisely.

Do not use “safe”, “verified secure”, “approved”, or “guaranteed” as
substitutes for evidence. The demo must also state that a changed revision
requires a new digest and does not inherit prior review evidence.
