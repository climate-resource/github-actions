import { appendFileSync, existsSync, readFileSync } from "node:fs";
import { cpuRequest, memoryLimit, memoryPeak, sample } from "./cgroup.mjs";

const { STATE_pid: pid, STATE_log: log } = process.env;

if (pid) {
  try {
    process.kill(Number(pid));
  } catch {
    // The sampler already exited.
  }
}

const report = () => {
  if (!log || !existsSync(log)) return;
  const samples = readFileSync(log, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
  samples.push(sample());
  if (samples.length < 2) return;

  const first = samples[0];
  const last = samples.at(-1);
  const wallSec = (last.at - first.at) / 1000;
  const cpuSec = (last.cpuUsec - first.cpuUsec) / 1e6;

  const rates = samples
    .slice(1)
    .map(
      (s, i) =>
        (s.cpuUsec - samples[i].cpuUsec) / 1000 / (s.at - samples[i].at),
    )
    .sort((a, b) => a - b);
  const quantile = (q) =>
    rates[Math.min(rates.length - 1, Math.floor(q * rates.length))];

  const gib = (bytes) =>
    bytes === undefined ? "none" : `${(bytes / 2 ** 30).toFixed(1)} GiB`;
  const cores = (n) => (n === undefined ? "unknown" : n.toFixed(1));
  const minutes = `${Math.floor(wallSec / 60)}m ${Math.round(wallSec % 60)}s`;

  const request = cpuRequest();
  const mean = cpuSec / wallSec;
  const limit = memoryLimit();
  const peak = memoryPeak() ?? Math.max(...samples.map((s) => s.memory));
  const anonPeak = Math.max(...samples.map((s) => s.anon));
  const waiting = ((last.waitUsec - first.waitUsec) / 1e6 / wallSec) * 100;
  const job = process.env.GITHUB_JOB;

  appendFileSync(
    process.env.GITHUB_STEP_SUMMARY,
    [
      `### Resources: ${job} on ${process.env.RUNNER_NAME}`,
      "",
      "| | |",
      "| --- | --- |",
      `| CPU request | ${cores(request)} cores |`,
      `| CPU used | mean ${cores(mean)}, p50 ${cores(quantile(0.5))}, p90 ${cores(quantile(0.9))}, max ${cores(rates.at(-1))} cores |`,
      `| CPU time | ${Math.round(cpuSec)} s over ${minutes} |`,
      `| Waiting for CPU | ${waiting.toFixed(0)}% of wall time |`,
      `| Memory peak | ${gib(peak)} including page cache, ${gib(anonPeak)} anonymous |`,
      `| Memory limit | ${gib(limit)} |`,
      "",
    ].join("\n"),
  );

  console.log(
    `::notice title=Resources (${job})::CPU mean ${cores(mean)}, p90 ${cores(quantile(0.9))} of ${cores(request)} requested. ` +
      `Memory peak ${gib(peak)}, ${gib(anonPeak)} anonymous, of ${gib(limit)}. ${minutes}.`,
  );
};

try {
  report();
} catch (error) {
  console.log(`::notice::Resource usage is not reported: ${error.message}`);
}
