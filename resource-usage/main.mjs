import { spawn } from "node:child_process";
import { appendFileSync } from "node:fs";
import { join } from "node:path";
import { available } from "./cgroup.mjs";

const skip = (reason) =>
  console.log(`::notice::Resource usage is not reported: ${reason}`);

if (!available()) {
  skip("no cgroup v2 accounting here.");
  process.exit(0);
}

let sampler;
try {
  const log = join(process.env.RUNNER_TEMP, "resource-usage.ndjson");
  sampler = spawn(
    process.execPath,
    [join(import.meta.dirname, "sampler.mjs"), log],
    {
      detached: true,
      stdio: "ignore",
    },
  );
  sampler.on("error", (error) => skip(error.message));
  if (sampler.pid === undefined) throw new Error("the sampler did not start.");
  sampler.unref();
  appendFileSync(process.env.GITHUB_STATE, `pid=${sampler.pid}\nlog=${log}\n`);
} catch (error) {
  if (sampler?.pid) sampler.kill();
  skip(error.message);
}
