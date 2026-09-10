# Browse and install a security extension

1. Build and serve the generated site:

   ```bash
   make generate
   make docs
   make serve
   ```

2. Open `http://localhost:8000/catalog.html`, search for **repository
   hardening**, and filter to the `security` specialty.
3. Open the result and read the purpose, prerequisites, capabilities, source
   revision, package digest, policy result, and review status.
4. Follow the displayed guided installation command only after confirming the
   exact revision and digest. The page does not silently install anything.
5. Record the installation result locally; do not upload a receipt or
   credentials.

Expected evidence is the same generated record shown by
`bcgov-find-extension`: `bcgov-public/repo-hardening`, the security specialty,
declared capabilities, source, digest, policy version, and marketplace review
language.

Reset by stopping the local server and deleting only the local installation
created for the demo.
