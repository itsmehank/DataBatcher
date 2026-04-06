import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const requiredEnv = (name) => {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
};

const optionalEnv = (name, fallback) => {
  const value = process.env[name]?.trim();
  return value || fallback;
};

const parseBoolean = (value, fallback) => {
  if (value === undefined) return fallback;
  return !["0", "false", "no", "off"].includes(value.toLowerCase());
};

const buildDashboardUrl = ({ frontendUrl, region, market, listCategory, date }) => {
  const url = new URL("/dashboard", frontendUrl);
  url.searchParams.set("region", region);
  url.searchParams.set("market", market);
  url.searchParams.set("listCategory", listCategory);
  url.searchParams.set("date", date);
  return url.toString();
};

const buildMinerviniUrl = ({ frontendUrl, region, market, listCategory, date }) => {
  const url = new URL("/api/minervini", frontendUrl);
  url.searchParams.set("region", region);
  url.searchParams.set("date", date);
  url.searchParams.set("market", market);
  url.searchParams.set("listCategory", listCategory);
  return url.toString();
};

const fetchJson = async (request, url, errorLabel) => {
  const response = await request.get(url);
  if (!response.ok()) {
    throw new Error(`${errorLabel} failed with status ${response.status()}`);
  }
  return response.json();
};

const waitForRows = async (page) => {
  const rows = page.locator("tbody tr");
  await rows.first().waitFor({ state: "visible", timeout: 120000 });
  const count = await rows.count();
  if (count === 0) {
    throw new Error("No dashboard rows available for download");
  }
  return count;
};

const readErrorBox = async (page) => {
  const errorBox = page.locator(".error-box").first();
  if (await errorBox.isVisible().catch(() => false)) {
    const message = (await errorBox.textContent())?.trim();
    if (message) {
      throw new Error(message);
    }
  }
};

const resolveDate = async ({ request, frontendUrl, region, requestedDate }) => {
  if (requestedDate) {
    return requestedDate;
  }

  const dates = await fetchJson(request, new URL(`/api/options/dates?region=${encodeURIComponent(region)}`, frontendUrl).toString(), "Date options request");
  if (!Array.isArray(dates) || dates.length === 0 || typeof dates[0] !== "string") {
    throw new Error(`No available dashboard dates for region ${region}`);
  }
  return dates[0];
};

const run = async () => {
  const frontendUrl = optionalEnv("FRONTEND_URL", "http://127.0.0.1:5173");
  const region = optionalEnv("REGION", "US");
  const market = requiredEnv("MARKET");
  const listCategory = optionalEnv("LIST_CATEGORY", "all");
  const date = process.env["DATE"]?.trim() || "";
  const headless = parseBoolean(process.env["HEADLESS"], true);
  const outputDir = optionalEnv("OUTPUT_DIR", path.join(__dirname, "output"));

  await fs.mkdir(outputDir, { recursive: true });

  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();

  try {
    const healthResponse = await page.request.get(new URL("/api/health", frontendUrl).toString());
    if (!healthResponse.ok()) {
      throw new Error(`Health check failed with status ${healthResponse.status()}`);
    }

    const dbHealthResponse = await page.request.get(new URL(`/api/health/db?region=${encodeURIComponent(region)}`, frontendUrl).toString());
    if (!dbHealthResponse.ok()) {
      throw new Error(`DB health check failed with status ${dbHealthResponse.status()}`);
    }

    const effectiveDate = await resolveDate({ request: page.request, frontendUrl, region, requestedDate: date });
    const previewRows = await fetchJson(
      page.request,
      buildMinerviniUrl({ frontendUrl, region, market, listCategory, date: effectiveDate }),
      "Minervini preview request",
    );

    if (!Array.isArray(previewRows) || previewRows.length === 0) {
      throw new Error(`No Minervini rows for region=${region}, date=${effectiveDate}, market=${market}, listCategory=${listCategory}`);
    }

    const dashboardUrl = buildDashboardUrl({ frontendUrl, region, market, listCategory, date: effectiveDate });

    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForLoadState("networkidle", { timeout: 120000 });
    await readErrorBox(page);

    const rowCount = await waitForRows(page);
    const selectAll = page.getByLabel("Select all rows for download");
    await selectAll.check();

    const downloadButton = page.getByRole("button", { name: /^Download Checked/ });
    await downloadButton.waitFor({ state: "visible", timeout: 30000 });
    await readErrorBox(page);

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 900000 }),
      downloadButton.click(),
    ]);

    const suggestedFilename = download.suggestedFilename() || `${region}-${market}.zip`;
    const targetPath = path.join(outputDir, suggestedFilename);
    await download.saveAs(targetPath);

    await page.waitForLoadState("networkidle", { timeout: 120000 }).catch(() => undefined);
    await readErrorBox(page);

    process.stdout.write(
      `${JSON.stringify({
        ok: true,
        rows: rowCount,
        region,
        market,
        listCategory,
        date: effectiveDate,
        file: targetPath,
      })}\n`,
    );
  } finally {
    await context.close();
    await browser.close();
  }
};

run().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
