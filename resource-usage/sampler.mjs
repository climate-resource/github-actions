import { appendFileSync } from "node:fs";
import { sample } from "./cgroup.mjs";

const [log] = process.argv.slice(2);
const write = () => appendFileSync(log, `${JSON.stringify(sample())}\n`);

write();
setInterval(write, 5000);
