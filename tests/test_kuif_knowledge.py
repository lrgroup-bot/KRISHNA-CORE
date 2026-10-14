from kuif.knowledge import KnowledgeStore

def test_project_separation(tmp_path):
    store = KnowledgeStore(str(tmp_path / "memory.db"))
    store.put("krishna", "a", "secret apple")
    store.put("kuber", "b", "public apple")
    assert store.search("krishna", "apple") == [("a", "secret apple")]
    assert store.search("kuber", "secret") == []
