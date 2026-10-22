(() => {
  "use strict";

  const catalog = __CATALOG__;
  const mailto = __MAIL_CATALOG__;
  const storageKey = "timelinestamp-demo-language";
  const normalize = value => value.trim().replace(/\s+/g, " ");
  const textEntries = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;

  while ((node = walker.nextNode())) {
    if (node.parentElement?.closest("script, style")) continue;
    const english = normalize(node.nodeValue);
    if (!Object.hasOwn(catalog, english)) continue;
    const leading = node.nodeValue.match(/^\s*/)[0];
    const trailing = node.nodeValue.match(/\s*$/)[0];
    textEntries.push({ node, english, leading, trailing });
  }

  const attributeEntries = [];
  document.querySelectorAll("[aria-label], [alt], [title]").forEach(element => {
    for (const name of ["aria-label", "alt", "title"]) {
      const english = element.getAttribute(name);
      if (english && Object.hasOwn(catalog, english)) {
        attributeEntries.push({ element, name, english });
      }
    }
  });

  const buttons = [...document.querySelectorAll(".language-switch [data-lang]")];
  const title = document.title;

  function setLanguage(language) {
    const selected = ["en", "ru", "zh"].includes(language) ? language : "en";
    for (const entry of textEntries) {
      const value = selected === "en" ? entry.english : catalog[entry.english][selected];
      entry.node.nodeValue = entry.leading + value + entry.trailing;
    }
    for (const entry of attributeEntries) {
      const value = selected === "en" ? entry.english : catalog[entry.english][selected];
      entry.element.setAttribute(entry.name, value);
    }
    document.title = selected === "en" ? title : catalog[title][selected];
    document.documentElement.lang = selected === "zh" ? "zh-CN" : selected;
    buttons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.lang === selected)));
    document.querySelectorAll("[data-mailto]").forEach(link => {
      link.href = mailto[selected][link.dataset.mailto];
    });
  }

  for (const button of buttons) {
    button.addEventListener("click", () => {
      setLanguage(button.dataset.lang);
      try { localStorage.setItem(storageKey, button.dataset.lang); } catch (_) { /* Private browsing can disable storage. */ }
    });
  }

  let saved = "en";
  try { saved = localStorage.getItem(storageKey) || "en"; } catch (_) { /* Keep the English default. */ }
  setLanguage(saved);
})();
