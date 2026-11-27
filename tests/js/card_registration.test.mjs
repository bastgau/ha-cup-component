// The card registers its elements and its card-picker entry once, even when the script is loaded twice
// (a leftover dashboard resource next to the copy card.py serves). Run by tests/test_card_js.py under Node.

import assert from "node:assert/strict";
import test from "node:test";

import { browser } from "./browser.mjs";

test("loading the card twice defines each element once", () => {
  const { load, calls, window } = browser();

  load();
  load();

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
