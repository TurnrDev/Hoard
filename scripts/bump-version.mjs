import { readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const rootDirectory = fileURLToPath(new URL("..", import.meta.url));
const bumpType = process.argv[2];
const allowedBumpTypes = new Set(["major", "minor", "patch"]);

if (!allowedBumpTypes.has(bumpType)) {
  console.error("Usage: npm run version:bump -- <major|minor|patch>");
  process.exit(1);
}

const versionPattern = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const packagePath = join(rootDirectory, "package.json");
const packageLockPath = join(rootDirectory, "package-lock.json");
const projectPath = join(rootDirectory, "pyproject.toml");
const apiPath = join(rootDirectory, "hoard", "campaigns", "api.py");

function readText(path) {
  return readFileSync(path, "utf8");
}

function readVersion(path, pattern) {
  const match = readText(path).match(pattern);

  if (!match) {
    throw new Error(`Could not find a version in ${path}.`);
  }

  return match[1];
}

function nextVersion(version, type) {
  const match = version.match(versionPattern);

  if (!match) {
    throw new Error(`Version ${version} is not a supported stable SemVer version.`);
  }

  const [major, minor, patch] = match.slice(1).map(Number);

  if (type === "major") {
    return `${major + 1}.0.0`;
  }

  if (type === "minor") {
    return `${major}.${minor + 1}.0`;
  }

  return `${major}.${minor}.${patch + 1}`;
}

function replaceVersions(path, patterns, version) {
  let contents = readText(path);

  for (const pattern of patterns) {
    const updatedContents = contents.replace(pattern, `$1${version}$2`);

    if (contents === updatedContents) {
      throw new Error(`Could not update the version in ${path}.`);
    }

    contents = updatedContents;
  }

  return { path, contents };
}

function writeUpdates(updates) {
  const temporaryPaths = updates.map(({ path, contents }) => {
    const temporaryPath = join(dirname(path), `.${Date.now()}-${path.split("/").pop()}`);
    writeFileSync(temporaryPath, contents);
    return { path, temporaryPath };
  });

  for (const { path, temporaryPath } of temporaryPaths) {
    renameSync(temporaryPath, path);
  }
}

const packageVersion = readVersion(packagePath, /^\s*"version": "([^"]+)",/m);
const versions = [
  packageVersion,
  readVersion(projectPath, /^version = "([^"]+)"$/m),
  readVersion(apiPath, /version="([^"]+)"/),
  readVersion(packageLockPath, /^\s*"version": "([^"]+)",/m),
  readVersion(
    packageLockPath,
    /\n\s+"": \{\n\s+"name": "hoard",\n\s+"version": "([^"]+)",/,
  ),
];

if (new Set(versions).size !== 1) {
  throw new Error(`Version files do not agree: ${versions.join(", ")}.`);
}

const version = nextVersion(packageVersion, bumpType);
writeUpdates([
  replaceVersions(packagePath, [/("version": ")[^"]+(",)/], version),
  replaceVersions(projectPath, [/(version = ")[^"]+(")/], version),
  replaceVersions(apiPath, [/(version=")[^"]+(")/], version),
  replaceVersions(
    packageLockPath,
    [
      /("version": ")[^"]+(",)/,
      /(\n\s+"": \{\n\s+"name": "hoard",\n\s+"version": ")[^"]+(",)/,
    ],
    version,
  ),
]);

console.log(`Bumped version from ${packageVersion} to ${version}.`);
