## Description of Changes
A concise summary of what this pull request introduces or fixes.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] New vendor / platform support (adding vendor profiles or CLI commands)
- [ ] Documentation update
- [ ] Security / dependency patch

## Related Issue
Fixes #(issue number)

## Verification & Testing
- [ ] All automated tests pass locally (`python -m unittest discover tests`)
- [ ] Tested with live or mock network device output
- [ ] Verified UI rendering and responsiveness (if modifying frontend)

## Security & Credential Hygiene Checklist
- [ ] **ZERO CREDENTIALS**: Verified that no passwords, API tokens, private keys, or SSH credentials are in code, commits, or test fixtures.
- [ ] **DUMMY DATA ONLY**: Verified that all IP addresses, hostnames, and serial numbers in test fixtures are synthetic (RFC 5737 documentation IPs / dummy values).
- [ ] **SECRET SCRUBBING**: Verified that any new CLI command parsers mask sensitive configuration fields (`password`, `secret`, `community`).

## Licensing Agreement
By submitting this pull request, I confirm that my contributions are made under the terms of the [Apache License 2.0](file:///d:/Zenquix/NW_audit_tool/LICENSE).
