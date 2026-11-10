# Report resource usage

Samples the job container's cgroup every 5 seconds, from this step to the end of the job.
When the job ends, pass or fail, it writes a table to the job summary and a one-line notice to the run page.

```yaml
steps:
  - uses: climate-resource/github-actions/resource-usage@v1
  - uses: actions/checkout@v6
```

Put it first so it measures the whole job.

The report holds:

- the CPU request, on Kubernetes runners only;
- mean, p50, p90 and max cores used, and total CPU time;
- the share of wall time any task spent waiting for CPU;
- the memory peak including page cache, the anonymous memory peak, and the memory limit.

Use it to size runner pools: a job whose p90 sits above its request competes for CPU,
and one whose anonymous peak nears its limit risks being OOM-killed.

## Limits

- It needs cgroup v2 with a private cgroup namespace, as Kubernetes runner pods and `container:` jobs have.
  On a plain VM runner it leaves a notice and reports nothing.
- The CPU request is read back from `cpu.weight` using runc 1.3's mapping.
  An older runtime that uses the linear mapping reports a higher request than it set.
- The anonymous memory peak is sampled, so spikes shorter than 5 seconds can be missed.
  The peak including page cache comes from `memory.peak` and is exact.
- Errors never fail the job. They turn into a notice.

## Development

The tests need a cgroup v2 container and skip elsewhere:

```bash
docker run --rm -v "$PWD/resource-usage:/a:ro" node:24-slim node --test /a/resource-usage.test.mjs
```
