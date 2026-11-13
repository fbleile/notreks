# GitHub and anonymous release procedure

The repository is intentionally free of author names, institutional paths,
cluster usernames, and personal email addresses. `CITATION.cff` uses a neutral
placeholder until the paper is de-anonymized.

## First public repository

From a clean working tree, create an empty GitHub repository and configure it
as the only remote:

```bash
git remote add origin <github-url>
git push -u origin main
```

Before pushing, run:

```bash
make release-check
make package-check
git grep -n -I -E 'f\\.bleile|tum\\.de|/Users/|/dss/|ge86xim2' -- ':!*.lock'
```

The final command must produce no output. Publish the repository at a commit
that has passed the release checklist, then create an immutable tag for the
paper artifact.

## Anonymous paper repository

Use a separate anonymous GitHub repository or anonymous archive mirror. Do not
rewrite the scientific history after the paper is submitted. Instead, publish
the exact commit or tag used for the paper and cite that immutable identifier
in the anonymized paper's reproducibility statement.

When the paper is de-anonymized, update only the citation metadata and the
paper link in a separate release commit. The code, protocol, result schemas,
and experiment identities must remain unchanged.

## Paper integration

The paper should link to the repository release and the separate result
archive. The source repository supplies code, manifests, small smoke outputs,
and exact analysis commands; the result archive supplies large aggregate
tables and rendered figures. The two must record the same repository commit.
