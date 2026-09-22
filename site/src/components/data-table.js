// Shared table renderer backing every data table on the site, replacing Observable's
// Inputs.table so table markup/CSS is 100% ours (no more fighting Observable's own
// inputs.css) and so we get sorting, pagination, column visibility and pinning that
// Inputs.table doesn't offer. @tanstack/table-core is headless: it computes row/column
// state but renders nothing, so this module owns a small imperative render() loop that
// rebuilds the <thead>/<tbody> (and the pager/column-menu, when enabled) on every state
// change. Call sites keep passing the same shapes Inputs.table already took — an array
// of column keys plus header/format maps from labels.js — instead of hand-written
// TanStack ColumnDef[] objects.
import {createTable, getCoreRowModel, getSortedRowModel, getPaginationRowModel} from "npm:@tanstack/table-core@8";
import {isNumericCol} from "./labels.js";
import {downloadExcel, copyTable} from "./export.js";

// format[col] callbacks receive (value, row) — the row's own data object — not an index
// into some outer array, so results stay correct under sorting/pagination.
export function dataTable(rows, {
  columns,
  header = {},
  format = {},
  width = {},
  links = {},
  numeric,
  pageSize = null,
  sort = null,
  sortDesc = true,
  enableMultiSort = true,
  pin = [],
  columnVisibility: showColumnMenu = false,
  exportable = true,
  exportFilename = "export",
  className = "",
} = {}) {
  const columnDefs = columns.map((col) => ({
    id: col,
    accessorFn: (row) => row[col],
    header: () => header[col] ?? col,
    cell: (info) => {
      const fn = format[col];
      const value = info.getValue();
      return fn ? fn(value, info.row.original) : value;
    },
    enableSorting: true,
    meta: {
      numeric: numeric ? numeric(col) : isNumericCol(col),
      width: width[col],
    },
  }));

  let state = {
    sorting: sort ? [{id: sort, desc: sortDesc}] : [],
    columnVisibility: {},
    columnPinning: {left: pin},
    // Only exercised once 2+ columns are pinned — getStart() sums preceding pinned columns'
    // getSize(), which reads state.columnSizing internally and throws if it's undefined.
    columnSizing: {},
    ...(pageSize ? {pagination: {pageIndex: 0, pageSize}} : {}),
  };

  const table = createTable({
    data: rows,
    columns: columnDefs,
    state,
    onStateChange: (updater) => {
      state = typeof updater === "function" ? updater(state) : updater;
      table.setOptions((prev) => ({...prev, state}));
      render();
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    ...(pageSize ? {getPaginationRowModel: getPaginationRowModel()} : {}),
    enableMultiSort,
    enableSortingRemoval: false,
    renderFallbackValue: null,
  });

  const root = document.createElement("div");
  root.className = `data-table ${className}`.trim();

  const scroll = document.createElement("div");
  scroll.className = "table-scroll";
  const tableEl = document.createElement("table");
  const colgroup = document.createElement("colgroup");
  const thead = document.createElement("thead");
  const tbody = document.createElement("tbody");
  tableEl.append(colgroup, thead, tbody);
  scroll.append(tableEl);
  root.append(scroll);

  let toolbar = null;
  let colMenu = null;
  let exportMenu = null;
  let pager = null;

  // Full label for the column-visibility menu: header[col] is either plain text or (for
  // icon headers) a DOM node that already carries the full name in its aria-label.
  function labelFor(col) {
    const h = header[col];
    if (typeof h === "string") return h;
    if (h instanceof Node) return h.getAttribute?.("aria-label") || h.textContent || col;
    return col;
  }

  function setCellContent(el, content) {
    el.replaceChildren();
    if (content instanceof Node) el.append(content);
    else if (content != null) el.append(String(content));
  }

  function applyColumnStyles(cell, column) {
    const meta = column.columnDef.meta ?? {};
    if (meta.numeric) cell.classList.add("dt-num");
    if (column.getIsPinned()) {
      cell.classList.add("dt-pinned");
      cell.style.position = "sticky";
      cell.dataset.pinCol = column.id;
      // left offset is set in a separate DOM-measurement pass (applyPinnedOffsets), not here —
      // column.getStart("left") sums TanStack's abstract column-sizing model, which we never
      // configure (no size/minSize set anywhere), so it defaults every column to the same
      // assumed width regardless of how wide it actually renders — good for a "#" column,
      // wildly wrong for anything wider, leaving a gap or overlap next to the pinned column.
    }
  }

  // Cumulative left offset for pinned columns, from real rendered widths (not TanStack's
  // assumed column-sizing model — see applyColumnStyles). Runs after thead+tbody are built,
  // using the header cell's width as the authoritative width for that whole column.
  function applyPinnedOffsets() {
    let offset = 0;
    for (const colId of pin) {
      const headerCell = thead.querySelector(`th[data-pin-col="${CSS.escape(colId)}"]`);
      if (!headerCell) continue;
      const width = headerCell.getBoundingClientRect().width;
      tableEl.querySelectorAll(`[data-pin-col="${CSS.escape(colId)}"]`).forEach((el) => {
        el.style.left = `${offset}px`;
      });
      offset += width;
    }
  }

  function render() {
    // table.getVisibleLeafColumns() returns columns in their *defined* order, filtered by
    // visibility — it does NOT reorder pinned columns to the front, unlike the header/row
    // cells below (built from getHeaderGroups()/getVisibleCells(), which do). Deriving the
    // colgroup from the header row's own column order instead keeps every <col> aligned with
    // the actual rendered cell in that visual position — a mismatched colgroup silently
    // applies each column's width to the wrong rendered column, which reads as some columns
    // clipped and others too wide, worse the further a pinned column moved from its defined
    // position.
    const orderedColumns = table.getHeaderGroups()[0]?.headers.map((h) => h.column) ?? table.getVisibleLeafColumns();
    colgroup.replaceChildren();
    for (const column of orderedColumns) {
      const col = document.createElement("col");
      const w = column.columnDef.meta?.width;
      if (w) col.style.width = `${w}px`;
      colgroup.append(col);
    }

    thead.replaceChildren();
    for (const headerGroup of table.getHeaderGroups()) {
      const tr = document.createElement("tr");
      for (const h of headerGroup.headers) {
        const th = document.createElement("th");
        const column = h.column;
        setCellContent(th, column.columnDef.header());
        if (column.getCanSort()) {
          th.classList.add("dt-sortable");
          const sorted = column.getIsSorted(); // false | "asc" | "desc"
          if (sorted) th.dataset.sort = sorted;
          const caret = document.createElement("span");
          caret.className = "dt-caret";
          if (state.sorting.length > 1) {
            const idx = column.getSortIndex();
            if (idx > -1 && sorted) caret.dataset.priority = String(idx + 1);
          }
          th.append(caret);
          th.addEventListener("click", column.getToggleSortingHandler());
        }
        applyColumnStyles(th, column);
        tr.append(th);
      }
      thead.append(tr);
    }

    tbody.replaceChildren();
    for (const row of table.getRowModel().rows) {
      const tr = document.createElement("tr");
      for (const cell of row.getVisibleCells()) {
        const td = document.createElement("td");
        setCellContent(td, cell.column.columnDef.cell(cell.getContext()));
        applyColumnStyles(td, cell.column);
        tr.append(td);
      }
      tbody.append(tr);
    }

    if (pin.length) applyPinnedOffsets();
    if (pageSize) renderPager();
    if (showColumnMenu) renderColMenu();
    if (exportable) renderExportMenu();
  }

  function ensureToolbar() {
    if (!toolbar) {
      toolbar = document.createElement("div");
      toolbar.className = "dt-toolbar";
      root.prepend(toolbar);
    }
    return toolbar;
  }

  // Every open menu shares one document-level click-outside handler and one open item at a
  // time, so opening the export menu closes an already-open column menu and vice versa.
  function makeMenu(className, btnClassName, btnLabel) {
    const wrap = document.createElement("div");
    wrap.className = className;
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = btnClassName; btn.textContent = btnLabel;
    const pop = document.createElement("div");
    pop.className = `${className}-pop`;
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const opening = !pop.classList.contains("open");
      document.querySelectorAll(".dt-colmenu-pop.open, .dt-exportmenu-pop.open").forEach((p) => p.classList.remove("open"));
      if (opening) pop.classList.add("open");
    });
    document.addEventListener("click", (e) => { if (!wrap.contains(e.target)) pop.classList.remove("open"); });
    wrap.append(btn, pop);
    return {wrap, btn, pop};
  }

  function renderPager() {
    if (!pager) {
      pager = document.createElement("div");
      pager.className = "dt-pager";
      root.append(pager);
    }
    pager.replaceChildren();
    const prevBtn = document.createElement("button");
    prevBtn.type = "button"; prevBtn.className = "mbtn"; prevBtn.textContent = "Prev";
    prevBtn.disabled = !table.getCanPreviousPage();
    prevBtn.addEventListener("click", () => table.previousPage());
    const nextBtn = document.createElement("button");
    nextBtn.type = "button"; nextBtn.className = "mbtn"; nextBtn.textContent = "Next";
    nextBtn.disabled = !table.getCanNextPage();
    nextBtn.addEventListener("click", () => table.nextPage());
    const info = document.createElement("span");
    info.className = "dt-pager-info";
    const {pageIndex} = table.getState().pagination;
    info.textContent = `Page ${pageIndex + 1} of ${Math.max(1, table.getPageCount())}`;
    pager.append(prevBtn, info, nextBtn);
  }

  function renderColMenu() {
    if (!colMenu) {
      colMenu = makeMenu("dt-colmenu", "dt-colmenu-btn", "Columns ▾");
      ensureToolbar().append(colMenu.wrap);
    }
    colMenu.pop.replaceChildren();
    for (const column of table.getAllLeafColumns()) {
      const item = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = column.getIsVisible();
      cb.addEventListener("change", column.getToggleVisibilityHandler());
      item.append(cb, document.createTextNode(" " + labelFor(column.id)));
      colMenu.pop.append(item);
    }
  }

  // "All rows" is table.getSortedRowModel() — the full filtered/sorted set the pagination
  // model itself slices from — vs table.getRowModel(), which is that same set narrowed to
  // whatever page is currently showing. Only offer the this-page/all-rows choice when the
  // table is actually paginated; otherwise they're the same rows and the choice is noise.
  function visibleColumns() {
    return table.getVisibleLeafColumns().map((c) => c.id);
  }
  function allRows() {
    return table.getSortedRowModel().rows.map((r) => r.original);
  }
  function pageRows() {
    return table.getRowModel().rows.map((r) => r.original);
  }

  function renderExportMenu() {
    if (!exportMenu) {
      exportMenu = makeMenu("dt-exportmenu", "dt-exportmenu-btn", "Export ▾");
      ensureToolbar().append(exportMenu.wrap);
    }
    const pop = exportMenu.pop;
    pop.replaceChildren();
    const cols = visibleColumns();
    const exportOpts = {header, format, links};

    function item(label, onClick) {
      const btn = document.createElement("button");
      btn.type = "button"; btn.className = "dt-exportmenu-item"; btn.textContent = label;
      btn.addEventListener("click", async () => {
        const original = btn.textContent;
        try {
          await onClick();
          btn.textContent = "Done ✓";
        } catch (err) {
          console.error("Table export failed:", err);
          btn.textContent = "Couldn't copy — try again";
        }
        setTimeout(() => { btn.textContent = original; }, 1600);
      });
      pop.append(btn);
    }

    const paginated = Boolean(pageSize);
    item(paginated ? `Download Excel — all rows` : "Download Excel", async () => {
      downloadExcel(allRows(), cols, {...exportOpts, filename: `${exportFilename}.xlsx`});
    });
    if (paginated) {
      item("Download Excel — this page", async () => {
        downloadExcel(pageRows(), cols, {...exportOpts, filename: `${exportFilename}-page.xlsx`});
      });
    }
    item(paginated ? "Copy table — all rows" : "Copy table", async () => {
      await copyTable(allRows(), cols, exportOpts);
    });
    if (paginated) {
      item("Copy table — this page", async () => {
        await copyTable(pageRows(), cols, exportOpts);
      });
    }
  }

  render();
  // The table isn't attached to the document yet at this point (the caller inserts the
  // returned node afterward), so the getBoundingClientRect() measurements applyPinnedOffsets
  // took during that first render() all read as 0 width. Once actually laid out post-attach,
  // remeasure — every render() after this one runs while already attached, so this one-time
  // follow-up is only needed for the initial paint.
  if (pin.length) requestAnimationFrame(() => applyPinnedOffsets());
  return root;
}
