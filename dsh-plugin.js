import { readFileSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const SKILL_FILE_URL = new URL("./skills/anchorbrowser/SKILL.md", import.meta.url);
const SKILL_FILE = fileURLToPath(SKILL_FILE_URL);
const SKILL_DIRECTORY = dirname(SKILL_FILE);
const FRONTMATTER = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/;

export const name = "dsh-anchorbrowser";
export const inject = ["skills"];

function readFrontmatterScalar(frontmatter, key) {
  const line = frontmatter.split(/\r?\n/).find((candidate) => candidate.startsWith(`${key}:`));
  if (line === undefined) {
    throw new Error(`dsh-anchorbrowser: packaged SKILL.md has no ${key}`);
  }
  const value = line.slice(key.length + 1).trim();
  if (value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1).replaceAll("''", "'");
  }
  if (value.startsWith('"') && value.endsWith('"')) {
    return JSON.parse(value);
  }
  if (value === "") {
    throw new Error(`dsh-anchorbrowser: packaged SKILL.md has an empty ${key}`);
  }
  return value;
}

function readSkill() {
  const source = readFileSync(SKILL_FILE, "utf8").replace(/^\uFEFF/, "");
  const match = FRONTMATTER.exec(source);
  if (match === null) {
    throw new Error("dsh-anchorbrowser: packaged SKILL.md has no valid frontmatter block");
  }
  return {
    name: readFrontmatterScalar(match[1], "name"),
    description: readFrontmatterScalar(match[1], "description"),
    content: source.slice(match[0].length).replace(/^\r?\n/, ""),
  };
}

export function apply(ctx) {
  const skill = readSkill();
  ctx.skills.register({
    ...skill,
    source: "bundled",
    provider: "dsh-anchorbrowser",
    resourceBase: { kind: "directory", path: SKILL_DIRECTORY },
    path: SKILL_FILE,
  });
}
