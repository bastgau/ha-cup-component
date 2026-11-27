// The card registers its elements and its card-picker entry once, even when the script is loaded twice
// (a leftover dashboard resource next to the copy card.py serves). Run by tests/test_card_js.py under Node.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const CARD = new URL(
  "../../custom_components/cup_component/frontend/cup-component-card.js",
  import.meta.url,
);

// The few browser globals the card touches while loading. Home Assistant loads the card as a module: each
// load has its own top-level scope, but customElements and window are shared, hence a context per load.
function browser() {
  const defined = new Map();
  const calls = [];
  const window = {};
  const context = {
    console: { info() {} },
    HTMLElement: class {},
    customElements: {
      get: (name) => defined.get(name),
      define: (name, element) => {
        calls.push(name);
        if (defined.has(name))
          throw new Error(`'${name}' has already been defined`);
        defined.set(name, element);
      },
    },
    window,
  };
  return {
    load: (source) => vm.runInContext(source, vm.createContext({ ...context })),
    calls,
    window,
  };
}

test("loading the card twice defines each element once", () => {
  const { load, calls, window } = browser();
  const source = readFileSync(CARD, "utf8");

  load(source);
  load(source);

  assert.deepEqual(calls.sort(), [
    "cup-component-card",
    "cup-component-card-editor",
  ]);
  assert.equal(
    window.customCards.filter((card) => card.type === "cup-component-card")
      .length,
    1,
  );
});
