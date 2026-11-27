/**
 * Cup Component Card
 * Custom card for the HA Cup Component integration.
 * Displays all monitored images grouped by update type.
 *
 * Config options:
 *   device_id       (required) - Device ID from the cup_component integration
 *   title           (optional) - Card title. Omit to hide the header entirely.
 *   hero_style      (optional) - "badges" (default) | "classic"
 *   hide_sections   (optional) - Array of section keys to hide
 *   order_sections  (optional) - Array of section keys defining display order
 *   collapsed       (optional) - "always" | "never" | "if_empty" (default)
 *   hide_hero       (optional) - true to hide the hero metrics block
 *   hide_footer     (optional) - true to hide the last checked footer
 *
 * custom_components/cup_component/card.py serves this file and adds it to every dashboard,
 * so it needs no dashboard resource.
 *
 * This file is synchronized to bastgau/ha-cup-component, where JavaScript is checked by
 * `scripts/lint js` (node --check, ESLint, Prettier) and by the `javascript` CI job.
 */

// ─── Helpers ──────────────────────────────────────────────────────────────────
// [START:helpers]

// Image references, versions and URLs come from the Cup server and from Docker image labels,
// which the image's author controls: everything inserted into innerHTML goes through
// escapeHtml, every link through safeUrl.
const HTML_ESCAPES = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

/**
 * Escape a value for insertion into HTML content or a quoted attribute.
 * @param {*} value
 * @returns {string}
 */
function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) => HTML_ESCAPES[character],
  );
}

/**
 * Return an absolute http(s) URL, escaped for an attribute.
 * @param {*} value
 * @returns {string|null} null for javascript:, data:, relative or invalid URLs
 */
function safeUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(String(value));
    return url.protocol === "http:" || url.protocol === "https:"
      ? escapeHtml(url.href)
      : null;
  } catch {
    return null;
  }
}

// [END:helpers]

// ─── Static assets ────────────────────────────────────────────────────────────

const INTEGRATION_DOMAIN = "cup_component";
const CARD_DESCRIPTION =
  "Displays all monitored Docker images grouped by update type.";
// Brand image served by Home Assistant's local brands API (requires an access token).
const CARD_LOGO_API_URL = `/api/brands/integration/${INTEGRATION_DOMAIN}/icon.png`;

// ─── CONFIG ───────────────────────────────────────────────────────────────────
// [START:config]

const CONFIG = {
  // UI texts - all user-facing strings
  TEXTS: {
    // Hero
    monitoredSingular: "monitored image",
    monitoredPlural: "monitored images",
    upToDateSingular: "up-to-date image",
    upToDatePlural: "up-to-date images",
    availableSingular: "update available",
    availablePlural: "updates available",
    upToDate: "Up to date",
    // Sections
    noImages: "No images",
    imageUnknown: "Unknown",
    lastCheckedUnknown: "Unknown",
    // Detail panel
    currentVersion: "Current version",
    newVersion: "New version",
    // Editor
    editorCollapsedBehaviour: "Default collapsed behaviour",
    editorHeroStyle: "Hero style",
    editorHideSections: "Hide sections",
    editorHideHeroBlock: "Hero block",
    editorHideFooter: "Footer",
    editorSectionOrder: "Section order",
    editorAddButton: "Add",
    // Section labels
    sectionMajorUpdates: "Major updates",
    sectionMinorUpdates: "Minor updates",
    sectionPatchUpdates: "Patch updates",
    sectionOtherUpdates: "Other updates",
    sectionUpToDate: "Up to date",
    sectionUnknown: "Unknown",
    sectionExcluded: "Excluded",
    sectionDivider: "── Divider ──",
  },
  // Colors - prefer HA CSS variables; hardcoded hex only when no semantic variable exists
  COLORS: {
    major_updates: "var(--error-color)",
    minor_updates: "var(--warning-color)",
    patch_updates: "var(--primary-color)",
    other_updates: "#9b59b6", // no HA variable - keep hardcoded
    up_to_date: "var(--success-color)",
    unknown: "var(--disabled-color)",
    excluded_images: "var(--disabled-color)",
  },
  // Icons (MDI icon names)
  ICONS: {
    // Section icons
    major_updates: "mdi:arrow-up-circle",
    minor_updates: "mdi:arrow-up-circle",
    patch_updates: "mdi:arrow-up-circle",
    other_updates: "mdi:arrow-up-circle",
    up_to_date: "mdi:check-circle",
    unknown: "mdi:help-circle-outline",
    excluded_images: "mdi:minus-circle-outline",
    // Hero icons
    update_available: "mdi:arrow-up-circle",
    no_updates: "mdi:check-circle-outline",
    docker: "mdi:docker",
    // UI chrome
    chevron_down: "mdi:chevron-down",
    chevron_up: "mdi:chevron-up",
    clock: "mdi:clock-outline",
    open_in_new: "mdi:open-in-new",
    plus: "mdi:plus",
    drag: "mdi:drag",
    close: "mdi:close",
  },
  // Default values for optional card config keys
  DEFAULTS: {
    hero_style: "badges",
    collapsed: "if_empty",
    hide_hero: false,
    hide_footer: false,
    hide_sections: [],
    // Preview-specific overrides applied in getStubConfig
    preview: {
      collapsed: "always",
      hide_sections: ["up_to_date", "unknown", "excluded_images"],
      hide_footer: true,
    },
  },
};

const DEFAULT_SECTIONS = [
  {
    key: "major_updates",
    label: CONFIG.TEXTS.sectionMajorUpdates,
    icon: CONFIG.ICONS.major_updates,
    color: CONFIG.COLORS.major_updates,
  },
  {
    key: "minor_updates",
    label: CONFIG.TEXTS.sectionMinorUpdates,
    icon: CONFIG.ICONS.minor_updates,
    color: CONFIG.COLORS.minor_updates,
  },
  {
    key: "patch_updates",
    label: CONFIG.TEXTS.sectionPatchUpdates,
    icon: CONFIG.ICONS.patch_updates,
    color: CONFIG.COLORS.patch_updates,
  },
  {
    key: "other_updates",
    label: CONFIG.TEXTS.sectionOtherUpdates,
    icon: CONFIG.ICONS.other_updates,
    color: CONFIG.COLORS.other_updates,
  },
  {
    key: "up_to_date",
    label: CONFIG.TEXTS.sectionUpToDate,
    icon: CONFIG.ICONS.up_to_date,
    color: CONFIG.COLORS.up_to_date,
  },
  {
    key: "unknown",
    label: CONFIG.TEXTS.sectionUnknown,
    icon: CONFIG.ICONS.unknown,
    color: CONFIG.COLORS.unknown,
  },
  {
    key: "excluded_images",
    label: CONFIG.TEXTS.sectionExcluded,
    icon: CONFIG.ICONS.excluded_images,
    color: CONFIG.COLORS.excluded_images,
  },
];

const ALL_SECTION_KEYS = DEFAULT_SECTIONS.map((s) => s.key);

// ─── Editor ───────────────────────────────────────────────────────────────────
// Must be registered BEFORE CupImagesCard.

const EDITOR_SECTION_KEYS = [...ALL_SECTION_KEYS, "divider"];
const EDITOR_SECTION_LABELS = {
  ...Object.fromEntries(DEFAULT_SECTIONS.map((s) => [s.key, s.label])),
  divider: CONFIG.TEXTS.sectionDivider,
};

const COLLAPSED_OPTIONS = [
  { value: "always", label: "Always collapsed" },
  { value: "if_empty", label: "Collapse empty sections" },
  { value: "never", label: "Never collapsed" },
];

const HERO_STYLE_OPTIONS = [
  { value: "badges", label: "Badges" },
  { value: "classic", label: "Classic" },
];
// [END:config]

// [START:editor]
class CupImagesCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._dragSrcIndex = null;
    this._domBuilt = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._domBuilt) return;
    // Pass updated hass to all ha-selector elements without rebuilding DOM
    this.shadowRoot.querySelectorAll("ha-selector").forEach((el) => {
      el.hass = hass;
    });
  }

  setConfig(config) {
    // HA passes a frozen object - always shallow-copy to get a mutable one.
    if (!this._domBuilt) {
      this._config = { ...config };
      this._buildDOM();
    } else {
      // DOM already built: accept incoming config (HA echoes back our dispatches).
      this._config = { ...config };
      this._updateValues();
    }
  }

  // ─── Build DOM once ─────────────────────────────────────────────────────────

  _buildDOM() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .editor { display: flex; flex-direction: column; gap: var(--ha-space-4); padding: var(--ha-space-4) 0; }
        .collapsible-header {
          display: flex; align-items: center; justify-content: space-between;
          cursor: pointer; user-select: none;
        }
        .collapsible-header:hover .field-label { color: var(--primary-text-color); }
        .collapsible-header ha-icon { --mdc-icon-size: 16px; color: var(--secondary-text-color); }
        .collapsible-body { margin-top: var(--ha-space-2); }
        .collapsible-body[hidden] { display: none; }
        .field-label {
          font-size: var(--ha-font-size-s);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: var(--secondary-text-color);
          margin-bottom: var(--ha-space-1);
        }
        .checkbox-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--ha-space-1) var(--ha-space-4); }
        .checkbox-row {
          display: flex; align-items: center; gap: var(--ha-space-2);
          font-size: var(--ha-font-size-m);
          cursor: pointer; user-select: none;
        }
        .checkbox-row input[type=checkbox] { width: 18px; height: 18px; cursor: pointer; }
        .order-list { display: flex; flex-direction: column; gap: var(--ha-space-1); }
        .order-item {
          display: flex; align-items: center; gap: var(--ha-space-2);
          padding: 6px var(--ha-space-2); border-radius: 4px;
          background: var(--secondary-background-color);
          cursor: grab; font-size: var(--ha-font-size-m);
          border: 1px solid transparent;
        }
        .order-item.dragging  { opacity: 0.4; }
        .order-item.drag-over { border-color: var(--primary-color); }
        .order-item ha-icon   { --mdc-icon-size: 18px; color: var(--secondary-text-color); flex-shrink: 0; }
        .order-item span      { flex: 1; }
        .order-item .remove-btn { cursor: pointer; color: var(--secondary-text-color); --mdc-icon-size: 16px; }
        .order-item .remove-btn:hover { color: var(--error-color); }
        .add-section-row { display: flex; align-items: center; gap: var(--ha-space-2); margin-top: var(--ha-space-1); }
        .add-section-row select {
          flex: 1; padding: 6px var(--ha-space-2); border-radius: 4px;
          border: 1px solid var(--divider-color);
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: var(--ha-font-size-m);
        }
        .add-btn {
          display: inline-flex; align-items: center; gap: var(--ha-space-1);
          padding: 6px var(--ha-space-3); border-radius: 4px;
          border: 1px solid var(--primary-color); background: none;
          color: var(--primary-color); font-size: var(--ha-font-size-m); cursor: pointer;
        }
        .add-btn:hover { background: var(--primary-color); color: var(--primary-background-color); }
        /* Hide validation error styling on optional title field */
        #title-field { --mdc-text-field-error-color: transparent; }
        .section-divider { border: none; border-top: 1px solid var(--divider-color); margin: 0; }
      </style>
      <div class="editor">

        <div>
          <ha-selector id="device-picker"></ha-selector>
        </div>

        <hr class="section-divider">

        <div>
          <ha-selector id="title-field"></ha-selector>
        </div>

        <hr class="section-divider">

        <div>
          <div class="collapsible-header" id="collapsed-behaviour-header">
            <div class="field-label">${CONFIG.TEXTS.editorCollapsedBehaviour}</div>
            <ha-icon icon="${CONFIG.ICONS.chevron_down}"></ha-icon>
          </div>
          <div class="collapsible-body" id="collapsed-behaviour-body" hidden>
            <ha-selector id="collapsed-select"></ha-selector>
          </div>
        </div>

        <hr class="section-divider">

        <div>
          <div class="collapsible-header" id="hero-style-header">
            <div class="field-label">${CONFIG.TEXTS.editorHeroStyle}</div>
            <ha-icon icon="${CONFIG.ICONS.chevron_down}"></ha-icon>
          </div>
          <div class="collapsible-body" id="hero-style-body" hidden>
            <ha-selector id="hero-style-select"></ha-selector>
          </div>
        </div>

        <hr class="section-divider">

        <div>
          <div class="collapsible-header" id="hide-sections-header">
            <div class="field-label">${CONFIG.TEXTS.editorHideSections}</div>
            <ha-icon icon="${CONFIG.ICONS.chevron_down}"></ha-icon>
          </div>
          <div class="collapsible-body" id="hide-sections-body" hidden>
            <div class="checkbox-grid">
              <label class="checkbox-row">
                <input type="checkbox" id="hide-hero-cb">
                ${CONFIG.TEXTS.editorHideHeroBlock}
              </label>
              <label class="checkbox-row">
                <input type="checkbox" id="hide-footer-cb">
                ${CONFIG.TEXTS.editorHideFooter}
              </label>
            </div>
            <hr class="section-divider">
            <div class="checkbox-grid">
              ${ALL_SECTION_KEYS.map(
                (key) => `
                <label class="checkbox-row">
                  <input type="checkbox" data-key="${key}">
                  ${EDITOR_SECTION_LABELS[key]}
                </label>
              `,
              ).join("")}
            </div>
          </div>
        </div>

        <hr class="section-divider">

        <div>
          <div class="collapsible-header" id="section-order-header">
            <div class="field-label">${CONFIG.TEXTS.editorSectionOrder}</div>
            <ha-icon icon="${CONFIG.ICONS.chevron_down}"></ha-icon>
          </div>
          <div class="collapsible-body" id="section-order-body" hidden>
            <div id="order-list-wrapper">
              <div class="order-list" id="order-list"></div>
            </div>
            <div class="add-section-row">
              <select id="add-select">
                ${EDITOR_SECTION_KEYS.map((key) => `<option value="${key}">${EDITOR_SECTION_LABELS[key]}</option>`).join("")}
              </select>
              <button class="add-btn" id="add-btn"><ha-icon icon="${CONFIG.ICONS.plus}"></ha-icon> ${CONFIG.TEXTS.editorAddButton}</button>
            </div>
          </div>
        </div>


      </div>
    `;

    // Assign static selector schemas (never change after build)
    const root = this.shadowRoot;
    root.querySelector("#device-picker").selector = {
      device: { integration: INTEGRATION_DOMAIN },
    };
    root.querySelector("#device-picker").label =
      this._hass?.localize("ui.components.device-picker.device") || "Device";
    root.querySelector("#title-field").selector = { text: { suffix: "" } };
    const titleLabel =
      this._hass?.localize("ui.panel.lovelace.editor.card.generic.title") ||
      "Title";
    const optionalLabel =
      this._hass?.localize("ui.common.optional") || "optional";
    root.querySelector("#title-field").label =
      `${titleLabel} (${optionalLabel})`;
    root.querySelector("#title-field").required = false;
    root.querySelector("#collapsed-select").selector = {
      select: { options: COLLAPSED_OPTIONS },
    };
    root.querySelector("#hero-style-select").selector = {
      select: { mode: "list", options: HERO_STYLE_OPTIONS },
    };

    this._domBuilt = true;
    this._updateValues();
    this._attachListeners();
  }

  // ─── Update values (no DOM rebuild) ─────────────────────────────────────────

  _updateValues() {
    const cfg = this._config;
    const root = this.shadowRoot;

    // Inject hass into all ha-selector elements
    if (this._hass) {
      root.querySelectorAll("ha-selector").forEach((el) => {
        el.hass = this._hass;
      });
    }

    // Set ha-selector values
    root.querySelector("#device-picker").value = cfg.device_id ?? "";
    root.querySelector("#title-field").value = cfg.title ?? "";
    root.querySelector("#collapsed-select").value =
      cfg.collapsed ?? CONFIG.DEFAULTS.collapsed;
    root.querySelector("#hero-style-select").value =
      cfg.hero_style ?? CONFIG.DEFAULTS.hero_style;

    // Set checkbox states for display toggles
    root.querySelector("#hide-hero-cb").checked = !!cfg.hide_hero;
    root.querySelector("#hide-footer-cb").checked = !!cfg.hide_footer;

    // Set checkbox states for section keys only (inputs with data-key)
    const hideSections = new Set(cfg.hide_sections ?? []);
    root.querySelectorAll("input[type=checkbox][data-key]").forEach((cb) => {
      cb.checked = hideSections.has(cb.dataset.key);
    });

    // Rebuild only the dynamic order list
    const orderSections = cfg.order_sections ?? ALL_SECTION_KEYS;
    root.querySelector("#order-list").innerHTML = orderSections
      .map(
        (key, i) => `
      <div class="order-item" draggable="true" data-index="${i}" data-key="${key}">
        <ha-icon icon="${CONFIG.ICONS.drag}"></ha-icon>
        <span>${EDITOR_SECTION_LABELS[key] ?? key}</span>
        <ha-icon class="remove-btn" icon="${CONFIG.ICONS.close}" data-index="${i}"></ha-icon>
      </div>
    `,
      )
      .join("");
  }

  // ─── Listeners (attached once) ───────────────────────────────────────────────

  _attachListeners() {
    const root = this.shadowRoot;

    // Device picker
    root
      .querySelector("#device-picker")
      .addEventListener("value-changed", (e) => {
        this._updateConfig({ device_id: e.detail.value });
      });

    // Title - no re-render to preserve focus
    root
      .querySelector("#title-field")
      .addEventListener("value-changed", (e) => {
        const val = (e.detail.value ?? "").trim();
        if (val) this._config.title = val;
        else delete this._config.title;
        this._fireConfig();
      });

    // Collapsed select
    root
      .querySelector("#collapsed-select")
      .addEventListener("value-changed", (e) => {
        const val = e.detail.value;
        this._updateConfig({
          collapsed: val === CONFIG.DEFAULTS.collapsed ? undefined : val,
        });
      });

    // Hero style radio
    root
      .querySelector("#hero-style-select")
      .addEventListener("value-changed", (e) => {
        const val = e.detail.value;
        this._updateConfig({
          hero_style: val === CONFIG.DEFAULTS.hero_style ? undefined : val,
        });
      });

    // Hide hero / footer checkboxes
    root.querySelector("#hide-hero-cb").addEventListener("change", (e) => {
      this._updateConfig({ hide_hero: e.target.checked || undefined });
    });
    root.querySelector("#hide-footer-cb").addEventListener("change", (e) => {
      this._updateConfig({ hide_footer: e.target.checked || undefined });
    });

    // Hide sections - delegated on the sections grid only (inputs with data-key)
    root
      .querySelector("#hide-sections-body")
      .addEventListener("change", (e) => {
        if (!e.target.matches("input[type=checkbox][data-key]")) return;
        const hidden = [
          ...root.querySelectorAll("input[type=checkbox][data-key]"),
        ]
          .filter((c) => c.checked)
          .map((c) => c.dataset.key);
        this._updateConfig({
          hide_sections: hidden.length ? hidden : undefined,
        });
      });

    // Order list - drag+drop+remove delegated on wrapper (stable element)
    const wrapper = root.querySelector("#order-list-wrapper");
    wrapper.addEventListener("dragstart", (e) => {
      const item = e.target.closest(".order-item");
      if (!item) return;
      this._dragSrcIndex = parseInt(item.dataset.index, 10);
      item.classList.add("dragging");
    });
    wrapper.addEventListener("dragend", () => {
      root
        .querySelectorAll(".order-item")
        .forEach((el) => el.classList.remove("dragging", "drag-over"));
    });
    wrapper.addEventListener("dragover", (e) => {
      e.preventDefault();
      const item = e.target.closest(".order-item");
      root
        .querySelectorAll(".order-item")
        .forEach((el) => el.classList.remove("drag-over"));
      if (item) item.classList.add("drag-over");
    });
    wrapper.addEventListener("drop", (e) => {
      e.preventDefault();
      const item = e.target.closest(".order-item");
      if (!item || this._dragSrcIndex === null) return;
      const destIndex = parseInt(item.dataset.index, 10);
      if (destIndex === this._dragSrcIndex) return;
      const order = [...(this._config.order_sections ?? ALL_SECTION_KEYS)];
      const [moved] = order.splice(this._dragSrcIndex, 1);
      order.splice(destIndex, 0, moved);
      this._dragSrcIndex = null;
      this._updateConfig({ order_sections: order });
    });
    wrapper.addEventListener("click", (e) => {
      const btn = e.target.closest(".remove-btn");
      if (!btn) return;
      const index = parseInt(btn.dataset.index, 10);
      const order = [...(this._config.order_sections ?? ALL_SECTION_KEYS)];
      order.splice(index, 1);
      this._updateConfig({ order_sections: order.length ? order : undefined });
    });

    // Collapsible sections toggle
    const toggleCollapsible = (headerId, bodyId) => {
      const header = root.querySelector(`#${headerId}`);
      const body = root.querySelector(`#${bodyId}`);
      const icon = header.querySelector("ha-icon");
      header.addEventListener("click", () => {
        const isHidden = body.hasAttribute("hidden");
        isHidden
          ? body.removeAttribute("hidden")
          : body.setAttribute("hidden", "");
        icon.setAttribute(
          "icon",
          isHidden ? CONFIG.ICONS.chevron_up : CONFIG.ICONS.chevron_down,
        );
      });
    };
    toggleCollapsible("collapsed-behaviour-header", "collapsed-behaviour-body");
    toggleCollapsible("hero-style-header", "hero-style-body");
    toggleCollapsible("hide-sections-header", "hide-sections-body");
    toggleCollapsible("section-order-header", "section-order-body");

    // Add section
    root.querySelector("#add-btn").addEventListener("click", () => {
      const key = root.querySelector("#add-select").value;
      if (!key) return;
      const order = [...(this._config.order_sections ?? ALL_SECTION_KEYS)];
      order.push(key);
      this._updateConfig({ order_sections: order });
    });
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────────

  _fireConfig() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
  }

  /**
   * Merge changes into config, fire config-changed, and update values in place.
   * @param {Object} changes
   */
  _updateConfig(changes) {
    for (const [k, v] of Object.entries(changes)) {
      if (v === undefined) delete this._config[k];
      else this._config[k] = v;
    }
    this._fireConfig();
    this._updateValues();
  }
}

// [END:editor]
if (!customElements.get("cup-component-card-editor")) {
  customElements.define("cup-component-card-editor", CupImagesCardEditor);
}

// ─── Card ─────────────────────────────────────────────────────────────────────
// [START:card]

class CupImagesCard extends HTMLElement {
  constructor() {
    super();
    this._deviceEntities = null;
    this._logoUrl = ""; // resolved asynchronously, empty until then
    this._collapsedSections = new Set();
    this._expandedRows = new Set();
    this.attachShadow({ mode: "open" });

    // Single persistent click listener - section toggle + row expand + refresh button
    this.shadowRoot.addEventListener("click", (e) => {
      if (e.target.closest("#refresh-btn")) {
        e.stopPropagation();
        this._pressRefresh();
        return;
      }
      // Row header toggle (whole header is clickable, except links)
      if (e.target.closest(".group-row-link")) return;
      const header = e.target.closest(".group-header");
      if (header) {
        const row = header.closest(".group-row");
        if (!row || row.classList.contains("no-details")) return;
        const key = row.dataset.key;
        if (this._expandedRows.has(key)) {
          this._expandedRows.delete(key);
          row.classList.remove("expanded");
        } else {
          this._expandedRows.add(key);
          row.classList.add("expanded");
        }
        return;
      }
      // Section collapse toggle
      const title = e.target.closest(".group-title");
      if (!title) return;
      const key = title.dataset.key;
      const block = this.shadowRoot.querySelector(
        `.group-block[data-key="${key}"]`,
      );
      if (!block) return;
      if (this._collapsedSections.has(key)) {
        this._collapsedSections.delete(key);
        block.classList.remove("collapsed");
      } else {
        this._collapsedSections.add(key);
        block.classList.add("collapsed");
      }
    });
  }

  setConfig(config) {
    if (!config.device_id) throw new Error("Please define a device_id.");
    // _preview is a stub-only flag used to render the card picker preview
    const { _preview, ...cleanConfig } = config;
    if (_preview) {
      delete cleanConfig.collapsed;
      delete cleanConfig.hide_sections;
      delete cleanConfig.hide_footer;
    }
    this._config = _preview ? config : cleanConfig;
    this._deviceEntities = null;
    this.content = null;
    this._collapsedSections = new Set();
    this._expandedRows = new Set();
    this._lastSnapshot = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._logoResolved) {
      // The card renders right away; the logo shows up once resolved, or never if it cannot be.
      this._logoResolved = true;
      this._resolveLogoUrl().finally(() => {
        this._lastSnapshot = null;
        this._render();
      });
    }
    this._render();
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement("cup-component-card-editor");
  }

  static getStubConfig(hass) {
    // Auto-select the first cup_component device for the card picker preview
    const entity = Object.values(hass?.entities ?? {}).find(
      (e) => e.platform === INTEGRATION_DOMAIN,
    );
    return {
      device_id: entity?.device_id ?? "",
      _preview: true,
      ...CONFIG.DEFAULTS.preview,
    };
  }

  // ─── Logo resolution ─────────────────────────────────────────────────────────

  /**
   * Resolve the logo URL. The logo is the integration's own brand/icon.png, served by
   * Home Assistant (2026.3 and later, below the minimum version this integration supports)
   * behind a brands access token. The brands CDN has no Cup logo.
   */
  async _resolveLogoUrl() {
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "brands/access_token",
      });
      if (result?.token) {
        this._logoUrl = `${CARD_LOGO_API_URL}?token=${encodeURIComponent(result.token)}`;
      }
    } catch (err) {
      console.warn("cup-component-card: the logo cannot be loaded.", err);
    }
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────────

  _isCollapsed(key, count) {
    const mode = this._config.collapsed ?? CONFIG.DEFAULTS.collapsed;
    if (mode === "always") return true;
    if (mode === "never") return false;
    if (this._collapsedSections.has(key)) return true;
    return count === 0;
  }

  /**
   * Return the configuration_url ("Visit" link) of the configured device, sanitized and
   * escaped, or null if absent or not http(s).
   * @returns {string|null}
   */
  get _deviceVisitUrl() {
    return safeUrl(
      this._hass?.devices?.[this._config?.device_id]?.configuration_url,
    );
  }

  /**
   * Render the integration logo, wrapped in a link to the device's Visit URL if available.
   * @returns {string}
   */
  _renderLogoHtml() {
    if (!this._logoUrl) return "";
    const imgTag = `<img src="${escapeHtml(this._logoUrl)}" alt="Logo Cup Component">`;
    return this._deviceVisitUrl
      ? `<a href="${this._deviceVisitUrl}" target="_blank" rel="noopener noreferrer" class="logo-link">${imgTag}</a>`
      : imgTag;
  }

  /**
   * Return the singular or plural label depending on count.
   * @param {number} count
   * @param {string} singular
   * @param {string} plural
   * @returns {string}
   */
  _pluralize(count, singular, plural) {
    return count > 1 ? plural : singular;
  }

  /**
   * Return the update icon name based on whether updates are available.
   * @param {number} count
   * @returns {string}
   */
  _updateIcon(count) {
    return count > 0 ? CONFIG.ICONS.update_available : CONFIG.ICONS.no_updates;
  }

  /**
   * Resolve all entities belonging to the configured device.
   * Results are cached until setConfig() is called again.
   * @returns {Object} Map of translation_key -> entity_id
   */
  _resolveDeviceEntities() {
    if (this._deviceEntities) return this._deviceEntities;
    const result = {};
    for (const entry of Object.values(this._hass.entities ?? {})) {
      if (entry.device_id === this._config.device_id && entry.translation_key) {
        result[entry.translation_key] = entry.entity_id;
      }
    }
    this._deviceEntities = result;
    return result;
  }

  /**
   * Find the entity_id of a sensor by translation_key on the configured device.
   * @param {string} translationKey
   * @returns {string|undefined}
   */
  _resolveSensorEntityId(translationKey) {
    return Object.values(this._hass.entities ?? {}).find(
      (e) =>
        e.device_id === this._config.device_id &&
        e.entity_id.startsWith("sensor.") &&
        e.translation_key === translationKey,
    )?.entity_id;
  }

  /** @returns {{ monitored_images: number, updates_available: number }} */
  _resolveMetrics() {
    const deviceEntities = this._resolveDeviceEntities();
    const monitoredTotal =
      parseInt(
        this._hass.states[deviceEntities["monitored_images"]]?.state,
        10,
      ) || 0;
    const updatesEntityId = this._resolveSensorEntityId("updates_available");
    const updatesAvailable =
      parseInt(this._hass.states[updatesEntityId]?.state, 10) || 0;
    return {
      monitored_images: monitoredTotal,
      updates_available: updatesAvailable,
    };
  }

  /** @returns {string} */
  _resolveLastChecked() {
    const state =
      this._hass.states[this._resolveSensorEntityId("last_checked")]?.state;
    return state
      ? new Date(state).toLocaleString(undefined, {
          dateStyle: "short",
          timeStyle: "short",
        })
      : CONFIG.TEXTS.lastCheckedUnknown;
  }

  _classifyImage(image) {
    const result = image?.result;
    if (result?.has_update === null || result?.has_update === undefined)
      return "unknown";
    if (result.has_update === false) return "up_to_date";
    const map = {
      major: "major_updates",
      minor: "minor_updates",
      patch: "patch_updates",
      other: "other_updates",
    };
    return map[result?.info?.version_update_type] ?? "other_updates";
  }

  _resolveSections() {
    const sectionMap = Object.fromEntries(
      DEFAULT_SECTIONS.map((s) => [s.key, s]),
    );
    const deviceEntities = this._resolveDeviceEntities();
    const allImages =
      this._hass.states[deviceEntities["monitored_images"]]?.attributes
        ?.images_list ?? [];
    const buckets = Object.fromEntries(ALL_SECTION_KEYS.map((k) => [k, []]));
    for (const image of allImages)
      buckets[this._classifyImage(image)].push(image);

    const excludedEntityId = deviceEntities["excluded_images"];
    if (excludedEntityId) {
      buckets["excluded_images"] =
        this._hass.states[excludedEntityId]?.attributes?.images_list ?? [];
    }

    const orderedKeys = this._config.order_sections ?? ALL_SECTION_KEYS;
    const remainingKeys = ALL_SECTION_KEYS.filter(
      (k) => !orderedKeys.includes(k) && k !== "divider",
    );
    const hiddenKeys = new Set(this._config.hide_sections ?? []);

    return [...orderedKeys, ...remainingKeys]
      .filter(
        (key) => key === "divider" || (!hiddenKeys.has(key) && sectionMap[key]),
      )
      .map((key) =>
        key === "divider"
          ? { key: "divider", divider: true }
          : { ...sectionMap[key], images: buckets[key] ?? [] },
      );
  }

  // ─── Hero rendering ──────────────────────────────────────────────────────────

  /**
   * Render the "badges" hero style: logo + two pill badges side by side.
   * @param {{ monitored_images: number, updates_available: number }} metrics
   * @returns {string}
   */
  _renderHeroBadges(metrics) {
    return `
      <div class="hero-badge-wrapper">
        <span class="hero-badge monitored">
          <ha-icon icon="${CONFIG.ICONS.docker}"></ha-icon>
          <span>${metrics.monitored_images}</span>
          ${this._pluralize(metrics.monitored_images, CONFIG.TEXTS.monitoredSingular, CONFIG.TEXTS.monitoredPlural)}
        </span>
        <span class="hero-badge ${metrics.updates_available > 0 ? "has-updates" : ""}">
          <ha-icon icon="${this._updateIcon(metrics.updates_available)}"></ha-icon>
          ${
            metrics.updates_available > 0
              ? `<span>${metrics.updates_available}</span> ${this._pluralize(metrics.updates_available, CONFIG.TEXTS.availableSingular, CONFIG.TEXTS.availablePlural)}`
              : CONFIG.TEXTS.upToDate
          }
        </span>
      </div>`;
  }

  /**
   * Render the "classic" hero style: logo + large number + update count.
   * @param {{ monitored_images: number, updates_available: number }} metrics
   * @returns {string}
   */
  _renderHeroClassic(metrics) {
    return `
      <div class="hero-counter">
        ${this._renderLogoHtml()}
        <div class="hero-stats">
          <span class="hero-number">${metrics.monitored_images}<span class="hero-label">&nbsp;&nbsp;${this._pluralize(metrics.monitored_images, CONFIG.TEXTS.monitoredSingular, CONFIG.TEXTS.monitoredPlural)}</span></span>
          <span class="hero-updates ${metrics.updates_available > 0 ? "has-updates" : ""}">
            <ha-icon icon="${this._updateIcon(metrics.updates_available)}"></ha-icon>
            ${metrics.updates_available} ${this._pluralize(metrics.updates_available, CONFIG.TEXTS.availableSingular, CONFIG.TEXTS.availablePlural)}
          </span>
        </div>
      </div>`;
  }

  // ─── Render ──────────────────────────────────────────────────────────────────

  _render() {
    if (!this._hass || !this._config) return;

    const sections = this._resolveSections();
    const metrics = this._resolveMetrics();

    // Skip render if data hasn't changed
    const lastChecked = this._resolveLastChecked();
    const snapshot = JSON.stringify({ sections, metrics, lastChecked });
    if (this.content && snapshot === this._lastSnapshot) return;
    this._lastSnapshot = snapshot;
    const hasTitle = !!this._config.title;
    const showHero = !this._config.hide_hero;
    const showFooter = !this._config.hide_footer;
    const heroStyle = this._config.hero_style ?? CONFIG.DEFAULTS.hero_style;

    if (!this.content) {
      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          .card-header { margin-block-start: 0; margin-block-end: 0; }
          .card-header .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

          /* ── Hero: shared ── */
          .card-hero {
            display: flex; flex-direction: row; align-items: center;
            padding: 0 0 1px 0;
          }

          /* ── Hero: badges style ── */
          .logo-link { display: inline-flex; }
          .card-hero > img, .card-hero > a > img { width: 52px; height: 52px; object-fit: contain; flex-shrink: 0; }
          .hero-badge-wrapper { flex: 1; display: flex; justify-content: center; align-items: center; gap: var(--ha-space-2); flex-wrap: wrap; }
          .hero-badge {
            display: inline-flex; align-items: center; gap: var(--ha-space-1);
            padding: 2px 6px;
            font-size: var(--ha-font-size-s); font-weight: 500;
            color: var(--success-color);
          }
          .hero-badge.monitored { color: var(--primary-color); }
          .hero-badge.has-updates { color: var(--error-color); }
          .hero-badge ha-icon { --mdc-icon-size: 16px; pointer-events: none; }
          .hero-badge span { font-weight: 600; }

          /* ── Hero: classic style ── */
          .hero-counter { display: flex; align-items: center; gap: var(--ha-space-3); margin-left:6px; }
          .hero-counter > img, .hero-counter > a > img { width: 52px; height: 52px; object-fit: contain; }
          .hero-stats { display: flex; flex-direction: column; gap: var(--ha-space-1); padding-left: 6px; }
          .hero-number {
            display: flex; align-items: baseline; white-space: nowrap;
            font-size: var(--ha-font-size-4xl); font-weight: 700; line-height: 1;
            color: var(--success-color);
          }
          .hero-label { font-size: var(--ha-font-size-l); font-weight: 400; color: var(--success-color); }
          .hero-updates {
            display: flex; align-items: center; gap: var(--ha-space-1);
            font-size: var(--ha-font-size-s); color: var(--secondary-text-color);
          }
          .hero-updates ha-icon { --mdc-icon-size: 14px; }
          .hero-updates.has-updates { color: var(--error-color); }

          /* ── Sections ── */
          .sections-divider { border: none; border-top: 1px solid var(--divider-color); margin: 11px 0 var(--ha-space-2) 0; }
          .group-title {
            display: flex; align-items: center; gap: var(--ha-space-1);
            font-size: var(--ha-font-size-s); font-weight: 500;
            text-transform: uppercase; letter-spacing: 0.05em;
            color: var(--secondary-text-color);
            margin-top: 10px; margin-bottom: 0; cursor: pointer; user-select: none;
          }
          .group-block:first-child .group-title { margin-top: 0; }
          .group-title:hover { color: var(--primary-text-color); }
          .group-title .group-chevron { --mdc-icon-size: 16px; width: 16px; height: 16px; display: flex; transition: transform 0.2s ease; flex-shrink: 0; }
          .group-block.collapsed .group-chevron { transform: rotate(-90deg); }
          .group-body { display: flex; flex-direction: column; gap: var(--ha-space-2); margin-top: 10px; }
          .group-block.collapsed .group-pre-body,
          .group-block.collapsed .group-body { display: none; }
          .group-row {
            border-radius: 8px; overflow: hidden;
          }
          .group-header {
            display: flex; align-items: center; gap: 10px;
            padding: 10px 12px; min-height: 31px; cursor: pointer; user-select: none;
            background: color-mix(in srgb, var(--primary-text-color) 5%, transparent);
            border-radius: 8px; transition: background 0.15s;
          }
          .group-header:hover {
            background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
          }
          .group-row.no-details .group-header { cursor: default; user-select: auto; }
          .group-row.no-details .group-header:hover { background: color-mix(in srgb, var(--primary-text-color) 5%, transparent); }
          .group-row.expanded .group-header {
            border-radius: 8px 8px 0 0;
            background: color-mix(in srgb, var(--primary-text-color) 7%, transparent);
          }
          .row-icon { --mdc-icon-size: 18px; flex-shrink: 0; margin-left: -2px; margin-right: -2px; }
          .group-name {
            flex: 1; font-size: var(--ha-font-size-m); font-weight: 500;
            display: flex; align-items: center; gap: var(--ha-space-1);
            overflow: hidden;
          }
          .group-row-link {
            display: inline-flex; align-items: center;
            color: var(--secondary-text-color); background: none;
            padding: var(--ha-space-1); border-radius: 4px; text-decoration: none;
          }
          .group-row-link:hover { color: var(--primary-text-color); background: color-mix(in srgb, var(--primary-text-color) 8%, transparent); }
          .group-row-link ha-icon { --mdc-icon-size: 16px; }
          .chevron {
            --mdc-icon-size: 18px; color: var(--secondary-text-color);
            transition: transform 0.2s ease; flex-shrink: 0;
          }
          .group-row.expanded .chevron { transform: rotate(180deg); }
          .group-details {
            display: none;
            background: color-mix(in srgb, var(--primary-text-color) 7%, transparent);
            padding: 10px 12px 8px 12px;
            border-radius: 0 0 8px 8px;
            border-top: 1px solid var(--divider-color);
          }
          .group-row.expanded .group-details { display: block; }
          .detail-row {
            display: flex; flex-direction: column; gap: var(--ha-space-1);
          }
          .detail-row + .detail-row { margin-top: var(--ha-space-1); }
          .detail-label {
            font-size: var(--ha-font-size-xs); color: var(--secondary-text-color);
            text-transform: uppercase; letter-spacing: 0.05em;
          }
          .detail-value {
            font-size: var(--ha-font-size-s); color: var(--primary-text-color); font-weight: 500;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
          }
          .group-empty {
            font-size: var(--ha-font-size-m); color: var(--secondary-text-color);
            font-style: italic; padding: 0;
          }

          /* ── Footer ── */
          .card-content:has(.card-footer) { padding-bottom: 0; }
          .card-footer:empty { padding-top: 5px; padding-bottom: 5px; }
          .card-footer {
            display: flex; align-items: center; justify-content: flex-end;
            padding: 0 0 6px; margin-top: var(--ha-space-1);
          }
          .footer-content {
            display: inline-flex; align-items: center; gap: 6px;
            font-size: var(--ha-font-size-xs); color: var(--secondary-text-color); font-style: italic;
          }
          button.footer-content {
            padding: 2px 0; border-radius: 999px; border: none; background: none; cursor: pointer;
          }
          button.footer-content:hover { color: var(--primary-text-color); background: var(--secondary-background-color); }
          .footer-content ha-icon { --mdc-icon-size: 12px; }
        </style>
        <ha-card>
          ${hasTitle ? `<h1 class="card-header"><div class="name">${escapeHtml(this._config.title)}</div></h1>` : ""}
          <div class="card-content">
            <div id="cup-container"></div>
            ${
              showFooter
                ? `
            <div class="card-footer">
              <button class="footer-content" id="refresh-btn">
                <ha-icon icon="${CONFIG.ICONS.clock}"></ha-icon> ${this._resolveLastChecked()}
              </button>
            </div>`
                : `<div class="card-footer"></div>`
            }
          </div>
        </ha-card>
      `;

      this.content = this.shadowRoot.getElementById("cup-container");
    }

    this._updateContent(sections, metrics, showHero, heroStyle);
  }

  /**
   * Render dynamic content (hero + sections) into #cup-container.
   * @param {Array}   sections
   * @param {Object}  metrics
   * @param {boolean} showHero
   * @param {string}  heroStyle
   */
  _updateContent(sections, metrics, showHero, heroStyle) {
    const isFirstRender = !this.content.querySelector(".group-block");

    if (isFirstRender) {
      // Full render on first pass - build the entire DOM
      this.content.innerHTML = `
        ${
          showHero
            ? `
        <div class="card-hero">
          ${heroStyle === "classic" ? this._renderHeroClassic(metrics) : this._renderHeroBadges(metrics)}
        </div>
        <hr class="sections-divider">`
            : ""
        }
        ${sections
          .map((section) => {
            if (section.divider) return `<hr class="sections-divider">`;
            const collapsed = this._isCollapsed(
              section.key,
              section.images.length,
            );
            if (collapsed) this._collapsedSections.add(section.key);
            return `
            <div class="group-block${collapsed ? " collapsed" : ""}" data-key="${section.key}">
              <div class="group-title" data-key="${section.key}">
                <ha-icon class="group-chevron" icon="${CONFIG.ICONS.chevron_down}"></ha-icon>
                <span>${section.label} (<span class="group-count">${section.images.length}</span>)</span>
              </div>
              <div class="group-pre-body"></div>
              <div class="group-body">
                ${this._renderImages(section)}
              </div>
            </div>`;
          })
          .join("")}
      `;
    } else {
      // Subsequent refreshes - preserve collapse state, only update dynamic parts
      if (showHero) {
        const hero = this.content.querySelector(".card-hero");
        if (hero)
          hero.innerHTML =
            heroStyle === "classic"
              ? this._renderHeroClassic(metrics)
              : this._renderHeroBadges(metrics);
      }

      sections.forEach((section) => {
        if (section.divider) return;
        const block = this.content.querySelector(
          `.group-block[data-key="${section.key}"]`,
        );
        if (!block) return;
        const countEl = block.querySelector(".group-count");
        if (countEl) countEl.textContent = section.images.length;
        const body = block.querySelector(".group-body");
        if (body) body.innerHTML = this._renderImages(section);
      });

      const footerBtn = this.shadowRoot.querySelector("#refresh-btn");
      if (footerBtn)
        footerBtn.innerHTML = `<ha-icon icon="${CONFIG.ICONS.clock}"></ha-icon> ${this._resolveLastChecked()}`;
    }
  }

  // ─── Actions ──────────────────────────────────────────────────────────────────

  async _pressRefresh() {
    const entityId = this._resolveDeviceEntities()["action_refresh"];
    if (!entityId) return;
    await this._hass.callService("button", "press", { entity_id: entityId });
  }

  // ─── Template helpers ─────────────────────────────────────────────────────────

  /**
   * Render the version line for an image.
   * @param {Object} image
   * @returns {string}
   */
  /**
   * Extract version info from an image as { current, next, hasUpdate }.
   * @param {Object} image
   * @returns {{ current: string|null, next: string|null, hasUpdate: boolean }}
   */
  _getVersionInfo(image) {
    const info = image?.result?.info;
    if (!info) return { current: null, next: null, hasUpdate: false };
    if (info.type === "digest") {
      const current = info.local_digests?.[0]?.substring(7, 19) ?? null;
      const next = info.remote_digest?.substring(7, 19) ?? null;
      return {
        current,
        next,
        hasUpdate: !!(current && next && current !== next),
      };
    }
    const current = info.current_version ?? null;
    const next = info.new_version ?? null;
    return {
      current,
      next,
      hasUpdate: !!(current && next && current !== next),
    };
  }

  /**
   * Render the image list HTML for a section.
   * @param {Object} section
   * @returns {string}
   */
  _renderImages(section) {
    if (section.images.length === 0)
      return `<div class="group-empty">${CONFIG.TEXTS.noImages}</div>`;
    return section.images
      .map((image) => {
        const key = image.reference ?? image.name ?? "";
        const { current, next } = this._getVersionInfo(image);
        const expanded = this._expandedRows.has(key);
        const hasDetails = !!(current || next);
        const url = safeUrl(image.url);
        return `
        <div class="group-row${expanded ? " expanded" : ""}${!hasDetails ? " no-details" : ""}" data-key="${escapeHtml(key)}">
          <div class="group-header">
            <ha-icon class="row-icon" icon="${section.icon}" style="color: ${section.color}"></ha-icon>
            <div class="group-name">
              <span>${key ? escapeHtml(key) : CONFIG.TEXTS.imageUnknown}</span>
              ${url ? `<a class="group-row-link" href="${url}" target="_blank" rel="noopener noreferrer"><ha-icon icon="${CONFIG.ICONS.open_in_new}"></ha-icon></a>` : ""}
            </div>
            ${hasDetails ? `<ha-icon class="chevron" icon="${CONFIG.ICONS.chevron_down}"></ha-icon>` : ""}
          </div>
          ${
            hasDetails
              ? `
          <div class="group-details">
            <div class="detail-row">
              <span class="detail-label">${CONFIG.TEXTS.currentVersion}</span>
              <span class="detail-value">${current === null ? "-" : escapeHtml(current)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">${CONFIG.TEXTS.newVersion}</span>
              <span class="detail-value">${next === null ? "-" : escapeHtml(next)}</span>
            </div>
          </div>`
              : ""
          }
        </div>`;
      })
      .join("");
  }
}

// [END:card]
// Loading the script twice (e.g. a leftover dashboard resource) must not define the elements again.
if (!customElements.get("cup-component-card")) {
  customElements.define("cup-component-card", CupImagesCard);
}

// [START:registration]
window.customCards = window.customCards ?? [];
if (!window.customCards.some((card) => card.type === "cup-component-card")) {
  window.customCards.push({
    type: "cup-component-card",
    name: "Cup Component Card",
    description: CARD_DESCRIPTION,
    preview: true,
  });
}

console.info(
  "%c 🐼 CUP-COMPONENT-CARD %c Version 1.90 ",
  "color: white; background: #2196f3; font-weight: 700;",
  "color: #2196f3; background: white; font-weight: 700;",
);
