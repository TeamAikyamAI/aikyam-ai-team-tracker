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

  await test("UI-B1", "sidebar shows the six delivery screens", async () => {
    // No Apply for Service and no My Requests: the team receives requests,
    // it does not file them against itself. The API key register is the team's
    // own infrastructure, so it does belong here.
    eq(await navLabels(page), [
      "Dashboard", "My Day", "Project Queue", "Requests Review", "Ask the Tracker",
      "API Keys",
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

  await test("UI-B6", "a team member has no Delete on a project", async () => {
    // Editing is everyday work; deleting is admin-only, so the button must not
    // even render for a member.
    await page.goto(`${BASE}/`);
    await page.getByText("Compliance Tracker").first().waitFor({ timeout: 20000 });
    await page.getByText("Compliance Tracker").first().click();
    await page.waitForTimeout(2000);
    const buttons = (await page.locator("main button").allInnerTexts()).map((t) => t.trim());
    ok(buttons.some((b) => b.includes("Edit")), "a member cannot edit a project");
    ok(!buttons.some((b) => b.includes("Delete")), "Delete is offered to a team member");
  });

  await test("UI-B7", "administration is not reachable", async () => {
    for (const route of ["/admin", "/audit", "/apply", "/my-requests"]) await expectBounced(page, route);
  });

  await test("UI-B8", "a member records a key in the register, without the key", async () => {
    await page.goto(`${BASE}/api-keys`);
    await page.getByRole("heading", { name: "API Key Register" }).waitFor({ timeout: 20000 });

    // The one thing the page must never offer: somewhere to paste the secret.
    const body = (await page.locator("main").innerText()).toLowerCase();
    ok(body.includes("register, not a vault"), "the page does not say what it is not");

    await page.getByRole("button", { name: "Add key" }).click();
    await page.getByRole("dialog").waitFor({ timeout: 10000 });
    const fields = await page.locator('[role="dialog"] input, [role="dialog"] textarea').count();
    const labels = (await page.locator('[role="dialog"] label').allInnerTexts())
      .map((t) => t.trim().toLowerCase());
    ok(!labels.some((l) => l.includes("key value") || l === "api key" || l.includes("secret")),
       "the dialog offers a field for the key itself");
    ok(fields > 0, "the dialog rendered no fields at all");

    await page.getByLabel("Name of the work this key belongs to").fill("UI Meeting Hub");
    // Provider is a curated list, so pick from it rather than typing.
    await page.locator('[role="dialog"] button[role="combobox"]').nth(1).click();
    await page.locator('[role="option"]').first().click();
    await page.locator("#key-purpose").fill("For the STT");
    await page.getByRole("button", { name: "Add to register" }).click();

    await page.getByText("UI Meeting Hub").first().waitFor({ timeout: 15000 });
    await page.screenshot({ path: path.join(SHOTS, "member-api-keys.png") });
  });

  await context.close();
}

async function blockAdmin() {
  console.log("\nBlock C - admin");
  const { context, page } = await signIn("admin");

  await test("UI-C1", "sidebar shows all ten screens", async () => {
    eq(await navLabels(page), [
      "Dashboard", "My Day", "Project Queue", "Apply for Service", "My Requests",
      "Requests Review", "Ask the Tracker", "API Keys", "Admin Panel", "Audit Trail",
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

  await test("UI-C5", "an admin can delete a project, with a confirmation first", async () => {
    // Create one through the dialog so the run never deletes seeded data.
    await page.goto(`${BASE}/`);
    await page.click('button:has-text("New Project")');
    await page.waitForSelector("#proj-name");
    await page.fill("#proj-name", "UI Suite Doomed Project");
    await pickFromSelect(page, page.locator('[role="dialog"] button').filter({ hasText: "Select" }).first(), "Accounts");
    await pickFromSelect(page, page.locator('[role="dialog"] button').filter({ hasText: "Select" }).first(), "WIP");
    await page.locator('[role="dialog"] button[type="submit"]').click();
    await page.waitForTimeout(2500);

    await page.getByText("UI Suite Doomed Project").first().click();
    await page.waitForTimeout(2000);
    await page.locator('main button:has-text("Delete")').first().click();
    await page.waitForTimeout(800);

    // Nothing goes without an explicit confirmation.
    const dialog = page.locator('[role="alertdialog"]');
    ok(await dialog.count() > 0, "Delete went straight through with no confirmation");
    ok((await dialog.innerText()).includes("UI Suite Doomed Project"),
      "the confirmation does not name the project being deleted");
    await dialog.locator('button:has-text("Delete project")').click();
    await page.waitForTimeout(2500);

    await page.goto(`${BASE}/`);
    await page.waitForSelector("main");
    await page.waitForTimeout(2000);
    ok(!(await page.locator("main").innerText()).includes("UI Suite Doomed Project"),
      "the deleted project is still on the board");
  });

  await test("UI-C6", "the permission grid refuses to lock the admin out", async () => {
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

  await test("UI-C7", "the register is closed to a requestor", async () => {
    const { context: rc, page: rp } = await signIn("requestor");
    const labels = await navLabels(rp);
    ok(!labels.includes("API Keys"), "a requestor is offered the API key register");
    await expectBounced(rp, "/api-keys");
    await rc.close();
  });

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

  await test("UI-D4", "the Apply for Service routes follow the permission both ways", async () => {
    // Off by default for the team. The Project Queue page also carries two
    // buttons into it - they have to appear and disappear with the tick, or
    // the person lands on a route that bounces them straight back.
    const before = await signIn("member");
    await before.page.goto(`${BASE}/queue`);
    await before.page.waitForSelector("main");
    await before.page.waitForTimeout(1500);
    ok(!(await before.page.locator("main").innerText()).includes("Apply for Service"),
      "the Project Queue offers Apply for Service to a role that cannot use it");
    await before.context.close();

    const row = admin.page.locator("tr", { hasText: "Apply for Service" }).first();
    const cell = row.locator('[role="checkbox"], input[type="checkbox"]').nth(1); // member column
    const save = admin.page.locator('button:has-text("Save")').first();

    await cell.click();
    await admin.page.waitForTimeout(600);
    if (await save.count()) { await save.click(); await admin.page.waitForTimeout(1500); }

    const granted = await signIn("member");
    ok((await navLabels(granted.page)).includes("Apply for Service"),
      "granting Apply for Service did not put it in the sidebar");
    await granted.context.close();

    await cell.click();
    await admin.page.waitForTimeout(600);
    if (await save.count()) { await save.click(); await admin.page.waitForTimeout(1500); }
    const revoked = await signIn("member");
    const labels = await navLabels(revoked.page);
    ok(!labels.includes("Apply for Service"),
      `Apply for Service still in the member sidebar: ${JSON.stringify(labels)}`);
    await revoked.context.close();
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
