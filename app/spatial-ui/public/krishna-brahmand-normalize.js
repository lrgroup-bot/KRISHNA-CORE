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
})();
