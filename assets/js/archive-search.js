// Search on the Blog page. Loads the search index the first time someone
// types, then shows matching posts in place of the date groups.
(function () {
  var input = document.getElementById('archive-search-input');
  if (!input) return;
  var status = document.querySelector('.archive-search-status');
  var results = document.querySelector('.archive-results');
  var groups = document.querySelector('.archive-groups');
  var rows = {};
  document.querySelectorAll('.archive-groups .archive-row').forEach(function (li) {
    var a = li.querySelector('a');
    if (a) rows[a.getAttribute('href')] = li;
  });
  var index = null, loading = null, timer = null;

  function norm(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function load() {
    if (!loading) {
      loading = fetch(input.getAttribute('data-index'))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          index = data.map(function (e) {
            return {
              u: e.u,
              title: ' ' + norm(e.t) + ' ',
              meta: ' ' + norm((e.c || '') + ' ' + (e.g || '')) + ' ',
              body: ' ' + norm(e.x) + ' ',
              text: e.x || ''
            };
          });
        });
    }
    return loading;
  }

  function snippet(text, words) {
    var lower = text.toLowerCase(), pos = -1;
    for (var i = 0; i < words.length && pos < 0; i++) pos = lower.indexOf(words[i]);
    if (pos < 0) return null;
    var start = Math.max(0, pos - 60);
    return (start > 0 ? '…' : '') + text.slice(start, pos + 140).replace(/\s+/g, ' ').trim() + '…';
  }

  function fullDate(li) {
    var t = li.querySelector('time');
    if (!t) return;
    var d = new Date(t.getAttribute('datetime') + 'T12:00:00Z');
    if (!isNaN(d)) t.textContent = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  }

  function keepInUrl(q) {
    try {
      var url = new URL(window.location.href);
      if (q) url.searchParams.set('q', q); else url.searchParams.delete('q');
      window.history.replaceState(null, '', url);
    } catch (e) { /* not important */ }
  }

  function search(index, words) {
    var hits = [];
    index.forEach(function (e, i) {
      var score = 0;
      for (var k = 0; k < words.length; k++) {
        var w = words[k], s = 0;
        if (e.title.indexOf(w) >= 0) s += 6;
        if (e.meta.indexOf(w) >= 0) s += 4;
        if (e.body.indexOf(w) >= 0) s += 1;
        if (!s) return;          // every word has to appear somewhere
        score += s;
      }
      hits.push({ e: e, score: score, i: i });
    });
    hits.sort(function (a, b) { return b.score - a.score || a.i - b.i; });
    return hits;
  }

  function run() {
    var q = input.value.trim();
    var words = norm(q).split(' ').filter(function (w) { return w.length > 1; });
    keepInUrl(q);
    if (!words.length) {
      results.hidden = true; results.innerHTML = ''; groups.hidden = false; status.textContent = '';
      return;
    }
    status.textContent = 'Searching…';
    load().then(function () {
      if (input.value.trim() !== q) return;   // a newer search is on its way
      var hits = search(index, words);
      results.innerHTML = '';
      hits.slice(0, 100).forEach(function (h) {
        var row = rows[h.e.u];
        if (!row) return;
        var li = row.cloneNode(true);
        fullDate(li);
        if (h.e.title.indexOf(' ' + words[0]) < 0) {
          var snip = snippet(h.e.text, words), el = li.querySelector('.archive-snippet');
          if (snip && el) el.textContent = snip;
        }
        results.appendChild(li);
      });
      groups.hidden = true;
      results.hidden = false;
      status.textContent = hits.length === 0 ? 'Nothing found.'
        : hits.length + (hits.length === 1 ? ' post' : ' posts') + (hits.length > 100 ? ', showing the first 100' : '');
    }).catch(function () { status.textContent = 'Search isn’t available right now.'; });
  }

  input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 150); });
  input.addEventListener('focus', function () { load().catch(function () {}); }, { once: true });
  var initial = new URLSearchParams(window.location.search).get('q');
  if (initial) { input.value = initial; run(); }

})();
