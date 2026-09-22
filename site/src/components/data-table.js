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

// format[col] callbacks receive (value, row) — the row's own data object — not an index
// into some outer array, so results stay correct under sorting/pagination.
export function dataTable(rows, {
  columns,
  header = {},
  format = {},
  width = {},
  numeric,
  pageSize = null,
  sort = null,
  sortDesc = true,
  enableMultiSort = true,
  pin = [],
  columnVisibility: showColumnMenu = false,
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

  let colMenu = null;
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
      cell.style.left = `${column.getStart("left")}px`;
    }
  }

  function render() {
    colgroup.replaceChildren();
    for (const column of table.getVisibleLeafColumns()) {
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

    if (pageSize) renderPager();
    if (showColumnMenu) renderColMenu();
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
      const wrap = document.createElement("div");
      wrap.className = "dt-colmenu";
      const btn = document.createElement("button");
      btn.type = "button"; btn.className = "dt-colmenu-btn"; btn.textContent = "Columns ▾";
      const pop = document.createElement("div");
      pop.className = "dt-colmenu-pop";
      btn.addEventListener("click", (e) => { e.stopPropagation(); pop.classList.toggle("open"); });
      document.addEventListener("click", (e) => { if (!wrap.contains(e.target)) pop.classList.remove("open"); });
      wrap.append(btn, pop);
      root.prepend(wrap);
      colMenu = {wrap, pop};
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

  render();
  return root;
}
