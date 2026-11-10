import { existsSync, readFileSync } from "node:fs";

const root = "/sys/fs/cgroup";

export const available = () =>
  existsSync(`${root}/cpu.stat`) && existsSync(`${root}/memory.current`);

const read = (file) => {
  try {
    return readFileSync(`${root}/${file}`, "utf8").trim();
  } catch {
    return undefined;
  }
};

const field = (file, key) => {
  const line = read(file)
    ?.split("\n")
    .find((l) => l.startsWith(`${key} `));
  return line ? Number(line.split(" ")[1]) : undefined;
};

/** One reading: CPU and CPU-wait time in microseconds, memory in bytes. */
export const sample = () => ({
  at: Date.now(),
  cpuUsec: field("cpu.stat", "usage_usec") ?? 0,
  waitUsec: Number(/total=(\d+)/.exec(read("cpu.pressure") ?? "")?.[1] ?? 0),
  memory: Number(read("memory.current") ?? 0),
  anon: field("memory.stat", "anon") ?? 0,
});

export const memoryPeak = () => {
  const peak = read("memory.peak");
  return peak ? Number(peak) : undefined;
};

export const memoryLimit = () => {
  const max = read("memory.max");
  return max && max !== "max" ? Number(max) : undefined;
};

/** Inverts runc 1.3's shares-to-weight mapping, which Kubernetes applies to the CPU request. */
export const cpuRequest = () => {
  const weight = Number(read("cpu.weight"));
  if (!weight || !process.env.KUBERNETES_SERVICE_HOST) return undefined;
  const c = 612 * (Math.log10(weight) + 7 / 34);
  const log2Shares = (-125 + Math.sqrt(125 ** 2 + 4 * c)) / 2;
  return 2 ** log2Shares / 1024;
};
