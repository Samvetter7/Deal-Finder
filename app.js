fetch("data.json?t=" + Date.now())
  .then(r => r.ok ? r.json() : Promise.reject("No data.json yet"))
  .then(D => startApp(D))
  .catch(() => {
    startApp({
      updated: new Date().toISOString(),
      deals: new Array(),
      rejected: new Array(),
      sweeps: new Array(),
      styles: [
        {slug:"tory-burch-lee-radziwill",brand:"Tory Burch",name:"Lee Radziwill bag",conservative:295,sold90:85,sell_through:0.41,max_all_in:50,cls:"Promising"},
        {slug:"filson-mackinaw-cruiser",brand:"Filson",name:"Mackinaw Cruiser",conservative:247.49,sold90:110,sell_through:0.43,max_all_in:50,cls:"Promising"},
        {slug:"burberry-quilted-jacket",brand:"Burberry",name:"Quilted trench / jacket",conservative:200,sold90:190,sell_through:0.38,max_all_in:50,cls:"Promising"},
        {slug:"sezane-clyde-trench",brand:"Sézane",name:"Clyde trench",conservative:195,sold90:65,sell_through:0.56,max_all_in:50,cls:"Hot"},
        {slug:"coach-tabby-bag",brand:"Coach",name:"Tabby bag",conservative:192,sold90:420,sell_through:0.41,max_all_in:50,cls:"Promising"},
        {slug:"burberry-vintage-wool-trench",brand:"Burberry",name:"Vintage wool trench",conservative:175,sold90:95,sell_through:0.35,max_all_in:50,cls:"Promising"},
        {slug:"burberry-trench-coat",brand:"Burberry",name:"Trench coat",conservative:170,sold90:340,sell_through:0.22,max_all_in:50,cls:"Promising"},
        {slug:"arcteryx-beta-jacket",brand:"Arc'teryx",name:"Beta jacket",conservative:160,sold90:280,sell_through:0.45,max_all_in:50,cls:"Promising"},
        {slug:"carhartt-detroit-jacket",brand:"Carhartt",name:"Detroit jacket (vintage)",conservative:160,sold90:2634,sell_through:0.36,max_all_in:50,cls:"Promising"},
        {slug:"barbour-waxed-jacket",brand:"Barbour",name:"Waxed jacket (Bedale/Beaufort)",conservative:155,sold90:310,sell_through:0.42,max_all_in:50,cls:"Promising"},
        {slug:"mackage-wool-coat",brand:"Mackage",name:"Wool or down coat",conservative:155,sold90:140,sell_through:0.39,max_all_in:50,cls:"Promising"},
        {slug:"polo-bear-sweater",brand:"Polo Ralph Lauren",name:"Polo Bear knit sweater",conservative:150,sold90:260,sell_through:0.41,max_all_in:50,cls:"Promising"},
        {slug:"aritzia-super-puff",brand:"Aritzia",name:"Super Puff jacket",conservative:145,sold90:390,sell_through:0.49,max_all_in:50,cls:"Promising"},
        {slug:"arcteryx-atom-jacket",brand:"Arc'teryx",name:"Atom jacket / hoody",conservative:140,sold90:410,sell_through:0.48,max_all_in:50,cls:"Promising"},
        {slug:"north-face-nuptse",brand:"The North Face",name:"1996 Retro Nuptse jacket",conservative:138,sold90:520,sell_through:0.43,max_all_in:50,cls:"Promising"},
        {slug:"doen-dress",brand:"Dôen",name:"Mainline dress",conservative:135,sold90:210,sell_through:0.47,max_all_in:50,cls:"Promising"}
      ]
    });
  });

function startApp(D) {
  const app = document.getElementById("app");
  const esc = s => String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  const money = v => typeof v === "number" ? "$" + v.toFixed(2) : "—";
  const pct = v => typeof v === "number" ? Math.round(v * 100) + "%" : "—";
  const ago = iso => {
    const m = Math.round((Date.now() - new Date(iso)) / 60000);
    if (isNaN(m)) return "";
    if (m < 1) return "just now";
    if (m < 60) return m + " min ago";
    if (m < 2880) return Math.round(m / 60) + " h ago";
    return Math.round(m / 1440) + " d ago";
  };
  const styles = D.styles || new Array();
  const styleBy = {};
  styles.forEach(s => { styleBy[s.slug] = s; });
  let marks = {};
  try { marks = JSON.parse(localStorage.getItem("df-marks") || "{}"); } catch (e) {}
  const saveMarks = () => { try { localStorage.setItem("df-marks", JSON.stringify(marks)); } catch (e) {} };
  let view = "deals";
  document.getElementById("last").textContent = "Last sweep " + ago(D.updated);

  function card(d) {
    const st = styleBy[d.style] || {};
    const m = marks[d.id];
    const imgHtml = d.img ? '<a class="ph" href="' + esc(d.url) + '" target="_blank"><img src="' + d.img + '" alt=""></a>' : "";
    const reasonsHtml = (d.reasons || new Array()).map(r => '<div class="muted">✓ ' + esc(r) + '</div>').join("");
    const flagsHtml = (d.flags || new Array()).map(f => '<div class="flag">⚠ ' + esc(f) + '</div>').join("");
    return '<div class="card deal">' + imgHtml + '<div style="flex:1">' +
      '<div><span class="pill ' + d.decision + '">' + d.decision + '</span> <span class="muted">' + esc(d.marketplace) + ' · found ' + ago(d.found) + '</span>' + (m ? ' <span class="muted">· ' + m + '</span>' : '') + '</div>' +
      '<div class="t"><a href="' + esc(d.url) + '" target="_blank">' + esc(d.title) + '</a></div>' +
      (st.brand ? '<div class="muted">' + esc(st.brand) + ' — ' + esc(st.name) + '</div>' : '') +
      '<div class="nums"><span>All-in <b>' + money(d.total) + '</b></span><span>Est. resale <b>' + money(d.resale) + '</b></span><span class="profit">Net profit <b>+' + money(d.net_profit) + '</b></span></div>' +
      reasonsHtml + flagsHtml +
      '<div class="actions"><a class="btn primary" href="' + esc(d.url) + '" target="_blank">Open listing</a>' +
      '<button class="btn" data-id="' + esc(d.id) + '" data-m="saved">Save</button>' +
      '<button class="btn" data-id="' + esc(d.id) + '" data-m="bought">Bought</button>' +
      '<button class="btn" data-id="' + esc(d.id) + '" data-m="passed">Pass</button></div></div></div>';
  }

  function render() {
    const deals = D.deals || new Array();
    const rejected = D.rejected || new Array();
    const sweeps = D.sweeps || new Array();
    const active = deals.filter(d => marks[d.id] !== "passed" && marks[d.id] !== "bought");
    const alerts = active.filter(d => d.decision === "ALERT");
    const offers = active.filter(d => d.decision === "OFFER" || d.decision === "REVIEW");
    const lastSweep = sweeps.length ? sweeps.slice(0, 1).pop() : {};

    if (view === "deals") {
      app.innerHTML = '<h1>Top deals right now</h1><p class="lead">Every rule passed: &le; $50 all-in, &ge; $40 conservative profit, verified style, and every photo checked.</p>' +
        '<div class="kpis"><div class="card kpi"><div class="muted">Buy alerts</div><div class="big profit">' + alerts.length + '</div></div>' +
        '<div class="card kpi"><div class="muted">Offer / Review</div><div class="big">' + offers.length + '</div></div>' +
        '<div class="card kpi"><div class="muted">Pages read last sweep</div><div class="big">' + (lastSweep.pages || 0) + '</div></div>' +
        '<div class="card kpi"><div class="muted">Profitable styles</div><div class="big">' + styles.length + '</div></div></div>' +
        (lastSweep.notes ? '<div class="card muted">' + esc(lastSweep.notes) + '</div>' : '') +
        (alerts.length ? '<div class="grid">' + alerts.map(card).join("") + '</div>' : '') +
        '<h2>Listings checked that did not pass</h2><div class="grid">' +
        rejected.slice(0, 12).map(r => '<div class="card"><span class="pill REJECT">NOT RECOMMENDED</span> <span class="muted">' + esc(r.marketplace) + '</span><div class="t" style="margin-top:4px">' + esc(r.title) + '</div><div class="flag">' + esc(r.why) + '</div><div class="actions"><a class="btn primary" href="' + esc(r.url) + '" target="_blank">Open listing</a></div></div>').join("") + '</div>';
    } else if (view === "offer") {
      app.innerHTML = '<h1>Make an offer &amp; Review</h1><div class="grid">' + (offers.length ? offers.map(card).join("") : '<p class="muted">No offer opportunities right now.</p>') + '</div>';
    } else if (view === "saved") {
      const saved = deals.filter(d => marks[d.id] === "saved" || marks[d.id] === "bought");
      app.innerHTML = '<h1>Saved &amp; Bought</h1><div class="grid">' + (saved.length ? saved.map(card).join("") : '<p class="muted">Nothing saved yet.</p>') + '</div>';
    } else if (view === "rejected") {
      app.innerHTML = '<h1>Rejected listings (' + rejected.length + ')</h1><div class="grid">' + rejected.map(r => '<div class="card"><span class="pill REJECT">REJECTED</span> <span class="muted">' + esc(r.marketplace) + '</span><div class="t" style="margin-top:4px">' + esc(r.title) + '</div><div class="flag">' + esc(r.why) + '</div><div class="actions"><a class="btn" href="' + esc(r.url) + '" target="_blank">Open</a></div></div>').join("") + '</div>';
    } else if (view === "styles") {
      app.innerHTML = '<h1>Tracked styles (' + styles.length + ')</h1><div class="tablewrap"><table><thead><tr><th>Brand &amp; Style</th><th>Class</th><th class="r">Conservative</th><th class="r">90d Sold</th><th class="r">Sell-through</th><th class="r">Max All-In</th></tr></thead><tbody>' + styles.map(s => '<tr><td><b>' + esc(s.brand) + '</b> — ' + esc(s.name) + '</td><td><span class="pill ' + s.cls + '">' + s.cls + '</span></td><td class="r">' + money(s.conservative) + '</td><td class="r">' + s.sold90 + '</td><td class="r">' + pct(s.sell_through) + '</td><td class="r">' + money(s.max_all_in) + '</td></tr>').join("") + '</tbody></table></div>';
    } else if (view === "sweeps") {
      app.innerHTML = '<h1>Sweep history</h1><div class="tablewrap"><table><thead><tr><th>Time</th><th>Sites</th><th>Searched</th><th class="r">Checked</th><th class="r">Alerts</th><th>Notes</th></tr></thead><tbody>' + sweeps.map(w => '<tr><td>' + ago(w.at) + '</td><td>' + (w.sites || new Array()).join(", ") + '</td><td>' + (w.searched || new Array()).join(", ") + '</td><td class="r">' + w.candidates + '</td><td class="r">' + w.alerts + '</td><td>' + esc(w.notes) + '</td></tr>').join("") + '</tbody></table></div>';
    }
  }

  document.getElementById("tabs").addEventListener("click", e => {
    if (e.target.dataset.v) {
      view = e.target.dataset.v;
      document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("on", b === e.target));
      render();
    }
  });

  app.addEventListener("click", e => {
    if (e.target.dataset.id && e.target.dataset.m) {
marks[e.target.dataset.id] = e.target.dataset.m;
saveMarks();
render();
}
});
render();
}
