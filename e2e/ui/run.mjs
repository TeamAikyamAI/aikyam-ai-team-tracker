/**
 * Browser suite for the Aikyam AI Team Tracker.
 *
 * Everything here is something only a real browser can prove: what the sidebar
 * actually renders for a role, whether a blocked route bounces, whether a
 * dialog writes what it says it writes. Anything provable at the endpoint
 * belongs in the pytest suite next door, not here.
 *
 * Runs against the throwaway instance on :8099 seeded by seed_e2e.py.
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.E2E_BASE || "http://127.0.0.1:8099";
const SHOTS = path.join(HERE, "shots");
fs.mkdirSync(SHOTS, { recursive: true });

const USERS = {
  admin: ["aiteam@aikyame2e.com", "AiteamPass123"],
  member: ["pranjal@aikyame2e.com", "PranjalPass123"],
  requestor: ["ravi@aikyame2e.com", "RaviPass123"],
};

const results = [];
let browser;

function eq(actual, expected, what) {
  const a = JSON.stringify(actual);
  const b = JSON.stringify(expected);
  if (a !== b) throw new Error(`${what}\n  expected: ${b}\n  actual:   ${a}`);
}
function ok(cond, what) {
  if (!cond) throw new Error(what);
}

async function test(id, name, fn) {
  const started = Date.now();
  try {
    await fn();
    results.push({ id, name, pass: true, ms: Date.now() - started });
    console.log(`  PASS  ${id}  ${name}`);
  } catch (err) {
    results.push({ id, name, pass: false, ms: Date.now() - started, error: String(err.message || err) });
    console.log(`  FAIL  ${id}  ${name}\n        ${String(err.message || err).replace(/\n/g, "\n        ")}`);
  }
}

/** A signed-in page in its own browser context, so roles never share a session. */
async function signIn(who) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  await page.goto(`${BASE}/login`);
  await page.fill("#email", USERS[who][0]);
  await page.fill("#password", USERS[who][1]);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE}/`, { timeout: 15000 });
  await page.waitForSelector("nav a, aside a", { timeout: 15000 });
  return { context, page };
}

async function navLabels(page) {
  await page.waitForSelector("nav a, aside a");
  const items = await page.locator("nav a, aside a").allInnerTexts();
  return items.map((t) => t.trim()).filter(Boolean);
}

/** Radix selects are buttons plus a portalled listbox, not <select>. */
async function pickFromSelect(page, triggerLocator, optionName) {
  await triggerLocator.click();
  await page.getByRole("option", { name: optionName, exact: false }).first().click();
}

async function expectBounced(page, route) {
  await page.goto(`${BASE}${route}`);
  await page.waitForTimeout(1200);
  const url = new URL(page.url());
  ok(url.pathname !== route, `${route} rendered for a role that should not reach it`);
}

// ===========================================================================

async function blockRequestor() {
  console.log("\nBlock A - requestor");
  const { context, page } = await signIn("requestor");

  await test("UI-A1", "sidebar shows exactly the four requestor screens", async () => {
    eq(await navLabels(page), ["Dashboard", "Project Queue", "Apply for Service", "My Requests"],
      "requestor sidebar");
  });

  await test("UI-A2", "dashboard renders with no write controls", async () => {
    await page.goto(`${BASE}/`);
    await page.waitForSelector("main");
    // The board loads after the KPI row, so wait for a card, not just <main>.
    await page.getByText("Compliance Tracker").first().waitFor({ timeout: 20000 });
    const buttons = (await page.locator("main button").allInnerTexts()).map((t) => t.trim());
    ok(!buttons.includes("New Project"), "New Project button shown to a requestor");
    ok(!buttons.includes("Export Excel"), "Export Excel button shown to a requestor");
    const body = await page.locator("main").innerText();
    ok(body.includes("Compliance Tracker"), "the board did not load for a requestor");
    await page.screenshot({ path: path.join(SHOTS, "requestor-dashboard.png") });
  });

  await test("UI-A3", "the project page shows owners and the target date", async () => {
    await page.goto(`${BASE}/`);
    await page.getByText("Compliance Tracker").first().waitFor({ timeout: 20000 });
    await page.getByText("Compliance Tracker").first().click();
    await page.waitForTimeout(2000);
    const body = await page.locator("main").innerText();
    ok(/Pranjal/i.test(body), "no owner named on the project page — the transparency the board exists for");
    ok(/target/i.test(body), "no target date on the project page");
  });

  await test("UI-A4", "internal remarks appear nowhere", async () => {
    const body = await page.locator("main").innerText();
    ok(!/NSE circular/i.test(body), "a requestor can read the internal remark text");
    ok(!/\bRemarks\b/.test(body), "the Remarks field is labelled on a requestor's screen");
  });

  await test("UI-A5", "blocked routes bounce", async () => {
    for (const route of ["/admin", "/my-day", "/audit", "/requests"]) {
      await expectBounced(page, route);
    }
  });

  await test("UI-A6", "the assistant widget respects the Ask the Tracker permission", async () => {
    await page.goto(`${BASE}/`);
    await page.waitForTimeout(1500);
    const bubble = await page.locator('[aria-label*="assistant" i], [aria-label*="chat" i]').count();
    ok(bubble === 0, "the chat bubble is offered to a role whose Ask the Tracker permission is off");
  });

  await test("UI-A7", "a request can be filed with a BRD and shows up in My Requests", async () => {
    const brd = path.join(HERE, "fixtures", "signed-brd.pdf");
    fs.mkdirSync(path.dirname(brd), { recursive: true });
    fs.writeFileSync(brd, Buffer.concat([Buffer.from("%PDF-1.4\n"), Buffer.alloc(4096, 0x41)]));

    await page.goto(`${BASE}/apply`);
    await page.waitForSelector("#title");
    await pickFromSelect(page, page.locator('button:has-text("Select your business vertical")').first(), "Automation");
    await page.fill("#title", "UI Suite: automate the margin file");
    await page.fill("#description", "Filed by the browser suite.");
    await page.setInputFiles('input[type="file"]', brd);
    await page.locator('main button[type="submit"], main button:has-text("Submit")').first().click();
    await page.waitForTimeout(2500);

    await page.goto(`${BASE}/my-requests`);
    await page.waitForSelector("main");
    await page.waitForTimeout(1500);
    const body = await page.locator("main").innerText();
    ok(body.includes("UI Suite: automate the margin file"), "the submitted request is not in My Requests");
  });

  await context.close();
}

async function blockMember() {
  console.log("\nBlock B - team member");
  const { context, page } = await signIn("member");

  await test("UI-B1", "sidebar shows the seven delivery screens", async () => {
    eq(await navLabels(page), [
      "Dashboard", "My Day", "Project Queue", "Apply for Service",
      "My Requests", "Requests Review", "Ask the Tracker",
    ], "member sidebar");
  });

  await test("UI-B2", "My Day accepts a task and ticks it", async () => {
    await page.goto(`${BASE}/my-day`);
    await page.waitForSelector('input[placeholder="What needs doing?"]');
    for (const title of ["UI task alpha", "UI task beta"]) {
      await page.fill('input[placeholder="What needs doing?"]', title);
      await page.click('button[aria-label="Add task"]');
      await page.waitForTimeout(900);
    }
    let body = await page.locator("main").innerText();
    ok(body.includes("UI task alpha") && body.includes("UI task beta"), "tasks were not added");

    await page.getByLabel('Mark "UI task alpha" as done').click();
    await page.waitForTimeout(2000);
    ok(await page.getByLabel('Mark "UI task alpha" as not done').count() > 0,
      "the task did not move to done after ticking");
    await page.screenshot({ path: path.join(SHOTS, "member-my-day.png") });
  });

  await test("UI-B3", "internal remarks are visible to the team", async () => {
    await page.goto(`${BASE}/`);
    await page.waitForSelector("main");
    await page.getByText("Compliance Tracker").first().click();
    await page.waitForTimeout(1800);
    const body = await page.locator("main").innerText();
    ok(/NSE circular/i.test(body), "a team member cannot see the project's internal remarks");
  });

  await test("UI-B4", "the New Project dialog creates a project on the board", async () => {
    await page.goto(`${BASE}/`);
    await page.click('button:has-text("New Project")');
    await page.waitForSelector("#proj-name");
    await page.fill("#proj-name", "UI Suite Created Project");
    await page.fill("#proj-desc", "Created through the dialog by the browser suite.");
    await pickFromSelect(page, page.locator('[role="dialog"] button').filter({ hasText: "Select" }).first(), "Accounts");
    await pickFromSelect(page, page.locator('[role="dialog"] button').filter({ hasText: "Select" }).first(), "WIP");
    await page.fill("#proj-assigned-by", "Browser suite");
    await page.locator('[role="dialog"] button[type="submit"]').click();
    await page.waitForTimeout(2500);
    const body = await page.locator("main").innerText();
    ok(body.includes("UI Suite Created Project"), "the new project is not on the board");
    await page.screenshot({ path: path.join(SHOTS, "member-dashboard.png") });
  });

  await test("UI-B5", "Export Excel downloads a workbook", async () => {
    await page.goto(`${BASE}/`);
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 20000 }),
      page.click('button:has-text("Export Excel")'),
    ]);
    const to = path.join(SHOTS, "export.xlsx");
    await download.saveAs(to);
    const head = fs.readFileSync(to).subarray(0, 2).toString("latin1");
    eq(head, "PK", "the export is not a real xlsx");
  });

  await test("UI-B6", "administration is not reachable", async () => {
    for (const route of ["/admin", "/audit"]) await expectBounced(page, route);
  });

  await context.close();
}

async function blockAdmin() {
  console.log("\nBlock C - admin");
  const { context, page } = await signIn("admin");

  await test("UI-C1", "sidebar shows all nine screens", async () => {
    eq(await navLabels(page), [
      "Dashboard", "My Day", "Project Queue", "Apply for Service", "My Requests",
      "Requests Review", "Ask the Tracker", "Admin Panel", "Audit Trail",
    ], "admin sidebar");
    await page.screenshot({ path: path.join(SHOTS, "admin-dashboard.png") });
  });

  await test("UI-C2", "the admin panel offers every tab", async () => {
    await page.goto(`${BASE}/admin`);
    await page.waitForSelector('[role="tablist"]');
    const tabs = (await page.locator('[role="tab"]').allInnerTexts()).map((t) => t.trim());
    for (const expected of ["Users", "Verticals", "Statuses", "Branding", "Settings", "Access"]) {
      ok(tabs.includes(expected), `the ${expected} tab is missing from the admin panel`);
    }
    await page.screenshot({ path: path.join(SHOTS, "admin-panel.png") });
  });

  await test("UI-C3", "the team day view is read-only", async () => {
    await page.goto(`${BASE}/my-day`);
    await page.waitForTimeout(1800);
    const body = await page.locator("main").innerText();
    ok(/Pranjal/i.test(body), "the admin cannot see the team's day at all");
    // Open the member's day and confirm every tick control is disabled.
    await page.getByRole("button", { name: "Pranjal Shukla" }).first().click();
    await page.waitForTimeout(2000);
    const boxes = page.locator('[role="checkbox"]');
    const n = await boxes.count();
    ok(n > 0, "the member's tasks did not load in the read-only view");
    for (let i = 0; i < n; i++) {
      const disabled = await boxes.nth(i).getAttribute("data-disabled");
      const aria = await boxes.nth(i).getAttribute("aria-disabled");
      ok(disabled !== null || aria === "true", "an admin can tick someone else's task");
    }
    await page.screenshot({ path: path.join(SHOTS, "admin-team-day.png") });
  });

  await test("UI-C4", "the assistant adds a project from the chat", async () => {
    await page.goto(`${BASE}/`);
    await page.waitForTimeout(1200);
    const bubble = page.locator('[aria-label*="assistant" i], [aria-label*="chat" i]').first();
    await bubble.click();
    await page.waitForTimeout(800);
    const box = page.locator('textarea, input[type="text"]').last();
    const say = async (text) => {
      await box.fill(text);
      await box.press("Enter");
      await page.waitForTimeout(1600);
    };
    await say("add a project");
    await say("UI Suite Chat Project");
    await say("Accounts");
    await say("WIP");
    await say("Browser suite");
    await say("save");
    await say("save");
    await page.waitForTimeout(1200);

    await page.goto(`${BASE}/`);
    await page.waitForSelector("main");
    await page.waitForTimeout(1500);
    const body = await page.locator("main").innerText();
    ok(body.includes("UI Suite Chat Project"), "the chat-created project is not on the board");
  });

  await test("UI-C5", "the permission grid refuses to lock the admin out", async () => {
    await page.goto(`${BASE}/admin`);
    await page.getByRole("tab", { name: "Access" }).click();
    await page.waitForTimeout(1500);
    const body = await page.locator("main").innerText();
    ok(/Admin Panel/i.test(body), "the Admin Panel row is missing from the grid");
    const locked = await page.locator('[role="checkbox"][disabled], [role="checkbox"][aria-disabled="true"], input[type="checkbox"]:disabled').count();
    ok(locked >= 1, "no locked cell in the grid — an admin could remove their own access");
    await page.screenshot({ path: path.join(SHOTS, "admin-access-grid.png") });
  });

  await context.close();
}

async function blockGridLive() {
  console.log("\nBlock D - a permission change, seen from the other side");
  const admin = await signIn("admin");
  const before = await signIn("requestor");

  await test("UI-D1", "a requestor starts with the dashboard", async () => {
    ok((await navLabels(before.page)).includes("Dashboard"), "the requestor has no dashboard to remove");
  });

  await test("UI-D2", "revoking Dashboard removes it from the requestor's session", async () => {
    await admin.page.goto(`${BASE}/admin`);
    await admin.page.getByRole("tab", { name: "Access" }).click();
    await admin.page.waitForTimeout(1500);

    const row = admin.page.locator("tr", { hasText: "Dashboard" }).first();
    const cell = row.locator('[role="checkbox"], input[type="checkbox"]').last();
    await cell.click();
    await admin.page.waitForTimeout(600);
    const save = admin.page.locator('button:has-text("Save")').first();
    if (await save.count()) { await save.click(); await admin.page.waitForTimeout(1500); }

    const after = await signIn("requestor").catch(() => null);
    ok(after !== null, "the requestor could not sign in at all after the change");
    const labels = await navLabels(after.page);
    ok(!labels.includes("Dashboard"), `Dashboard is still in the requestor's sidebar: ${JSON.stringify(labels)}`);
    await after.context.close();
  });

  await test("UI-D3", "restoring it brings it straight back", async () => {
    const row = admin.page.locator("tr", { hasText: "Dashboard" }).first();
    const cell = row.locator('[role="checkbox"], input[type="checkbox"]').last();
    await cell.click();
    await admin.page.waitForTimeout(600);
    const save = admin.page.locator('button:has-text("Save")').first();
    if (await save.count()) { await save.click(); await admin.page.waitForTimeout(1500); }

    const after = await signIn("requestor");
    ok((await navLabels(after.page)).includes("Dashboard"), "Dashboard did not come back");
    await after.context.close();
  });

  await admin.context.close();
  await before.context.close();
}

// ===========================================================================

browser = await chromium.launch();
try {
  await blockRequestor();
  await blockMember();
  await blockAdmin();
  await blockGridLive();
} finally {
  await browser.close();
}

const failed = results.filter((r) => !r.pass);
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed`);
fs.writeFileSync(path.join(HERE, "results.json"), JSON.stringify(results, null, 2));
process.exit(failed.length ? 1 : 0);
