// Table export: download as .xlsx (real Excel numbers/number-formats, real clickable
// hyperlinks) or copy to the clipboard as an HTML <table> (pastes as real cells into
// Excel/Sheets/Word/Notion/Slack) with a TSV plain-text fallback.
//
// SheetJS stopped publishing current builds to the public npm registry in 2023 (a dispute
// with npm Inc., unrelated to the library itself) — the npm-registry mirror Framework's own
// `npm:` specifier would resolve to is frozen at 0.18.5 with since-patched vulnerabilities.
// This is the one place on the site that imports directly from SheetJS's own CDN instead of
// the usual npm: convention, to get a current, patched build.
import * as XLSX from "https://cdn.sheetjs.com/xlsx-0.20.3/package/xlsx.mjs";
import {labels, isNumericCol, fmt} from "./labels.js";

export function labelFor(col, header) {
  const h = header?.[col];
  if (typeof h === "string") return h;
  if (h instanceof Node) return h.getAttribute?.("aria-label") || h.textContent?.trim() || col;
  return col;
}

function numFmtFor(col) {
  const t = labels[col]?.fmt;
  if (t === "int") return "#,##0";
  if (t === "dec") return "0.00";
  if (t === "pct") return "0.0%";
  return "General";
}

// A link callback typically returns a site-relative path ("./player?id=...") that only
// resolves inside the live page — once the URL leaves the browser (opened in Excel, pasted
// into Word/Notion), there's no "current page" to resolve it against, so it must be absolute.
function toAbsolute(url) {
  try {
    return new URL(url, location.href).href;
  } catch {
    return url;
  }
}

// Resolves one cell's export value. A linked column always exports the row's plain raw text
// plus a URL (not whatever badge/emoji-decorated HTML the on-screen cell renders). A numeric
// column carries two representations: `excelNumber` — the raw value, scaled for Excel's own
// number-format code (pct values are stored as e.g. 40.4, so they're divided by 100 for
// Excel's "×100 and append %" display convention) — and `text`, the same site-wide fmt()
// used everywhere else ("78.5%", "1,460"), for the plain HTML/TSV clipboard path where
// there's no cell-level number formatting to reinterpret a raw scaled value. Everything else
// runs through the same format() callback the on-screen table already uses, reducing any
// DOM-node cell (crest images, tooltips) to its plain text.
function cellValue(col, row, {format, links}) {
  if (links?.[col]) {
    const url = links[col](row);
    return {text: row[col] == null ? "" : String(row[col]), url: url ? toAbsolute(url) : null};
  }
  const raw = row[col];
  if (isNumericCol(col) || typeof raw === "number") {
    const num = typeof raw === "number" && !Number.isNaN(raw) ? raw : null;
    if (num == null) return {text: ""};
    const excelNumber = labels[col]?.fmt === "pct" ? num / 100 : num;
    return {excelNumber, text: fmt(col, num)};
  }
  const fn = format?.[col];
  let rendered = fn ? fn(raw, row) : raw;
  if (rendered instanceof Node) rendered = rendered.textContent;
  return {text: rendered == null ? "" : String(rendered).trim()};
}

function buildCells(rows, columns, opts) {
  return rows.map((row) => columns.map((col) => cellValue(col, row, opts)));
}

export function downloadExcel(rows, columns, {header = {}, format = {}, links = {}, filename = "export.xlsx", sheetName = "Data"} = {}) {
  const headerRow = columns.map((col) => labelFor(col, header));
  const cells = buildCells(rows, columns, {format, links});
  const aoa = [headerRow, ...cells.map((r) => r.map((c) => (c.excelNumber != null ? c.excelNumber : c.text ?? "")))];
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  cells.forEach((r, ri) => {
    r.forEach((c, ci) => {
      const addr = XLSX.utils.encode_cell({r: ri + 1, c: ci});
      const cell = ws[addr];
      if (!cell) return;
      if (c.excelNumber != null) cell.z = numFmtFor(columns[ci]);
      if (c.url) cell.l = {Target: c.url};
    });
  });
  ws["!cols"] = columns.map((col) => ({wch: Math.max(10, labelFor(col, header).length + 2)}));
  // Filter dropdowns on the header row, so the sheet is immediately sortable/filterable in
  // Excel without the reader having to select-all + Insert Filter first. (A frozen header row
  // would be the natural companion, but SheetJS's community/free build accepts `ws["!freeze"]`
  // without erroring yet silently omits it from the written file — confirmed by inspecting the
  // output XML directly — so it appears to be a Pro-tier write feature; not worth chasing further.)
  const range = {s: {r: 0, c: 0}, e: {r: cells.length, c: columns.length - 1}};
  ws["!autofilter"] = {ref: XLSX.utils.encode_range(range)};
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  XLSX.writeFileXLSX(wb, filename);
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}

// Plain-text {header, body} rows — the same fmt()-formatted text tableHtml() puts in table
// cells, without the HTML/TSV wrapping — for callers building their own document (PDF tables,
// rich clipboard content spanning more than one table) that just need formatted cell text.
export function tableRows(rows, columns, opts = {}) {
  const {header = {}} = opts;
  const headerRow = columns.map((col) => labelFor(col, header));
  const body = buildCells(rows, columns, opts).map((r) => r.map((c) => c.text ?? ""));
  return {header: headerRow, body};
}

export function tableHtml(rows, columns, {header = {}, format = {}, links = {}} = {}) {
  const headerRow = columns.map((col) => labelFor(col, header));
  const cells = buildCells(rows, columns, {format, links});
  const thead = `<tr>${headerRow.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr>`;
  const tbody = cells.map((r) => `<tr>${r.map((c) => {
    const text = c.text ?? "";
    return `<td>${c.url ? `<a href="${escapeHtml(c.url)}">${escapeHtml(text)}</a>` : escapeHtml(text)}</td>`;
  }).join("")}</tr>`).join("");
  const html = `<table border="1" cellspacing="0" cellpadding="4">${thead}${tbody}</table>`;
  const tsv = [headerRow, ...cells.map((r) => r.map((c) => c.text ?? ""))]
    .map((r) => r.join("\t")).join("\n");
  return {html, tsv};
}

export async function copyTable(rows, columns, opts = {}) {
  const {html, tsv} = tableHtml(rows, columns, opts);
  await navigator.clipboard.write([
    new ClipboardItem({
      "text/html": new Blob([html], {type: "text/html"}),
      "text/plain": new Blob([tsv], {type: "text/plain"}),
    }),
  ]);
}
