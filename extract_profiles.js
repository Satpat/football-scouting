// DRIBL member-profile extraction — run inside the browser pane on https://fsa.dribl.com
// after the match extraction. Gives age, nationality, headshot, club colours, per-season
// career rows and every match this season (including cups/trials).
//
//   window.__p.ids = [...player ids...];       // unique user_hash_id values from players.csv
//   await __p.profiles(); await __p.careers(); await __p.matches();
//   __p.dump('profiles'); __p.dump('careers'); __p.dump('matches', 0, 3); ...
// Then: python merge_dumps.py <dump files> -o output/dribl_profiles_2026.json

(() => {
  const B = 'https://mc-api.dribl.com/api/';
  const TENANT = '3pmvvjLmvJ';
  const SEASON = '7MNGzMbmAz';
  const BATCH = 15;
  const st = (window.__p && window.__p.state) || { profiles: {}, careers: {}, member_matches: {}, errors: [] };

  async function get(path) {
    const r = await fetch(B + path);
    if (!r.ok) throw new Error(`${r.status} ${path}`);
    return r.json();
  }
  const attrs = (rec) => (rec && rec.attributes) ? { hash_id: rec.hash_id || rec.id, ...rec.attributes } : rec;
  const list = (body) => Array.isArray(body) ? body : (Array.isArray(body.data) ? body.data : Object.values(body.data || {}));

  async function batched(items, fn) {
    for (let i = 0; i < items.length; i += BATCH) {
      await Promise.all(items.slice(i, i + BATCH).map(async (it) => {
        try { await fn(it); } catch (e) { st.errors.push({ item: it, error: String(e) }); }
      }));
    }
  }

  const api = {
    state: st,
    ids: (window.__p && window.__p.ids) || [],
    async profiles() {
      await batched(api.ids.filter((id) => !st.profiles[id]), async (id) => {
        st.profiles[id] = attrs((await get(`memberprofile/${id}?tenant=${TENANT}&season=${SEASON}`)).data);
      });
      return Object.keys(st.profiles).length;
    },
    async careers() {
      await batched(api.ids.filter((id) => !st.careers[id]), async (id) => {
        st.careers[id] = list(await get(`memberprofile-careers/member/${id}/tenant/${TENANT}?member=${id}&season=${SEASON}`)).map(attrs);
      });
      return Object.keys(st.careers).length;
    },
    async matches() {
      await batched(api.ids.filter((id) => !st.member_matches[id]), async (id) => {
        st.member_matches[id] = list(await get(`memberprofile-matches/member/${id}?member=${id}&tenant=${TENANT}&date_range=default&m=${id}&season=${SEASON}`)).map(attrs);
      });
      return Object.keys(st.member_matches).length;
    },
    dump(part = 'profiles', i = 0, n = 1) {
      const head = { extracted_at: new Date().toISOString(), tenant: TENANT, season: SEASON, part };
      const key = part === 'matches' ? 'member_matches' : part;
      const keys = Object.keys(st[key]).sort();
      const size = Math.ceil(keys.length / n);
      const slice = Object.fromEntries(keys.slice(i * size, (i + 1) * size).map((k) => [k, st[key][k]]));
      return JSON.stringify({ ...head, slice: i, of: n, [key]: slice, errors: i === 0 ? st.errors : [] });
    },
  };
  window.__p = api;
  return 'ready';
})();
