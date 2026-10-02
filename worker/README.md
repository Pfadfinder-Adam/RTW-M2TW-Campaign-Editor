# The report relay

`Tools > Send a report` in the editor sends the logs (with names cut out) to this small relay, a Cloudflare Worker.
The relay keeps the GitHub token on its side, so the token is never in the editor or in this repo. It checks each
report (size, a real zip, 3 a minute from one address), commits the zip to a **private** reports repo and opens an
issue there, so the author gets a notification with the report's number. It keeps no IP addresses and sets no
cookies.

## Setting it up (once, about 10 minutes, free)

1. **A private repo for the reports**: GitHub > New repository > `RTW-M2TW-Campaign-Editor-Reports`, **Private**, tick
   "Add a README file".
2. **A token only for that repo**: GitHub > Settings > Developer settings > Personal access tokens >
   Fine-grained tokens > Generate new token. Repository access: *Only select repositories* >
   `RTW-M2TW-Campaign-Editor-Reports`. Permissions > Repository: **Contents: Read and write**, **Issues: Read and write**
   (nothing else). Pick an expiry, generate, copy the token (it is shown once).
3. **The Worker**: dash.cloudflare.com (a free account) > Workers & Pages > Create > Create Worker > name it
   `rtw-m2tw-campaign-editor-reports` > Deploy. Then Edit code, replace everything with `report-relay.js` from this folder,
   Deploy.
4. **Its settings**: the Worker > Settings > Variables and Secrets > Add:
   - `REPORTS_REPO`, type Text: `MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor-Reports`
   - `GITHUB_TOKEN`, type **Secret**: the token from step 2
5. **Its address**: the Worker's page shows it, like `https://rtw-m2tw-campaign-editor-reports.<account>.workers.dev`. It goes
   into `campaign_editor/report.py` (`REPORT_URL`), and the next release sends reports there.

The rate limit (3 a minute from one address) needs `wrangler deploy` with `wrangler.toml` from this folder; without
it the relay still works, only without that limit.

When the token expires: make a new one (step 2) and replace the `GITHUB_TOKEN` secret (step 4). If the token ever
leaks: delete it on GitHub at once - it can only touch the reports repo.
