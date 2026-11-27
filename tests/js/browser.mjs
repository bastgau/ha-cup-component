// The few browser globals the card touches, for its tests under Node. Home Assistant loads the card as a
// module: each load has its own top-level scope, but customElements and window are shared, hence a context per
// load over the same globals.

import { readFileSync } from "node:fs";
import vm from "node:vm";

export const CARD_SOURCE = readFileSync(
  new URL(
    "../../custom_components/cup_component/frontend/cup-component-card.js",
    import.meta.url,
  ),
  "utf8",
);

export function browser() {
  const defined = new Map();
  const calls = [];
  const window = {};
  const globals = {
    console: { info() {}, warn() {} },
    URL,
    HTMLElement: class {
      attachShadow() {
        this.shadowRoot = {
          addEventListener() {},
          querySelector: () => null,
          getElementById: () => null,
        };
        return this.shadowRoot;
      }
    },
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
  const load = () =>
    vm.runInContext(CARD_SOURCE, vm.createContext({ ...globals }));
  return { load, calls, window, element: (name) => defined.get(name) };
}
