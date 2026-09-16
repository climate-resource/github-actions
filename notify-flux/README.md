# Notify Flux

> [!WARNING]
> Deprecated and removed in the next major release.
> Flux polls for OCI deployment bundles, so remove this step from build workflows.

Calls a Flux `generic-hmac` Receiver after an image has been pushed.
The request body contains the published commit SHA.
The action needs Python 3 on the runner.

```yaml
- name: Notify Flux
  if: ${{ !github.event.pull_request.head.repo.fork }}
  uses: climate-resource/github-actions/notify-flux@v1
  with:
    receiver-url: ${{ secrets.FLUX_RECEIVER_URL }}
    receiver-token: ${{ secrets.FLUX_RECEIVER_TOKEN }}
    sha: ${{ github.event.pull_request.head.sha || github.sha }}
```

Run this step only after a successful image push.
If both secrets are absent, the action reports that Flux will poll instead.
A partially configured receiver or a failed request fails the step.
The action does not print the URL, token, signature or response body.
