// Friendly column names, descriptions and formatters shared by every page.
import {FileAttachment} from "observablehq:stdlib";
import * as d3 from "npm:d3";
import {crestHref} from "./crests.js";

export const labels = await FileAttachment("../data/labels.json").json();
export const clubs = await FileAttachment("../data/clubs.csv").csv({typed: true});
const clubBySlug = new Map(clubs.map((c) => [c.slug, c]));
const clubByName = new Map(clubs.map((c) => [c.club, c]));
export const slugify = (name) => String(name ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
export function clubInfo(nameOrSlug) { return clubByName.get(nameOrSlug) ?? clubBySlug.get(nameOrSlug) ?? clubBySlug.get(slugify(nameOrSlug)); }
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
export function formats(cols) { return Object.fromEntries(cols.map((c) => [c, (v) => fmt(c, v)])); }

// Metrics offered on the chart axes (label -> column), ordered by group as declared in labels.json
export function metricOptions(cols) {
  return new Map(cols.filter((c) => labels[c]?.metric).map((c) => [label(c), c]));
}
