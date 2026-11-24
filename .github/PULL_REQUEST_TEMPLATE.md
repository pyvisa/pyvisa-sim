Thanks for wanting to contribute to PyVISA-sim!

## Summary

Describe the user-facing change and why it is needed.

## News fragment

- [ ] User-visible changes should add a Towncrier fragment under `newsfragments/<issue>.<type>.rst` unless the PR carries the `no-news-required` label.
- [ ] For transport- or protocol-specific changes, optionally place the fragment in `newsfragments/<section>/<issue>.<type>.rst` using a configured section such as `asrl`, `gpib`, `tcpip`, `tcpip/vxi11`, `tcpip/hislip`, `tcpip/socket`, `usb`, `vicp`, or `prologix`.
- [ ] When a PR affects multiple transports or protocols, create one fragment for each affected section instead of combining them in a single entry.
- [ ] Chosen fragment type: `feature`, `bugfix`, `doc`, `removal`, or `misc`.
- [ ] If the PR does not require a changelog entry, add the `no-news-required` label instead of creating a fragment.

## Testing

Describe the exact validation you ran for this change.
