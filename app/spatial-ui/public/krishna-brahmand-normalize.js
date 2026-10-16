(() => {
  const data = window.KRISHNA_BRAHMAND_DATA;
  if (!data || !data.nodes) return;
  Object.entries(data.nodes).forEach(([id, def]) => {
    if (!def || typeof def !== 'object') return;
    if (!def.id) def.id = id;
    if (!Array.isArray(def.aliases)) def.aliases = [id];
    if (Array.isArray(def.children)) {
      def.children = def.children.filter((child) => Boolean(data.nodes[child]));
    }
  });
  if (Array.isArray(data.root)) {
    data.root = data.root.filter((id) => Boolean(data.nodes[id]));
  }

  const words = value => String(value ?? '').toLowerCase().replace(/[_\-/]+/g, ' ').replace(/\s+/g, ' ').trim();
  const flatten = value => Array.isArray(value) ? value.flatMap(flatten) :
    typeof value === 'string' ? [value] : value && typeof value === 'object' ?
      [value.id, value.name, value.specialist, value.agent].filter(v => typeof v === 'string') : [];
  const owners = task => {
    const fields = ['assigned_specialist','assignedSpecialist','specialist','specialists','agent','owner','worker','assignee','capability'];
    return [...new Set([task, task?.detail].flatMap(part => fields.flatMap(key => flatten(part?.[key]))).map(words))];
  };
  const matches = (def, task) => (def?.id === 'specialists' &&
    [task?.specialists, task?.detail?.specialists].some(value => Array.isArray(value) && value.length > 0)) || owners(task).some(owner => (def?.aliases || []).some(alias => {
    const term = words(alias);
    return term && (` ${owner} `).includes(` ${term} `);
  }));
  const descendants = (id, seen = new Set()) => {
    if (seen.has(id) || !data.nodes[id]) return [];
    seen.add(id);
    return [id, ...(data.nodes[id].children || []).flatMap(child => descendants(child, seen))];
  };
  const tasksFor = (id, tasks) => {
    const defs = descendants(id).map(key => data.nodes[key]);
    return tasks.filter(task => id === 'krishna' || defs.some(def => matches(def, task)));
  };
  const status = task => words(task?.status).replaceAll(' ', '_');
  const verification = task => {
    const detail = task?.detail || {};
    const candidates = [task?.verification, task?.verification_evidence, task?.test_results, detail.verification, detail.promotion?.verification];
    return candidates.find(value => value && typeof value === 'object' &&
      (value.verified === true || value.passed === true || (typeof value.passed === 'number' && value.passed > 0 && value.failed === 0))) || null;
  };
  window.KRISHNA_BRAHMAND_NORMALIZE = { words, owners, matches, descendants, tasksFor, status, verification };
})();
