// Friendly column names, descriptions and formatters shared by every page.
import {FileAttachment} from "observablehq:stdlib";
import * as d3 from "npm:d3";
import {crestHref} from "./crests.js";
import {iconHeader, COL_ICONS} from "./icons.js";

export const labels = await FileAttachment("../data/labels.json").json();
export const clubs = await FileAttachment("../data/clubs.csv").csv({typed: true});
const clubBySlug = new Map(clubs.map((c) => [c.slug, c]));
const clubByName = new Map(clubs.map((c) => [c.club, c]));
export const slugify = (name) => String(name ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
export function clubInfo(nameOrSlug) { return clubByName.get(nameOrSlug) ?? clubBySlug.get(nameOrSlug) ?? clubBySlug.get(slugify(nameOrSlug)); }

// A fixture's own league already tells you the grade (a league is one grade's competition), so
// any "<club> Under 18's SL2"-style compound name can be split back into club + grade + league.
const leaguesMeta = await FileAttachment("../data/leagues.json").json();
const gradeByLeague = new Map(leaguesMeta.map((l) => [l.league, l.grade]));
// Cups/trials/friendlies aren't in leagues.json (only the graded State League competitions are),
// so fall back to reading the grade off the competition's own name.
export function leagueGrade(leagueName) {
  const known = gradeByLeague.get(leagueName);
  if (known) return known;
  const name = String(leagueName ?? "");
  if (/U18|Under 18/i.test(name)) return "U18";
  if (/Reserves|Res\b/i.test(name)) return "RES";
  return name ? "SEN" : undefined;
}
// <img> for a club crest (empty span when unknown so table cells stay aligned)
export function crest(nameOrSlug, size = 20) {
  const c = clubInfo(nameOrSlug);
  const img = document.createElement("img");
  const href = c ? crestHref[c.slug] : undefined;
  if (!href) { const s = document.createElement("span"); s.className = "crest crest-empty"; s.style.width = s.style.height = `${size}px`; return s; }
  img.src = href; img.alt = c.club; img.width = img.height = size; img.className = "crest"; img.loading = "lazy";
  return img;
}
export function clubCell(name, size = 18) {
  const span = document.createElement("span"); span.className = "club-cell";
  span.append(crest(name, size), document.createTextNode(" " + (name ?? "")));
  return span;
}

// Dates: everything renders as DD/MM/YYYY (Australian). Accepts Date, epoch ms (Arrow), or "YYYY-MM-DD[ HH:MM]".
const auDate = d3.timeFormat("%d/%m/%Y");
export function toDate(v) {
  if (v == null || v === "") return null;
  if (v instanceof Date) return v;
  if (typeof v === "number") return new Date(v);
  if (typeof v === "bigint") return new Date(Number(v));
  const m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? new Date(+m[1], +m[2] - 1, +m[3]) : new Date(v);
}
export function fmtDate(v) { const d = toDate(v); return d && !isNaN(d) ? auDate(d) : "–"; }

// percentile rank (0-100) of v within values; higher = better unless invert
export function percentile(values, v, invert = false) {
  const xs = values.filter((x) => x != null && !Number.isNaN(x));
  if (v == null || !xs.length) return null;
  const below = xs.filter((x) => (invert ? x > v : x < v)).length;
  const equal = xs.filter((x) => x === v).length;
  return Math.round(100 * (below + 0.5 * equal) / xs.length);
}

export const GRADES = new Map([["Seniors", "SEN"], ["Reserves", "RES"], ["Under 18s", "U18"]]);
export const GRADE_NAME = {SEN: "Seniors", RES: "Reserves", U18: "Under 18s"};
export const GRADE_COLORS = {domain: ["SEN", "RES", "U18"], range: ["#1f77b4", "#e6550d", "#2ca02c"]};

export function label(col) { return labels[col]?.label ?? col; }
export function short(col) { return labels[col]?.short ?? label(col); }
export function describe(col) { return labels[col]?.desc ?? ""; }

const f0 = d3.format(",d"), f2 = d3.format(".2f"), f1 = d3.format(".1f");
export function fmt(col, v) {
  if (v == null || v === "" || Number.isNaN(v)) return "–";
  const t = labels[col]?.fmt;
  if (t === "date") return fmtDate(v);
  if (t === "int") return f0(v);
  if (t === "dec") return f2(v);
  if (t === "pct") return f1(v) + "%";
  if (t === "bool") return v === true || v === "true" ? "yes" : "";
  return String(v);
}

// {friendlyLabel: column} map for a set of columns — what Inputs.table / Plot want
export function headers(cols) { return Object.fromEntries(cols.map((c) => [c, label(c)])); }
// Short-form headers (P/W/D/L/GF/GA/GD/Pts) for compact tables like a ladder, where the full label is too wide.
export function shortHeaders(cols) { return Object.fromEntries(cols.map((c) => [c, short(c)])); }
// Icons stand in for a number (a count, a rate, a percentage); text, dates and yes/no flags always get a text header.
export function isNumericCol(col) { return ["int", "dec", "pct"].includes(labels[col]?.fmt); }
// Identity attributes read better as words even when their fmt is numeric — a person's age isn't a "stat" to compress.
const ICON_EXEMPT = new Set(["age"]);
// Numeric stat columns with a known icon (COL_ICONS) get the icon-only header used by the match/season tables,
// so every player-stats table in the app reads the same way. Everything else falls back to text.
export function iconHeaders(cols) { return Object.fromEntries(cols.map((c) => [c, COL_ICONS[c] && isNumericCol(c) && !ICON_EXEMPT.has(c) ? iconHeader(c, label(c)) : label(c)])); }
export function formats(cols) { return Object.fromEntries(cols.map((c) => [c, (v) => fmt(c, v)])); }

// Metric columns grouped into player-facing categories, for the chart-axis dropdowns.
const METRIC_GROUPS = [
  ["Playing time", ["apps", "starts", "sub_apps", "bench_unused", "minutes", "minutes_share_pct", "availability_pct", "start_rate_pct"]],
  ["Attack", ["goals", "goals_open_play", "goals_penalty", "own_goals", "goals_per90", "npg_per90", "team_goal_share_pct", "goals_equaliser", "goals_go_ahead", "goals_winner", "goals_late", "goals_consolation", "goals_away", "goals_vs_top_half", "goals_as_sub", "goals_per_sub_90"]],
  ["Defence", ["gf_on_pitch", "ga_on_pitch", "gd_on_pitch_per90", "gd_on_pitch_vs_team", "ga_on_pitch_per90", "ga_on_pitch_vs_team"]],
  ["Goalkeeping", ["clean_sheets", "full_matches", "clean_sheet_pct"]],
  ["Discipline", ["yellow_cards", "red_cards", "yellows_per90"]],
  ["Impact & votes", ["votes", "votes_3", "votes_per_app", "captain_apps", "borrowed_apps"]],
  ["Team stats", ["ppg_when_playing", "ppg_start_diff", "team_ladder_pos", "team_ppg"]],
  ["Career totals", ["sen_minutes", "res_minutes", "u18_minutes", "sen_apps", "n_teams", "borrowed_apps_all", "age"]],
];
// {friendlyLabel: column} map for the metric dropdowns — same shape metricOptions used to return.
export function metricOptions(cols) {
  return new Map(cols.filter((c) => labels[c]?.metric).map((c) => [label(c), c]));
}
// Sort an Inputs.select(metricOptions(cols), {...})'s <option>s into <optgroup> sections by category.
// Takes the <form> Inputs.select returns and mutates it in place, so view()/disabled/reactivity all
// keep working exactly as Inputs.select already handles them — this only reorganises the markup.
// Inputs.select gives each <option> an index-based value (not the column name), so match by its
// visible label text instead, which is exactly what metricOptions() used as the map key.
export function groupMetricSelect(form) {
  const sel = form.querySelector("select");
  if (!sel) return form;
  const selected = sel.options[sel.selectedIndex]; // moving <option>s can reset the browser's selection
  const byLabel = new Map(Array.from(sel.querySelectorAll("option")).map((o) => [o.textContent, o]));
  for (const [name, groupCols] of METRIC_GROUPS) {
    const present = groupCols.map((c) => byLabel.get(label(c))).filter(Boolean);
    if (!present.length) continue;
    const og = document.createElement("optgroup");
    og.label = name;
    for (const opt of present) { og.append(opt); byLabel.delete(opt.textContent); }
    sel.append(og);
  }
  if (selected) selected.selected = true;
  return form;
}

// Compact league / competition names for tables. Strips sponsor names (sponsors change and a
// player's match history can include junior grades that carry a different sponsor than the
// senior State League competitions — HPG Homes, Nova, RAA, Hahn and Carl's Jr./Junior all
// appear in the real data, and the same competition shows up both with and without its
// sponsor) and normalises every "Under N's" / "UN's" spelling to "UN" so it lines up with
// the Grade column's own values.
export function shortLeague(name) {
  return String(name ?? "")
    .replace(/^(HPG Homes|Nova|RAA|Hahn)\s+/, "")
    .replace(/Carl['’]s (?:Jr\.?|Junior)\s*/i, "")
    .replace("State League ", "SL")
    .replace(" - ", " ")
    .replace(/\((\d+)s\)/, "U$1")
    .replace(/Under (\d+)'?s?/g, "U$1")
    .replace(/\bU(\d+)'s\b/g, "U$1")
    .replace("(Seniors)", "").replace("(Reserves)", "Res").replace("Reserves", "Res")
    .replace("Finals Series", "Finals").replace("Final Series", "Finals")
    .replace("Federation Cup", "Fed Cup")
    .replace(/Senior Men'?s\s*/, "").replace("Trial Matches", "Trials")
    .replace(/\s+/g, " ").trim();
}
// shortLeague(), minus the trailing grade token — for use next to a Grade column, where repeating "U14"-"U18"/"Res" is redundant.
export function shortLeagueOnly(name) {
  const s = shortLeague(name);
  return s.replace(/\s*(U1[4-8]|Res)$/, "").trim() || s;
}
