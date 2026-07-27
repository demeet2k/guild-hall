#!/usr/bin/env node
const crypto = require("crypto");
const fs = require("fs");

const TOP_KEYS = [
  "schema", "seedID", "version", "parent", "identity", "query",
  "carrier", "routes", "branchTestAddress", "approximation", "defects",
  "provenance", "witnesses", "unresolved", "promotion", "return",
];
const ROUTES = [
  "F03<->F08", "F07<->F08", "F08<->F09",
  "F08<->F17", "F08->F18", "F08->F31",
];

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function requireValue(condition, code) {
  if (!condition) throw new Error(code);
}

function projection(seed) {
  const q1 = seed.approximation.Q01;
  const q2 = seed.approximation.Q02;
  const values = [
    seed.schema, seed.version, seed.identity.gid,
    seed.identity.grid, seed.identity.station,
    seed.carrier.tuple, seed.carrier.jet,
    ...seed.routes, seed.branchTestAddress.Q01,
    q1.model, String(q1.order), q1.remainder, q1.errorBound,
    q1.neighborhood, q1.singularDirections,
    q1.globalizationBurden, q1.integratedModel,
    String(q1.integratedOrder), q1.integratedRemainder,
    q1.integratedErrorBound, q1.integratedNeighborhood,
    q2.object, q2.ordinaryJet, q2.testSpace, q2.order,
    q2.remainder, q2.errorBound, q2.neighborhood,
    q2.singularDirections, q2.globalizationBurden,
    seed.promotion.IC10, seed.promotion.QSHRINK,
    seed.return.rollbackTarget, seed.return.nextSeed,
  ];
  return sha256(Buffer.from(JSON.stringify(values), "utf8"));
}

function main() {
  const path = process.argv[2];
  const expected = process.argv[3];
  const raw = fs.readFileSync(path);
  const digest = sha256(raw);
  if (expected && digest !== expected) {
    console.log(`DECODER_B::DIGEST_MISMATCH EXPECTED::${expected} OBSERVED::${digest}`);
    return 2;
  }
  requireValue(raw.at(-1) === 0x0a, "FINAL_LF_MISSING");
  requireValue([...raw].filter((b) => b === 0x0a).length === 1, "PAYLOAD_NOT_SINGLE_LINE");
  const seed = JSON.parse(raw.toString("utf8"));
  requireValue(JSON.stringify(Object.keys(seed)) === JSON.stringify(TOP_KEYS), "TOP_LEVEL_ORDER_OR_FIELD_MISMATCH");
  requireValue(seed.schema === "KC144.STATION_REENTRY.F08.V1", "SCHEMA_MISMATCH");
  requireValue(seed.version === "KC144.V1", "VERSION_MISMATCH");
  requireValue(seed.identity.gid === "051", "GID_MISMATCH");
  requireValue(seed.identity.grid === "R05C03", "GRID_MISMATCH");
  requireValue(seed.identity.station === "F08", "STATION_MISMATCH");
  requireValue(JSON.stringify(seed.routes) === JSON.stringify(ROUTES), "ROUTE_MISMATCH");
  requireValue(seed.carrier.tuple === "A8=(P8,iota8,Lambda8,partial8,N8)", "CARRIER_MISMATCH");
  requireValue(seed.approximation.Q01.order === 2, "Q01_ORDER_MISMATCH");
  requireValue(seed.approximation.Q01.remainder === "R3(h)", "Q01_REMAINDER_MISMATCH");
  requireValue(seed.approximation.Q01.neighborhood === "|h|<=r<1 ON PLUS LIFT", "Q01_NEIGHBORHOOD_MISMATCH");
  requireValue(seed.approximation.Q02.ordinaryJet === "UNDEFINED", "Q02_JET_MISMATCH");
  requireValue(seed.approximation.Q02.testSpace === "REQUIRED", "Q02_TEST_SPACE_MISMATCH");
  requireValue(seed.promotion.IC10 === "HOLD", "IC10_AUTHORITY_MISMATCH");
  requireValue(seed.promotion.QSHRINK === "HOLD", "QSHRINK_AUTHORITY_MISMATCH");
  console.log(`DECODER_B::PASS SHA256::${digest} PROJECTION::${projection(seed)}`);
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.log(`DECODER_B::BLOCK::${error.message}`);
  process.exitCode = 1;
}
