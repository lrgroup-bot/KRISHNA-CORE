/* Read-only local book-ledger overview. Never sends source text to the browser. */
"use strict";
(function () {
  const target = document.getElementById("book-ledger-list");
  const state = document.getElementById("book-ledger-state");
  if (!target || !state) return;
  function node(tag, text, cls) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = String(text);
    return el;
  }
  function sessionCard(book, mode, reading) {
    const card = node("article", undefined, "book-session");
    card.append(node("h3", book.title || "Untitled book"));
    card.append(node("div", mode, "book-method"));
    const counts = node("div", undefined, "book-progress-count");
    counts.append(node("strong", reading.lines_processed + " / " +
                    reading.lines_total + " lines"));
    counts.append(node("span", (reading.progress_percent || 0) + "%"));
    card.append(counts);
    const track = node("div", undefined, "book-progress-track");
    const fill = node("div", undefined, "book-progress-fill");
    fill.style.width = Math.min(100, Math.max(0,
        Number(reading.progress_percent) || 0)) + "%";
    track.append(fill);
    card.append(track);
    card.append(node("p", (reading.reached_end ? "Text pass reached final line" :
        "Next unread source line: " + (reading.lines_processed + 1)) +
        " · " + (reading.model_steps_completed || 0) + " journal steps", "book-fine"));
    card.append(node("p", "Visual evidence items: " +
        (book.visual_items_examined || 0) +
        " · Visual inventory " + (book.visual_inventory_finished ?
            "finished (meaning unverified)" : "not confirmed complete"), "book-fine"));
    card.append(node("p", "BRAHMAGYAN candidate receipts: " +
        (book.brahmagyan_candidate_receipts || 0) +
        " · Rishi factual verification: pending", "book-fine"));
    if (reading.last_error) card.append(node("p",
        "Last reading error: " + reading.last_error, "book-error"));
    return card;
  }
  async function refresh() {
    try {
      const response = await fetch("/api/books", {cache:"no-store",
        credentials:"same-origin"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      const books = Array.isArray(data.books) ? data.books : [];
      target.replaceChildren();
      state.textContent = books.length + " locally registered books";
      if (!books.length) {
        target.append(node("div", "No approved local books imported yet.", "empty-state"));
        return;
      }
      for (const book of books.slice(0,100)) {
        const sessions = book.sessions || {};
        const learned = Object.keys(sessions).filter(mode => mode.startsWith("ollama:"));
        if (!learned.length) {
          target.append(sessionCard(book, "Indexed only — no model reading", {
            lines_processed:0,lines_total:book.lines_indexed || 0,
            progress_percent:0,model_steps_completed:0, reached_end:false
          }));
        } else {
          for (const mode of learned) target.append(sessionCard(book, mode, sessions[mode]));
        }
      }
    } catch (error) {
      state.textContent = "Book ledger unavailable";
      target.replaceChildren(node("p", "Cannot read local book status: " +
                                  String(error.message || error), "book-error"));
    }
  }
  refresh();
  window.setInterval(refresh, 15000);
})();
