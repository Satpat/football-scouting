// Small inline SVG icon set (stroke = currentColor) + column → icon mapping for table headers.
const P = {
  calendar: '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M8 2v4M16 2v4M3 10h18"/>',
  trophy: '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4z"/><path d="M7 6H4a3 3 0 0 0 3 5M17 6h3a3 3 0 0 1-3 5"/>',
  hash: '<path d="M4 9h16M4 15h16M10 3 8 21M16 3l-2 18"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  home: '<path d="M3 11 12 3l9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  flag: '<path d="M5 22V4"/><path d="M5 4h12l-2 4 2 4H5"/>',
  scoreboard: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M12 5v14M7 10v4M17 10v4"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  play: '<path d="M6 4l14 8-14 8V4z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  ball: '<circle cx="12" cy="12" r="9"/><path d="M12 7l4.8 3.5-1.8 5.6H9L7.2 10.5 12 7z"/><path d="M12 3v4M20.6 9.5l-3.8 1M3.4 9.5l3.8 1M17.5 19.4 15 16.1M6.5 19.4 9 16.1"/>',
  star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9L12 3z"/>',
  card: '<rect x="6" y="3" width="12" height="18" rx="2"/>',
  captain: '<path d="M3 8h18l-2 12H5L3 8z"/><path d="M3 8l4-4h10l4 4"/><path d="M14.5 12a2.5 2.5 0 1 0 0 4"/>',
  gloves: '<path d="M7 11V5a2 2 0 1 1 4 0v5M11 10V4a2 2 0 1 1 4 0v6M15 10V6a2 2 0 1 1 4 0v8a6 6 0 0 1-6 6h-2a6 6 0 0 1-6-6v-3a2 2 0 1 1 4 0"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  cake: '<path d="M4 21h16M5 21v-6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v6"/><path d="M8 13V9M12 13V9M16 13V9"/><path d="M12 5v4M8 6v3M16 6v3"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  shirt: '<path d="M8 3 4 6l2 4 2-1v11h8V9l2 1 2-4-4-3a4 4 0 0 1-8 0z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 13 9 5 9-5M3 17l9 5 9-5"/>',
  list: '<path d="M9 6h12M9 12h12M9 18h12M4 6h1M4 12h1M4 18h1"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0"/><circle cx="17" cy="9" r="3"/><path d="M15.5 14.5A6 6 0 0 1 22 20"/>',
  route: '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8 18h6a3 3 0 0 0 0-6h-4a3 3 0 0 1 0-6h6"/>',
  trending: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  ladder: '<path d="M7 3v18M17 3v18M7 7h10M7 12h10M7 17h10"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  percent: '<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  bench: '<path d="M3 12h18v3H3zM6 15v4M18 15v4M5 12V8h14v4"/>',
  swap: '<path d="M7 16V4M4 7l3-3 3 3"/><path d="M17 8v12M20 17l-3 3-3-3"/>',
  zap: '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  handshake: '<path d="M4 9l4-3h8l4 3-4 8H8L4 9z"/><path d="M8 17v3h8v-3"/>',
  redcard: '<rect x="6" y="3" width="12" height="18" rx="2" fill="#d62728" stroke="#d62728"/>',
  yellowcard: '<rect x="6" y="3" width="12" height="18" rx="2" fill="#f2c200" stroke="#f2c200"/>',
  gem: '<path d="M6 3h12l4 6-10 12L2 9l4-6z"/><path d="M2 9h20M9 3l3 6 3-6M6 9l6 12M18 9l-6 12"/>',
  whistle: '<circle cx="9" cy="14" r="5"/><path d="M13 12l8-4v3l-7 3"/><path d="M9 9V6"/>',
  // rate/per-90 gauge: distinct from the raw-count icons it sits beside, so a rate column
  // reads as "a rate" at a glance without needing to parse the suffix text first
  gauge: '<path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 18 16.5 10.5"/><circle cx="12" cy="18" r="1.3" fill="currentColor" stroke="none"/>',
};

export const COL_ICONS = {
  date: "calendar", date_local: "calendar", league: "trophy", comp: "trophy", full_round: "hash", round: "hash",
  opponent: "shield", ha: "home", home_away: "home", result: "flag", score: "scoreboard", did_play: "check",
  starting: "play", minutes: "clock", goals: "ball", goals_open_play: "ball", goals_penalty: "target", own_goals: "minus",
  votes: "star", yellow_cards: "yellowcard", red_cards: "redcard", is_captain: "captain", captain_apps: "captain",
  is_goalkeeper: "gloves", clean_sheet: "gloves", clean_sheets: "gloves", clean_sheet_pct: "gloves", in_dataset: "database",
  borrowed_side: "handshake", flag: "globe", apps: "list", starts: "play", sub_apps: "swap", bench_unused: "bench", borrowed: "handshake", borrowed_apps: "handshake",
  goals_go_ahead: "trending", goals_winner: "zap", goals_equaliser: "swap", goals_late: "clock",
  team_gf: "plus", team_ga: "minus", age: "cake", nationality: "globe", jersey: "shirt", role: "user", grade: "layers",
  n_teams: "users", grades_played: "route", highest_grade: "trending", sen_minutes: "clock", team_ladder_pos: "ladder",
  team_ppg: "chart", npg_per90: "gauge", goals_per90: "gauge", votes_per_app: "star", team_goal_share_pct: "percent",
  minutes_share_pct: "percent", start_rate_pct: "play", gd_on_pitch_vs_team: "chart", ga_on_pitch_per90: "gauge",
  yellows_per90: "gauge", ppg_when_playing: "chart", ppg_start_diff: "chart", team: "shield", season: "calendar",
  clubs: "shield", leagues: "trophy", played: "list", started: "play", was_goalkeeper: "gloves",
};

// Short qualifier shown beside the icon when several columns share a base icon.
export const COL_SUFFIX = {
  goals_open_play: "NP", goals_per90: "/90", npg_per90: "NP/90", goals_penalty: "pen", own_goals: "OG",
  team_goal_share_pct: "goals", minutes_share_pct: "min", start_rate_pct: "%", clean_sheet_pct: "%",
  gd_on_pitch_vs_team: "GD", ga_on_pitch_per90: "GA/90", yellows_per90: "/90", votes_per_app: "/app", ppg_when_playing: "PPG", ppg_start_diff: "±PPG",
  goals_late: "75'", goals_equaliser: "=", goals_go_ahead: "lead", goals_winner: "win", sen_minutes: "SEN", team_gf: "GF", team_ga: "GA",
  sub_apps: "sub", captain_apps: "C", borrowed_apps: "brw", n_teams: "", highest_grade: "top",
};

export function icon(name, {size = 16, title} = {}) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("width", size); svg.setAttribute("height", size);
  svg.setAttribute("fill", "none"); svg.setAttribute("stroke", "currentColor"); svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round"); svg.setAttribute("stroke-linejoin", "round"); svg.setAttribute("class", "ico");
  svg.setAttribute("aria-label", title ?? name); svg.setAttribute("role", "img");
  svg.innerHTML = (title ? `<title>${title}</title>` : "") + (P[name] ?? P.hash);
  return svg;
}

// Header cell: icon only, full column name in the tooltip (and for screen readers).
// Diamond mark for hidden gems (Reserves/U18 player with no senior minutes). Tooltip carries the meaning.
export function gemMark(title = "Hidden gem: no senior minutes this season") {
  const span = document.createElement("span");
  span.className = "gem-mark"; span.title = title; span.setAttribute("aria-label", title);
  span.append(icon("gem", {size: 14, title}));
  return span;
}

export function iconHeader(col, label, {size = 16, suffix = COL_SUFFIX[col]} = {}) {
  const span = document.createElement("span");
  span.className = "ico-hdr"; span.title = label; span.setAttribute("aria-label", label);
  span.append(icon(COL_ICONS[col] ?? "hash", {size, title: label}));
  if (suffix) { const q = document.createElement("small"); q.className = "ico-q"; q.textContent = suffix; span.append(q); }
  return span;
}
export function iconLabel(col, label, {size = 15} = {}) {
  const span = document.createElement("span");
  span.className = "ico-label";
  span.append(icon(COL_ICONS[col] ?? "hash", {size, title: label}), document.createTextNode(" " + label));
  return span;
}
