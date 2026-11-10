import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { available } from "./cgroup.mjs";

const here = import.meta.dirname;
const skip =
  !available() && "needs a cgroup v2 container, such as a `container:` job";

const run = (script, env) =>
  execFileSync(process.execPath, [join(here, script)], {
    env: { ...process.env, ...env },
    encoding: "utf8",
  });

const state = (file) =>
  Object.fromEntries(
    readFileSync(file, "utf8")
      .trim()
      .split("\n")
      .map((line) => line.split("="))
      .map(([key, value]) => [`STATE_${key}`, value]),
  );

// Only samplers logging under this test's directory, not the one the job itself runs.
const samplers = (dir) =>
  readdirSync("/proc")
    .filter((pid) => /^\d+$/.test(pid))
    .filter((pid) => {
      try {
        const cmdline = readFileSync(`/proc/${pid}/cmdline`, "utf8");
        return cmdline.includes("sampler.mjs") && cmdline.includes(dir);
      } catch {
        return false;
      }
    });

const job = () => {
  const dir = mkdtempSync(join(tmpdir(), "resource-usage-"));
  return {
    RUNNER_TEMP: dir,
    GITHUB_STATE: join(dir, "state"),
    GITHUB_STEP_SUMMARY: join(dir, "summary"),
    GITHUB_JOB: "test",
    RUNNER_NAME: "local",
  };
};

test(
  "writes a summary and a notice, then stops the sampler",
  { skip },
  async () => {
    const env = job();
    run("main.mjs", env);
    await new Promise((resolve) => setTimeout(resolve, 1500));

    const output = run("post.mjs", { ...env, ...state(env.GITHUB_STATE) });

    assert.match(output, /::notice title=Resources \(test\)::CPU mean/);
    const summary = readFileSync(env.GITHUB_STEP_SUMMARY, "utf8");
    assert.match(summary, /### Resources: test on local/);
    assert.match(summary, /\| Memory peak \| \d+\.\d GiB/);
    assert.deepEqual(samplers(env.RUNNER_TEMP), []);
  },
);

test("stops the sampler even before it has logged a sample", { skip }, () => {
  const env = job();
  run("main.mjs", env);
  run("post.mjs", {
    ...env,
    ...state(env.GITHUB_STATE),
    STATE_log: join(env.RUNNER_TEMP, "missing"),
  });
  assert.deepEqual(samplers(env.RUNNER_TEMP), []);
});

test(
  "reports a notice instead of failing when the state cannot be saved",
  { skip },
  () => {
    const env = { ...job(), GITHUB_STATE: "/nonexistent/state" };
    assert.match(
      run("main.mjs", env),
      /::notice::Resource usage is not reported/,
    );
    assert.deepEqual(samplers(env.RUNNER_TEMP), []);
  },
);
