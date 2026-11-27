// What the card inserts into its HTML: data from the Cup server and from Docker image labels is escaped, and
// a logo that cannot be loaded never keeps the card from rendering. Run by tests/test_card_js.py under Node.

import assert from "node:assert/strict";
import test from "node:test";

import { browser } from "./browser.mjs";

function newCard() {
  const { load, element } = browser();
  load();
  const Card = element("cup-component-card");
  return new Card();
}

const SECTION = { key: "major_updates", icon: "mdi:alert", color: "red" };

test("image references, versions and links from the Cup server are escaped", () => {
  const card = newCard();
  const html = card._renderImages({
    ...SECTION,
    images: [
      {
        reference: '<img src=x onerror="alert(1)">:latest',
        url: "javascript:alert(document.cookie)",
        result: {
          has_update: true,
          info: {
            type: "version",
            current_version: "<b>1</b>",
            new_version: '2" onmouseover="x',
          },
        },
      },
    ],
  });

  assert.ok(!html.includes("<img"), html);
  assert.ok(!html.includes("<b>"), html);
  assert.ok(!html.includes("javascript:"), html);
  assert.ok(!html.includes('" onmouseover'), html);
  assert.ok(
    html.includes("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;:latest"),
    html,
  );
});

test("only http(s) image links are kept", () => {
  const card = newCard();
  const link = (url) =>
    card._renderImages({
      ...SECTION,
      images: [
        { reference: "nginx:latest", url, result: { has_update: false } },
      ],
    });

  assert.ok(
    link("https://github.com/sergi0g/cup").includes(
      'href="https://github.com/sergi0g/cup"',
    ),
  );
  assert.ok(
    !link("data:text/html,<script>alert(1)</script>").includes(
      "group-row-link",
    ),
  );
  assert.ok(!link("not a url").includes("group-row-link"));
});

test("the card renders at once, and without a logo when the logo cannot be loaded", async () => {
  const card = newCard();
  let renders = 0;
  card._render = () => {
    renders += 1;
  };

  card.hass = {
    connection: {
      sendMessagePromise: () => Promise.reject(new Error("unauthorized")),
    },
  };
  assert.equal(renders, 1);

  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(renders, 2);
  assert.equal(card._renderLogoHtml(), "");
});

test("the logo comes from the integration's brand folder behind an access token", async () => {
  const card = newCard();
  card._hass = {
    connection: { sendMessagePromise: async () => ({ token: "a b" }) },
  };

  await card._resolveLogoUrl();

  assert.equal(
    card._logoUrl,
    "/api/brands/integration/cup_component/icon.png?token=a%20b",
  );
  assert.ok(
    card
      ._renderLogoHtml()
      .startsWith(
        '<img src="/api/brands/integration/cup_component/icon.png?token=a%20b"',
      ),
  );
});
