// Exports for the "Ask the data" chat page: copying a turn (or the whole conversation) to
// the clipboard as rich text, and downloading a turn (or the whole conversation) as a PDF —
// in both cases the answer prose plus its result tables, not the collapsed SQL detail.
//
// Content is modelled as a flat array of "blocks" (heading/paragraph/list/table), built once
// per turn in chat.md and consumed by both the clipboard and PDF renderers below, so the two
// output formats can't drift out of sync with each other.
import {tableHtml, tableRows, escapeHtml, labelFor} from "./export.js";

// Reduces a rendered markdown DOM node (from renderMarkdown()) to blocks. Bold/italic/links
// within a paragraph are flattened to plain text — full inline-formatting fidelity in a PDF
// would need per-run font switching for marginal benefit here.
export function htmlToBlocks(container) {
  const blocks = [];
  for (const el of container.children) {
    const tag = el.tagName;
    if (/^H[1-6]$/.test(tag)) blocks.push({type: "heading", text: el.textContent.trim()});
    else if (tag === "UL" || tag === "OL") {
      blocks.push({type: "list", items: [...el.children].map((li) => li.textContent.trim())});
    } else if (tag === "TABLE") {
      const rows = [...el.querySelectorAll("tr")].map((tr) => [...tr.children].map((c) => c.textContent.trim()));
      if (rows.length) blocks.push({type: "table", header: rows[0], body: rows.slice(1)});
    } else {
      const text = el.textContent.trim();
      if (text) blocks.push({type: "paragraph", text});
    }
  }
  return blocks;
}

// A "data table" block — the raw rows/columns/format/links a dataTable() call would take —
// stays as-is until render time, since the clipboard and PDF renderers need different things
// from it (an HTML <table> vs. plain autoTable() rows).
export function dataTableBlock(rows, columns, opts = {}) {
  return {type: "datatable", rows, columns, opts};
}

function blockHtml(block) {
  if (block.type === "heading") return `<h3>${escapeHtml(block.text)}</h3>`;
  if (block.type === "paragraph") return `<p>${escapeHtml(block.text)}</p>`;
  if (block.type === "list") return `<ul>${block.items.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
  if (block.type === "table") {
    const thead = `<tr>${block.header.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr>`;
    const tbody = block.body.map((r) => `<tr>${r.map((c) => `<td>${escapeHtml(c)}</td>`).join("")}</tr>`).join("");
    return `<table border="1" cellspacing="0" cellpadding="4">${thead}${tbody}</table>`;
  }
  if (block.type === "datatable") return tableHtml(block.rows, block.columns, block.opts).html;
  return "";
}

function blockText(block) {
  if (block.type === "heading") return `${block.text}\n${"=".repeat(block.text.length)}`;
  if (block.type === "paragraph") return block.text;
  if (block.type === "list") return block.items.map((i) => `- ${i}`).join("\n");
  if (block.type === "table") return [block.header.join("\t"), ...block.body.map((r) => r.join("\t"))].join("\n");
  if (block.type === "datatable") return tableHtml(block.rows, block.columns, block.opts).tsv;
  return "";
}

export async function copyBlocks(blocks) {
  const html = blocks.map(blockHtml).join("\n");
  const text = blocks.map(blockText).join("\n\n");
  await navigator.clipboard.write([
    new ClipboardItem({
      "text/html": new Blob([html], {type: "text/html"}),
      "text/plain": new Blob([text], {type: "text/plain"}),
    }),
  ]);
}

export async function blocksToPdf(blocks, filename) {
  const {jsPDF} = await import("npm:jspdf@3.0.3");
  const {default: autoTable} = await import("npm:jspdf-autotable@5.0.8");

  const doc = new jsPDF({unit: "pt"});
  const marginX = 40;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const maxWidth = pageWidth - marginX * 2;
  const lineGap = 14;
  let y = 50;

  function ensureSpace(need) {
    if (y + need > pageHeight - 40) {
      doc.addPage();
      y = 50;
    }
  }
  function writeLines(text, {bold = false, size = 10.5, gapAfter = 8} = {}) {
    doc.setFont(undefined, bold ? "bold" : "normal");
    doc.setFontSize(size);
    const lines = doc.splitTextToSize(text, maxWidth);
    ensureSpace(lines.length * lineGap);
    doc.text(lines, marginX, y);
    y += lines.length * lineGap + gapAfter;
  }

  for (const block of blocks) {
    if (block.type === "heading") {
      writeLines(block.text, {bold: true, size: 13, gapAfter: 10});
    } else if (block.type === "paragraph") {
      writeLines(block.text);
    } else if (block.type === "list") {
      for (const item of block.items) writeLines(`•  ${item}`, {gapAfter: 2});
      y += 6;
    } else if (block.type === "table" || block.type === "datatable") {
      const {header, body} = block.type === "table"
        ? {header: block.header, body: block.body}
        : tableRows(block.rows, block.columns, block.opts);
      ensureSpace(40);
      autoTable(doc, {
        head: [header], body,
        startY: y, margin: {left: marginX, right: marginX},
        styles: {fontSize: 8, cellPadding: 3, overflow: "linebreak"},
        headStyles: {fillColor: [40, 40, 40]},
        theme: "grid",
      });
      y = doc.lastAutoTable.finalY + 14;
    }
  }
  doc.save(filename);
}
