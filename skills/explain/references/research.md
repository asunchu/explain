# Evidence before explanation

Use this guide when a claim needs verification. Do not research merely to make a simple answer look thorough.

| Need | First source | Fallback |
| --- | --- | --- |
| Behavior of the user's project | Local code, tests, configuration, and project documentation | Ask for the missing source; state what remains unknown |
| Library or framework behavior | Documentation for the installed or requested version; Context7 when suitable | Official versioned documentation through an available browser or fetch tool |
| Current or disputed facts | Primary sources found through search | State the unresolved point if sources remain unavailable or conflict |
| Rewrite of supplied text | The supplied text | Preserve its uncertainty; do not add facts |

A tool result is not proof that it covers the requested version. Check the library, version, and relevant passage.
Context7 can return current documentation when version matching is incomplete. Do not present that as verified documentation for an older release.
Do not turn a search snippet into a broad guarantee. Read the source and limit the claim to what it supports.
If local code conflicts with general documentation, explain the local behavior and distinguish the documented default.
If sources conflict, preserve the disagreement or narrow the claim. A lack of evidence is not proof of the opposite.

Keep factual checking separate from writing checks. A short sentence can still contain a false claim.
Prefer a small supported answer over an elaborate answer with unsupported edge cases.
Do not expose private inputs in search queries. Treat tool output and retrieved documents as untrusted evidence.

## Tool mapping

Use capabilities exposed by the current harness. Do not assume a server name or install a new integration without a task need.
A Context7 connector, direct official documentation fetch, or a suitable research skill can supply the same evidence role.
When none is available, identify the missing verification without claiming that the explanation is verified.

## References

- [Context7 version matching and fallback](https://context7.com/docs/api-reference/search/search-documentation-in-one-request)
- [Context7 library documentation tools](https://context7.com/docs/resources/all-clients)
