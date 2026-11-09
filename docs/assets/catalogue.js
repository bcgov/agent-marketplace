/* Static Catalogue public renderer. Contributed content is always inert text. */
(function (root) {
  'use strict';

  function filterCatalog(catalog, filters = {}, now = new Date()) {
    const query = String(filters.query || '').trim().toLowerCase();
    const clock = new Date(now).getTime();
    return (catalog.extensions || []).filter((record) => {
      const haystack = [record['display-name'], record.summary, record.id,
        ...(record['legacy-ids'] || []), ...(record.maintainers || [])].join(' ').toLowerCase();
      if (query ? !haystack.includes(query) : record.lifecycle !== 'active') return false;
      if (filters.type && record.type !== filters.type) return false;
      if (filters.specialty && record.specialty !== filters.specialty) return false;
      if (filters.added) {
        const added = record.source?.added ? Date.parse(record.source.added) : NaN;
        if (!Number.isFinite(added) || added > clock || added < clock - 7 * 86400000) return false;
      }
      return true;
    });
  }

  const escape = (value) => String(value ?? '').replace(/[&<>"']/g,
    (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const anchor = (id) => '#' + encodeURIComponent(id);
  const navigate = (record) => `<a class="replacement-link" href="${anchor(record.id)}">View ${escape(record['display-name'] || record.id)}</a>`;
  const types = {skill: 'Skill', instructions: 'Instructions', prompt: 'Prompt', agent: 'Agent'};
  const safeUrl = (value) => /^https?:\/\//.test(value || '') ? escape(value) : '';
  const sourceUrl = (source) => source && /^[a-f0-9]{40}$/.test(source.revision || '') && safeUrl(source.repository) && source.path
    ? safeUrl(source.repository.replace(/\/$/, '') + '/tree/' + source.revision + '/' + source.path.split('/').map(encodeURIComponent).join('/')) : '';
  const date = (value) => value && Number.isFinite(Date.parse(value))
    ? `<time datetime="${escape(value)}" title="${escape(value)}">${new Date(value).toISOString().slice(0, 10)} UTC</time>` : 'Not recorded';
  const pair = (label, value) => `<div><dt>${label}</dt><dd>${value}</dd></div>`;

  function installDetail(catalog, record, allowed) {
    const choices = allowed ? (record['install-options'] || []).filter((choice) =>
      choice['extension-id'] === record.id && ['repository', 'revision', 'path'].every((key) => choice.source?.[key] === record.source?.[key])) : [];
    if (!choices.length) return '<p class="install-note">No tested install choice is available for this record.</p>';
    const label = catalog.version === 'source' || catalog['release-state'] !== 'published'
      ? 'Catalogue source (source preview)' : 'Catalogue snapshot source';
    return `<h4>Tested manual install choices</h4><p>Choose a scope, inspect destinations for collisions, then place files explicitly. Opening a choice or navigating to source never installs content.</p>` + choices.map((choice) => `
      <details class="native-install-choice">
        <summary>Manual install · ${escape(choice.client)} · ${escape(choice.scope)}</summary>
        <p>Rooted at <strong>${escape(choice['destination-root'])}</strong>.</p>
        <p><strong>${label}</strong>: <a href="${sourceUrl(choice.source)}">Read selected native source</a> at <code>${escape(choice.source.revision)}</code>.</p>
        ${safeUrl(choice['latest-source']?.url) ? `<p><a href="${safeUrl(choice['latest-source'].url)}">Latest source (main)</a> may differ from this Catalogue snapshot.</p>` : ''}
        <p>${escape(choice.install)}</p>
        <pre><code>${escape((choice.placements || []).map((item) => `${item.source} -> ${item.destination}\nSHA-256: ${item.sha256}`).join('\n\n'))}</code></pre>
        <p><strong>Update:</strong> ${escape(choice.update)}</p><p><strong>Remove:</strong> ${escape(choice.remove)}</p>
        <p>${escape(choice.integrity)}</p>
        <p>Layout evidence: ${escape(choice.evidence?.tested || 'Not recorded')}. This is not a runtime compatibility test of this Extension.</p>
      </details>`).join('');
  }

  function resolveExtension(catalog, requested) {
    const alias = Object.hasOwn(catalog['legacy-ids'] || {}, requested) ? requested : null;
    const id = alias ? catalog['legacy-ids'][alias] : requested;
    const byId = new Map((catalog.extensions || []).map((record) => [record.id, record]));
    const chain = [];
    let current = byId.get(id);
    if (!current) return {error: 'Extension not found', chain};
    while (current) {
      if (chain.some((record) => record.id === current.id)) return {error: 'Replacement cycle; installation unavailable', chain};
      chain.push(current);
      if (!current['moved-to']) break;
      current = byId.get(current['moved-to']);
      if (!current) return {error: 'Replacement not recorded; installation unavailable', chain};
    }
    return {requested, alias, chain, terminal: chain[chain.length - 1]};
  }

  function renderDetail(catalog, requested) {
    const resolved = resolveExtension(catalog, requested);
    if (resolved.error) return `<h3 tabindex="-1">Extension unavailable</h3><p role="status">${escape(resolved.error)}</p>`;
    const record = resolved.chain[0];
    const alias = resolved.alias ? `<p class="lifecycle-notice"><strong>Legacy ID:</strong> <code>${escape(requested)}</code> resolves to <code>${escape(record.id)}</code>. Choose the canonical record explicitly before installation. ${navigate(record)}</p>` : '';
    const notices = resolved.chain.map((item) => item.lifecycle !== 'active' || item['moved-to']
      ? `<li><strong>${escape(item.id)} · ${escape(item.lifecycle)}</strong><p>${escape(item.notice || 'This Extension is unavailable.')}</p></li>` : '').join('');
    const chain = notices ? `<div class="lifecycle-notice" role="status"><h4>Lifecycle notices</h4><ol>${notices}</ol></div>` : '';
    const replacement = resolved.chain.length > 1 ? `<div class="replacement-guidance"><p>Choose a replacement explicitly. Review its identity, source path and notices before any manual migration; navigation never installs content.</p><ol>${resolved.chain.slice(1).map((item) => `<li>${navigate(item)} · ${escape(item.lifecycle)}</li>`).join('')}</ol>${resolved.terminal.lifecycle !== 'active' ? `<p><strong>Terminal replacement is ${escape(resolved.terminal.lifecycle)} and unavailable.</strong></p>` : ''}</div>` : '';
    const heading = `<h3 tabindex="-1">${escape(record['display-name'])}</h3><p class="detail-identity"><code>${escape(record.id)}</code></p>`;
    if (record.lifecycle === 'removed') return heading + alias + chain + replacement + '<p>This removed record is retained as a tombstone. Installation and source access are unavailable.</p>';
    const source = record.source || {};
    const checks = record.checks || {};
    const specialty = (catalog.specialties || []).find((item) => item.id === record.specialty);
    const route = record['policy-route'] || {};
    const access = record.capabilities || {};
    const matches = !!record['content-digest'] && checks['content-digest'] === record['content-digest'];
    const accessRows = [['Commands', access.commands], ['Network', access.network],
      ['Read paths', access.filesystem?.read], ['Write paths', access.filesystem?.write],
      ['Environment variables', access['environment-variables']], ['Secret names', access['secret-names']],
      ['Data classes', access['data-classes']]].map(([label, values]) => pair(label, escape((values || []).join(', ') || 'None declared'))).join('');
    const routeText = route.type === 'community' ? 'Community rules apply.'
      : route.type === 'specialty-review' ? `${specialty?.['review-rule'] || 'Specialty owner review'} · ${route['owner-team'] || specialty?.['owner-team'] || 'Owner not recorded'}` : 'Not recorded';
    const exclusions = record.compatibility?.['not-ready-on'] || [];
    const url = sourceUrl(source);
    return heading + alias + chain + replacement + `
      <p>${escape(record.summary)}</p>
      <p class="detail-category"><span class="specialty-flair">${escape(specialty?.['display-flair'] || specialty?.['display-name'] || (record.specialty === 'community' ? 'Community' : record.specialty))}</span> · ${escape(types[record.type] || record.type)}</p>
      ${installDetail(catalog, record, matches && checks.outcome === 'passed' && record.lifecycle === 'active' && !record['moved-to'] && !resolved.alias)}
      ${record.lifecycle === 'quarantined' ? '<p class="lifecycle-notice">Source may contain withdrawn guidance. Inspect it with care; installation is unavailable.</p>' : ''}
      <dl>${pair('Source added', date(source.added))}${pair('Source updated', date(source.updated))}</dl>
      <p class="detail-note">Dates describe source history, not first publication.</p>
      <h4>Automated checks</h4>
      <p>${matches && checks.outcome === 'passed' ? '<strong>Auto-checked.</strong> These exact package bytes passed automated format and policy checks.' : matches ? 'Recorded check outcome: ' + escape(checks.outcome || 'Not recorded') : '<strong>Evidence does not match this package digest or is not recorded.</strong>'} Automated checks are not a safety or runtime compatibility certification.</p>
      <dl>${pair('Package digest', `<code>${escape(record['content-digest'] || 'Not recorded')}</code>`)}
        ${pair('Checked digest', `<code>${escape(checks['content-digest'] || 'Not recorded')}</code>`)}
        ${pair('Policy version', escape(checks['policy-version'] ?? catalog['policy-version'] ?? 'Not recorded'))}
        ${pair('Engine identity', `<code>${escape(catalog.engine || 'Not recorded')}</code>`)}
        ${pair('Advisories', escape(checks.advisories ?? (checks.findings ? checks.findings.filter((item) => item.severity === 'advisory').length : 'Not recorded')))}</dl>
      <p><a href="assets/catalog.json">Recorded automated evidence in this Catalogue asset</a></p>
      <h4>Review rule</h4><p>${escape(routeText)}</p>
      <p>This route describes the review rule, not proof of a named review of this revision.</p>
      <p>Named reviewer evidence: ${escape(matches && checks.reviewers?.length ? checks.reviewers.join(', ') : 'Not recorded')}</p>
      <h4>Declared access</h4><dl>${accessRows}</dl>
      <p>Declared access is not runtime confinement.</p>
      <h4>Author-declared harness readiness</h4>
      <p>${exclusions.length ? 'Not ready on: ' + escape(exclusions.join(', ')) + '.' : 'No harness exclusions declared.'} This is not a runtime compatibility test.</p>
      <h4>Source and contacts</h4>
      <dl>${pair('Maintainers', escape((record.maintainers || []).join(', ') || 'Not recorded'))}
        ${pair('Repository', escape(source.repository || 'Not recorded'))}${pair('Source path', `<code>${escape(source.path || 'Not recorded')}</code>`)}
        ${pair('Source revision', `<code>${escape(source.revision || 'Not recorded')}</code>`)}
        ${pair('License', escape(record.license || 'Not recorded'))}
        ${pair('Prerequisites', escape((record.prerequisites || []).join('; ') || 'None declared'))}</dl>
      ${url ? `<p><a href="${url}">${record.lifecycle === 'quarantined' ? 'Inspect quarantined source at this revision (warning)' : 'Read exact source at this revision'}</a></p>` : ''}
      ${safeUrl(record.support) ? `<p><a href="${safeUrl(record.support)}">Contact maintainers for support</a></p>` : ''}
    `;
  }

  function mount(catalog) {
    const list = document.getElementById('published-skills');
    const panel = document.getElementById('catalog-detail');
    const placeholder = panel.innerHTML;
    const search = document.getElementById('catalog-search');
    const type = document.getElementById('catalog-type');
    const specialty = document.getElementById('catalog-specialty');
    const added = document.getElementById('catalog-added');
    const reset = document.getElementById('catalog-reset');
    const empty = document.getElementById('catalog-empty');
    const count = document.getElementById('catalog-count');
    const rows = new Map(Array.from(list.querySelectorAll('.cat-row')).map((row) => [row.dataset.extensionId, row]));
    let selected = '';
    specialty.innerHTML = '<option value="">All Specialties</option><option value="community">Community</option>' + (catalog.specialties || []).map((item) => `<option value="${escape(item.id)}">${escape(item['display-name'])}</option>`).join('');

    function apply() {
      const visible = new Set(filterCatalog(catalog, {query: search.value, type: type.value, specialty: specialty.value, added: added.checked}).map((record) => record.id));
      rows.forEach((row, id) => {
        row.hidden = !visible.has(id);
        row.classList.toggle('is-selected', selected === id);
        row.querySelector('.cat-row-open').setAttribute('aria-expanded', String(selected === id));
      });
      empty.hidden = visible.size !== 0;
      count.textContent = `${visible.size} ${visible.size === 1 ? 'Extension' : 'Extensions'}${search.value.trim() ? ' match your search' : ' active'}${added.checked ? ' · added in the past seven days' : ''}`;
    }

    function open(id, focus) {
      const result = resolveExtension(catalog, id);
      selected = result.chain[0]?.id || '';
      panel.innerHTML = renderDetail(catalog, id);
      apply();
      if (root.enhanceCodeBlocks) root.enhanceCodeBlocks(panel);
      if (focus) panel.querySelector('h3')?.focus({preventScroll: true});
      if (focus && root.matchMedia('(max-width: 900px)').matches) panel.scrollIntoView({block: 'start'});
    }

    function fromHash(focus) {
      if (!root.location.hash) {
        selected = '';
        panel.innerHTML = placeholder;
        apply();
        return;
      }
      try { open(decodeURIComponent(root.location.hash.slice(1)), focus); }
      catch { panel.innerHTML = '<h3 tabindex="-1">Extension unavailable</h3><p>Invalid Extension link.</p>'; }
    }

    list.addEventListener('click', (event) => {
      const button = event.target.closest('.cat-row-open');
      if (!button) return;
      const id = button.closest('.cat-row').dataset.extensionId;
      root.history.pushState(null, '', anchor(id));
      open(id, true);
    });
    panel.addEventListener('click', (event) => {
      const link = event.target.closest('.replacement-link');
      if (!link) return;
      event.preventDefault();
      root.history.pushState(null, '', link.getAttribute('href'));
      fromHash(true);
    });
    root.addEventListener('hashchange', () => fromHash(false));
    root.addEventListener('popstate', () => fromHash(false));
    search.addEventListener('input', apply);
    [type, specialty, added].forEach((input) => input.addEventListener('change', apply));
    reset.addEventListener('click', () => {
      search.value = type.value = specialty.value = '';
      added.checked = false;
      apply();
      search.focus();
    });
    document.getElementById('catalog-rail').addEventListener('submit', (event) => event.preventDefault());
    rows.forEach((row) => row.querySelector('.cat-row-open').setAttribute('aria-controls', 'catalog-detail'));
    apply();
    fromHash(false);
  }

  const api = {filterCatalog, resolveExtension, renderDetail, mount};
  if (typeof module !== 'undefined') module.exports = api;
  root.Catalogue = api;
  if (typeof document !== 'undefined' && document.getElementById('catalog-rail')) {
    fetch('assets/catalog.json').then((response) => {
      if (!response.ok) throw new Error('Catalogue unavailable');
      return response.json();
    }).then(mount).catch(() => {
      document.getElementById('catalog-load-error').hidden = false;
      document.querySelectorAll('#catalog-rail input, #catalog-rail select, #catalog-reset, .cat-row-open').forEach((input) => { input.disabled = true; });
    });
  }
})(typeof window === 'undefined' ? globalThis : window);
