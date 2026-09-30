// The editor's report relay - a Cloudflare Worker (free plan).
//
// The editor (Tools > Send a report) POSTs one JSON: {message, contact, info, zip (base64)}. The relay checks it
// (size, a real zip, the rate), commits the zip to a PRIVATE reports repo and opens an issue there, so the author
// gets a notification with the report's number. The GitHub token is the Worker's secret (GITHUB_TOKEN) - it is never
// in the editor or in this repo. Nothing else is kept: no IP address, no cookies.
//
// Settings (Worker > Settings > Variables and Secrets):
//   GITHUB_TOKEN  secret: a fine-grained token for the reports repo only - Contents: read and write,
//                 Issues: read and write
//   REPORTS_REPO  text: owner/name of the private reports repo, like MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor-Reports
// Optional: a rate limit binding named REPORT_LIMIT (wrangler.toml) - 3 reports a minute from one address.

const ZIP_CAP = 4 * 1024 * 1024;            // bytes, as the editor's report.ZIP_CAP
const B64_CAP = Math.ceil(ZIP_CAP / 3) * 4 + 16;

function reply(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function reportId() {
  const d = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const r = crypto.getRandomValues(new Uint8Array(3));
  return "R-" + d + "-" + [...r].map((b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}

function clean(text, cap) {
  // plain text for the issue: no mentions, no html, no links that ping anyone
  return String(text || "")
    .slice(0, cap)
    .replace(/[<>]/g, "")
    .replace(/@/g, "@​");
}

async function github(env, method, path, body) {
  const r = await fetch("https://api.github.com/repos/" + env.REPORTS_REPO + path, {
    method,
    headers: {
      Authorization: "Bearer " + env.GITHUB_TOKEN,
      Accept: "application/vnd.github+json",
      "User-Agent": "rtw-m2tw-editor-report-relay",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("GitHub " + r.status);
  return r.json();
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return reply(405, { error: "send a report from the editor (Tools > Send a report)" });
    if (!env.GITHUB_TOKEN || !env.REPORTS_REPO) return reply(503, { error: "the relay is not set up yet" });
    if (!(request.headers.get("User-Agent") || "").startsWith("RTW-M2TW-Campaign-Editor/"))
      return reply(403, { error: "reports come from the editor only" });
    const size = Number(request.headers.get("Content-Length") || 0);
    if (size > B64_CAP + 16384) return reply(413, { error: "the report is too big" });
    if (env.REPORT_LIMIT) {
      const who = request.headers.get("CF-Connecting-IP") || "?";
      const { success } = await env.REPORT_LIMIT.limit({ key: who });
      if (!success) return reply(429, { error: "too many reports in a minute - wait a little and send again" });
    }
    let data;
    try {
      data = await request.json();
    } catch (e) {
      return reply(400, { error: "not a report" });
    }
    const zip = typeof data.zip === "string" ? data.zip : "";
    if (!zip.startsWith("UEsDB") || zip.length > B64_CAP || !/^[A-Za-z0-9+/=]+$/.test(zip))
      return reply(400, { error: "the report has no zip, or a broken one" });
    const id = reportId();
    const day = id.slice(2, 10);
    const file = "reports/" + day.slice(0, 4) + "-" + day.slice(4, 6) + "-" + day.slice(6) + "/" + id + ".zip";
    const info = data.info && typeof data.info === "object" ? data.info : {};
    const lines = Object.entries(info)
      .slice(0, 12)
      .map(([k, v]) => "- **" + clean(k, 40) + "**: " + clean(v, 200));
    try {
      await github(env, "PUT", "/contents/" + file, { message: "Report " + id, content: zip });
      await github(env, "POST", "/issues", {
        title: id + ": " + (clean(data.message, 80).split("\n")[0] || "(no words)"),
        body: [
          "**What happened**",
          "",
          clean(data.message, 4000)
            .split("\n")
            .map((l) => "> " + l)
            .join("\n") || "> (not said)",
          "",
          "**Contact**: " + (clean(data.contact, 200) || "none"),
          "",
          ...lines,
          "",
          "The logs: https://github.com/" + env.REPORTS_REPO + "/blob/HEAD/" + file,
        ].join("\n"),
      });
    } catch (e) {
      return reply(502, { error: "the report could not be filed (" + e.message + ") - save the zip and send it on Discord" });
    }
    return reply(200, { id });
  },
};
