// Friendly column names, descriptions and formatters shared by every page.
import {FileAttachment} from "observablehq:stdlib";
import * as d3 from "npm:d3";

export const labels = await FileAttachment("../data/labels.json").json();

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
  if (t === "int") return f0(v);
  if (t === "dec") return f2(v);
  if (t === "pct") return f1(v) + "%";
  if (t === "bool") return v ? "yes" : "";
  return String(v);
}

// {friendlyLabel: column} map for a set of columns — what Inputs.table / Plot want
export function headers(cols) { return Object.fromEntries(cols.map((c) => [c, label(c)])); }
export function formats(cols) { return Object.fromEntries(cols.map((c) => [c, (v) => fmt(c, v)])); }

// Metrics offered on the chart axes (label -> column), ordered by group as declared in labels.json
export function metricOptions(cols) {
  return new Map(cols.filter((c) => labels[c]?.metric).map((c) => [label(c), c]));
}
