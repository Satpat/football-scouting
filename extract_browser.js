// DRIBL enriched extraction — run inside the browser pane on the relevant *.dribl.com
// site (Cloudflare blocks non-browser clients). Paste the whole file into the JS console,
// then run the phases one at a time:
//   await __v2.leagues();  await __v2.results();  await __v2.matchcentres();
//   await __v2.members();  await __v2.ladders();
//   __v2.dump('meta'); __v2.dump('mc'); __v2.dump('members', 0, 3); ... (see dump())
// Each phase stores its output on window.__v2.state so a failed phase can be re-run.
//
// This site now pulls from two separate DRIBL tenants, each with its own site/tenant/
// season id — run this script separately on each origin with that source's constants:
//
//   Football SA (fsa.dribl.com) — SL1, SL2, NPL men's:
//     TENANT = '3pmvvjLmvJ', SEASON = '7MNGzMbmAz'
//     COMPS = ['vbd911WYd4', 'gld4ppz2dW', '08NOppXWKZ']
//     (NPL Women's, 'LBdDxx9Jdb', is a separate competition, intentionally not included)
//
//   SAASL (saasl.dribl.com) — Home and Away only (excludes SAASL Cups and preseason
//   trials/shields, same "no trials/cups" convention as the Football SA leagues):
//     TENANT = 'V8dnR1odwL', SEASON = '7MNGzzEmAz'
//     COMPS = ['1pN6ppZAd0']

(() => {
  const B = 'https://mc-api.dribl.com/api/';
  const TENANT = '3pmvvjLmvJ';
  const SEASON = '7MNGzMbmAz';
  const COMPS = ['vbd911WYd4', 'gld4ppz2dW', '08NOppXWKZ']; // SL1, SL2, NPL (men's) — see header for the SAASL alternative
  const TZ = 'Australia/Adelaide';
  const BATCH = 15;

  const st = (window.__v2 && window.__v2.state) || { leagues: [], fixtures: [], mc: {}, members: {}, ladders: {}, errors: [] };

  async function get(path) {
    const r = await fetch(B + path);
    if (!r.ok) throw new Error(`${r.status} ${path}`);
    return r.json();
  }
  const attrs = (rec) => (rec && rec.attributes) ? { id: rec.id, ...rec.attributes } : rec;
  const list = (body) => Array.isArray(body) ? body : (Array.isArray(body.data) ? body.data : Object.values(body.data || {}));

  async function batched(items, fn) {
    const out = [];
    for (let i = 0; i < items.length; i += BATCH) {
      const chunk = items.slice(i, i + BATCH);
      const res = await Promise.all(chunk.map(async (it) => {
        try { return await fn(it); } catch (e) { st.errors.push({ item: it, error: String(e) }); return null; }
      }));
      out.push(...res);
    }
    return out;
  }

  const api = {
    state: st,
    async leagues() {
      const body = await get(`competitions?disable_paging=true&tenant=${TENANT}&season=${SEASON}`);
      st.leagues = [];
      for (const c of list(body)) {
        const ca = attrs(c);
        if (!COMPS.includes(ca.hash_id || ca.id)) continue;
        for (const l of (ca.leagues || [])) {
          const la = attrs(l);
          st.leagues.push({ competition_id: ca.hash_id || ca.id, competition: ca.name, league_id: la.hash_id || la.id, league: la.name });
        }
      }
      return st.leagues.length;
    },
    async results() {
      // results is cursor-paginated (30 per page); disable_paging is ignored, so follow next_cursor.
      st.fixtures = [];
      for (const lg of st.leagues) {
        let cursor = null, pages = 0;
        do {
          const body = await get(`results?season=${SEASON}&competition=${lg.competition_id}&league=${lg.league_id}&tenant=${TENANT}&results=1&timezone=${encodeURIComponent(TZ)}` + (cursor ? `&cursor=${cursor}` : ''));
          for (const f of list(body)) {
            const a = attrs(f);
            if (a.status !== 'complete') continue;
            st.fixtures.push({ ...lg, hash_id: f.hash_id || a.hash_id || a.id, match_hash_id: a.match_hash_id, home_team_hash_id: a.home_team_hash_id, away_team_hash_id: a.away_team_hash_id, date: a.date, name: a.name, round: a.round_label || a.round });
          }
          cursor = body.meta && body.meta.next_cursor;
          pages += 1;
        } while (cursor && pages < 100);
      }
      return st.fixtures.length;
    },
    async matchcentres() {
      const todo = st.fixtures.filter(f => f.match_hash_id && !st.mc[f.match_hash_id]);
      await batched(todo, async (f) => {
        const body = await get(`matchcentre/${f.match_hash_id}?tenant=${TENANT}`);
        const a = attrs(body.data || body);
        delete a.home_logo; delete a.away_logo; delete a.body_logo;
        (a.referees || []).forEach(r => delete r.image);
        (a.penalties || []).forEach(p => delete p.image);
        st.mc[f.match_hash_id] = a;
      });
      return Object.keys(st.mc).length;
    },
    async members() {
      const todo = [];
      for (const f of st.fixtures) {
        const mc = st.mc[f.match_hash_id]; if (!mc) continue;
        for (const side of ['home', 'away']) {
          const team = mc[`${side}_team_hash_id`] || f[`${side}_team_hash_id`];
          const key = `${f.match_hash_id}:${side}`;
          if (team && !st.members[key]) todo.push({ key, mid: f.match_hash_id, team });
        }
      }
      await batched(todo, async (t) => {
        const body = await get(`matchcentre-match-members/match/${t.mid}/team/${t.team}`);
        st.members[t.key] = list(body).map(p => { const q = { ...p }; delete q.image; return q; });
      });
      return Object.keys(st.members).length;
    },
    async ladders() {
      for (const lg of st.leagues) {
        try {
          const body = await get(`ladders?league=${lg.league_id}&require_pools=true&include_match_type=true`);
          st.ladders[lg.league_id] = list(body).map(attrs);
        } catch (e) { st.errors.push({ item: lg, error: String(e) }); }
      }
      return Object.keys(st.ladders).length;
    },
    // The full dump is ~50 MB; the JS tool saves big results to a file, but split it to stay safe.
    //   __v2.dump('meta')      -> leagues, fixtures, ladders, errors
    //   __v2.dump('mc')        -> match centre records
    //   __v2.dump('members', i, n) -> i-th of n slices of the lineups
    dump(part = 'all', i = 0, n = 1) {
      const head = { extracted_at: new Date().toISOString(), tenant: TENANT, season: SEASON, part };
      if (part === 'meta') return JSON.stringify({ ...head, leagues: st.leagues, fixtures: st.fixtures, ladders: st.ladders, errors: st.errors });
      if (part === 'mc') return JSON.stringify({ ...head, mc: st.mc });
      if (part === 'members') {
        const keys = Object.keys(st.members).sort();
        const size = Math.ceil(keys.length / n);
        const slice = Object.fromEntries(keys.slice(i * size, (i + 1) * size).map(k => [k, st.members[k]]));
        return JSON.stringify({ ...head, slice: i, of: n, members: slice });
      }
      return JSON.stringify({ ...head, ...st });
    },
  };
  window.__v2 = api;
  return 'ready';
})();
