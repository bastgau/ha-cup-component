/**
 * Cup Images Card
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
 *   To debug: fetch('/local/custom_components/cup_component/cup-images-card.js?v='+Date.now()).then(r=>r.text()).then(t=>console.log(t.match(/const CARD_VERSION = "(\w+)"/)?.[1]))
 *
 */

// ─── Static labels & assets ────────────────────────────────────────────────

const INTEGRATION_DOMAIN = "cup_component";
const CARD_DESCRIPTION = "Displays all monitored Docker images grouped by update type.";
const CARD_VERSION = "XXXX";

// Brand image URL — resolved at runtime depending on HA version:
//   HA >= 2026.3: served via local brands API, theme-aware (icon vs dark_icon).
//   HA <  2026.3: fallback to the public brands CDN (dark_icon@2x only).

const CARD_LOGO_CDN_URL = `https://brands.home-assistant.io/_/${INTEGRATION_DOMAIN}/icon.png`;
const CARD_LOGO_API_URL = `/api/brands/integration/${INTEGRATION_DOMAIN}/icon.png`;

const LABELS = {
  // Card — hero
  monitoredSingular: "monitored image",
  monitoredPlural: "monitored images",
  upToDateSingular: "up-to-date image",
  upToDatePlural: "up-to-date images",
  availableSingular: "update available",
  availablePlural: "updates available",
  upToDate: "Up to date",
  // Card — sections
  noImages: "No images",
  imageUnknown: "Unknown",
  lastCheckedUnknown: "Unknown",
  // Editor
  editorCollapsedBehaviour: "Default collapsed behaviour",
  editorHeroStyle: "Hero style",
  editorHideSections: "Hide sections",
  editorHideHeroBlock: "Hero block",
  editorHideFooter: "Footer",
  editorSectionOrder: "Section order",
  editorAddButton: "Add",
};

const DEFAULT_SECTIONS = [
  { key: "major_updates", label: "Major Updates", icon: "mdi:alert-circle", color: "#db4437" },
  { key: "minor_updates", label: "Minor Updates", icon: "mdi:arrow-up-circle", color: "#f4a623" },
  { key: "patch_updates", label: "Patch Updates", icon: "mdi:arrow-up-circle-outline", color: "#4a90d9" },
  { key: "other_updates", label: "Other Updates", icon: "mdi:sync-circle", color: "#9b59b6" },
  { key: "up_to_date", label: "Up to Date", icon: "mdi:check-circle-outline", color: "#43a047" },
  { key: "unknown", label: "Unknown", icon: "mdi:help-circle-outline", color: "#9e9e9e" },
  { key: "excluded_images", label: "Excluded", icon: "mdi:minus-circle-outline", color: "#757575" },
];

const ALL_SECTION_KEYS = DEFAULT_SECTIONS.map((s) => s.key);
const _globalCollapsed = {};

// ─── Config defaults ──────────────────────────────────────────────────────────
// Single source of truth for all optional config keys.
// Used in the card render logic, editor, and getStubConfig.
const CONFIG_DEFAULTS = {
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
};

// ─── Editor ───────────────────────────────────────────────────────────────────
// Must be registered BEFORE CupImagesCard.

const EDITOR_SECTION_KEYS = [...ALL_SECTION_KEYS, "divider"];
const EDITOR_SECTION_LABELS = {
  major_updates: "Major Updates",
  minor_updates: "Minor Updates",
  patch_updates: "Patch Updates",
  other_updates: "Other Updates",
  up_to_date: "Up to Date",
  unknown: "Unknown",
  excluded_images: "Excluded",
  divider: "── Divider ──",
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
    this.shadowRoot.querySelectorAll("ha-selector").forEach((el) => { el.hass = hass; });
  }

  setConfig(config) {
    // HA passes a frozen object — always shallow-copy to get a mutable one.
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
        .editor { display: flex; flex-direction: column; gap: 16px; padding: 16px 0; }
        .collapsible-header {
          display: flex; align-items: center; justify-content: space-between;
          cursor: pointer; user-select: none;
        }
        .collapsible-header:hover .field-label { color: var(--primary-text-color); }
        .collapsible-header ha-icon { --mdc-icon-size: 16px; color: var(--secondary-text-color); }
        .collapsible-body { margin-top: 8px; }
        .collapsible-body[hidden] { display: none; }
        .field-label {
          font-size: var(--ha-font-size-s, 12px);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: var(--secondary-text-color);
          margin-bottom: 4px;
        }
        .checkbox-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; }
        .checkbox-row {
          display: flex; align-items: center; gap: 8px;
          font-size: var(--ha-font-size-m, 14px);
          cursor: pointer; user-select: none;
        }
        .checkbox-row input[type=checkbox] { width: 18px; height: 18px; cursor: pointer; }
        .order-list { display: flex; flex-direction: column; gap: 4px; }
        .order-item {
          display: flex; align-items: center; gap: 8px;
          padding: 6px 8px; border-radius: 4px;
          background: var(--secondary-background-color);
          cursor: grab; font-size: var(--ha-font-size-m, 14px);
          border: 1px solid transparent;
        }
        .order-item.dragging  { opacity: 0.4; }
        .order-item.drag-over { border-color: var(--primary-color); }
        .order-item ha-icon   { --mdc-icon-size: 18px; color: var(--secondary-text-color); flex-shrink: 0; }
        .order-item span      { flex: 1; }
        .order-item .remove-btn { cursor: pointer; color: var(--secondary-text-color); --mdc-icon-size: 16px; }
        .order-item .remove-btn:hover { color: var(--error-color); }
        .add-section-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
        .add-section-row select {
          flex: 1; padding: 6px 8px; border-radius: 4px;
          border: 1px solid var(--divider-color);
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-size: var(--ha-font-size-m, 14px);
        }
        .add-btn {
          display: inline-flex; align-items: center; gap: 4px;
          padding: 6px 12px; border-radius: 4px;
          border: 1px solid var(--primary-color); background: none;
          color: var(--primary-color); font-size: var(--ha-font-size-m, 14px); cursor: pointer;
        }
        .add-btn:hover { background: var(--primary-color); color: white; }
        /* Hide validation error styling on optional title field */
        #title-field { --mdc-text-field-error-color: transparent; }
      </style>
      <div class="editor">

        <div>
          <ha-selector id="device-picker"></ha-selector>
        </div>

        <div>
          <ha-selector id="title-field"></ha-selector>
        </div>

        <div>
          <div class="field-label">${LABELS.editorCollapsedBehaviour}</div>
          <ha-selector id="collapsed-select"></ha-selector>
        </div>

        <div>
          <div class="collapsible-header" id="hero-style-header">
            <div class="field-label">${LABELS.editorHeroStyle}</div>
            <ha-icon icon="mdi:chevron-down"></ha-icon>
          </div>
          <div class="collapsible-body" id="hero-style-body" hidden>
            <ha-selector id="hero-style-select"></ha-selector>
          </div>
        </div>

        <div>
          <div class="collapsible-header" id="hide-sections-header">
            <div class="field-label">${LABELS.editorHideSections}</div>
            <ha-icon icon="mdi:chevron-down"></ha-icon>
          </div>
          <div class="collapsible-body" id="hide-sections-body" hidden>
            <div class="checkbox-grid">
              <label class="checkbox-row">
                <input type="checkbox" id="hide-hero-cb">
                ${LABELS.editorHideHeroBlock}
              </label>
              <label class="checkbox-row">
                <input type="checkbox" id="hide-footer-cb">
                ${LABELS.editorHideFooter}
              </label>
            </div>
            <hr style="border:none;border-top:1px solid var(--divider-color);margin:8px 0;">
            <div class="checkbox-grid">
              ${ALL_SECTION_KEYS.map((key) => `
                <label class="checkbox-row">
                  <input type="checkbox" data-key="${key}">
                  ${EDITOR_SECTION_LABELS[key]}
                </label>
              `).join("")}
            </div>
          </div>
        </div>

        <div>
          <div class="collapsible-header" id="section-order-header">
            <div class="field-label">${LABELS.editorSectionOrder}</div>
            <ha-icon icon="mdi:chevron-down"></ha-icon>
          </div>
          <div class="collapsible-body" id="section-order-body" hidden>
            <div id="order-list-wrapper">
              <div class="order-list" id="order-list"></div>
            </div>
            <div class="add-section-row">
              <select id="add-select">
                ${EDITOR_SECTION_KEYS.map((key) => `<option value="${key}">${EDITOR_SECTION_LABELS[key]}</option>`).join("")}
              </select>
              <button class="add-btn" id="add-btn"><ha-icon icon="mdi:plus"></ha-icon> ${LABELS.editorAddButton}</button>
            </div>
          </div>
        </div>

        <!-- cup-images-card ${CARD_VERSION} -->

      </div>
    `;

    // Assign static selector schemas (never change after build)
    const root = this.shadowRoot;
    root.querySelector("#device-picker").selector = { device: { integration: INTEGRATION_DOMAIN } };
    root.querySelector("#device-picker").label = this._hass?.localize("ui.components.device-picker.device") || "Device";
    root.querySelector("#title-field").selector = { text: { suffix: "" } };
    const titleLabel = this._hass?.localize("ui.panel.lovelace.editor.card.generic.title") || "Title";
    const optionalLabel = this._hass?.localize("ui.common.optional") || "optional";
    root.querySelector("#title-field").label = `${titleLabel} (${optionalLabel})`;
    root.querySelector("#title-field").required = false;
    root.querySelector("#collapsed-select").selector = { select: { options: COLLAPSED_OPTIONS } };
    root.querySelector("#hero-style-select").selector = { select: { mode: "list", options: HERO_STYLE_OPTIONS } };

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
      root.querySelectorAll("ha-selector").forEach((el) => { el.hass = this._hass; });
    }

    // Set ha-selector values
    root.querySelector("#device-picker").value = cfg.device_id ?? "";
    root.querySelector("#title-field").value = cfg.title ?? "";
    root.querySelector("#collapsed-select").value = cfg.collapsed ?? CONFIG_DEFAULTS.collapsed;
    root.querySelector("#hero-style-select").value = cfg.hero_style ?? CONFIG_DEFAULTS.hero_style;

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
    root.querySelector("#order-list").innerHTML = orderSections.map((key, i) => `
      <div class="order-item" draggable="true" data-index="${i}" data-key="${key}">
        <ha-icon icon="mdi:drag"></ha-icon>
        <span>${EDITOR_SECTION_LABELS[key] ?? key}</span>
        <ha-icon class="remove-btn" icon="mdi:close" data-index="${i}"></ha-icon>
      </div>
    `).join("");
  }

  // ─── Listeners (attached once) ───────────────────────────────────────────────

  _attachListeners() {
    const root = this.shadowRoot;

    // Device picker
    root.querySelector("#device-picker").addEventListener("value-changed", (e) => {
      this._updateConfig({ device_id: e.detail.value });
    });

    // Title — no re-render to preserve focus
    root.querySelector("#title-field").addEventListener("value-changed", (e) => {
      const val = (e.detail.value ?? "").trim();
      if (val) this._config.title = val; else delete this._config.title;
      this._fireConfig();
    });

    // Collapsed select
    root.querySelector("#collapsed-select").addEventListener("value-changed", (e) => {
      const val = e.detail.value;
      this._updateConfig({ collapsed: val === CONFIG_DEFAULTS.collapsed ? undefined : val });
    });

    // Hero style radio
    root.querySelector("#hero-style-select").addEventListener("value-changed", (e) => {
      const val = e.detail.value;
      this._updateConfig({ hero_style: val === CONFIG_DEFAULTS.hero_style ? undefined : val });
    });

    // Hide hero / footer checkboxes
    root.querySelector("#hide-hero-cb").addEventListener("change", (e) => {
      this._updateConfig({ hide_hero: e.target.checked || undefined });
    });
    root.querySelector("#hide-footer-cb").addEventListener("change", (e) => {
      this._updateConfig({ hide_footer: e.target.checked || undefined });
    });

    // Hide sections — delegated on the sections grid only (inputs with data-key)
    root.querySelector("#hide-sections-body").addEventListener("change", (e) => {
      if (!e.target.matches("input[type=checkbox][data-key]")) return;
      const hidden = [...root.querySelectorAll("input[type=checkbox][data-key]")]
        .filter((c) => c.checked).map((c) => c.dataset.key);
      this._updateConfig({ hide_sections: hidden.length ? hidden : undefined });
    });

    // Order list — drag+drop+remove delegated on wrapper (stable element)
    const wrapper = root.querySelector("#order-list-wrapper");
    wrapper.addEventListener("dragstart", (e) => {
      const item = e.target.closest(".order-item");
      if (!item) return;
      this._dragSrcIndex = parseInt(item.dataset.index, 10);
      item.classList.add("dragging");
    });
    wrapper.addEventListener("dragend", () => {
      root.querySelectorAll(".order-item").forEach((el) => el.classList.remove("dragging", "drag-over"));
    });
    wrapper.addEventListener("dragover", (e) => {
      e.preventDefault();
      const item = e.target.closest(".order-item");
      root.querySelectorAll(".order-item").forEach((el) => el.classList.remove("drag-over"));
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
        isHidden ? body.removeAttribute("hidden") : body.setAttribute("hidden", "");
        icon.setAttribute("icon", isHidden ? "mdi:chevron-up" : "mdi:chevron-down");
      });
    };
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
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    }));
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

customElements.define("cup-images-card-editor", CupImagesCardEditor);

// ─── Card ─────────────────────────────────────────────────────────────────────

class CupImagesCard extends HTMLElement {

  constructor() {
    super();
    this._deviceEntities = null;
    this._initialized = false;
    this._logoUrl = ""; // resolved asynchronously before first render
    this.attachShadow({ mode: "open" });

    // Single persistent click listener — toggle section visibility directly in DOM
    this.shadowRoot.addEventListener("click", (e) => {
      const title = e.target.closest(".section-title");
      if (!title) return;
      const key = title.dataset.key;
      const body = this.shadowRoot.querySelector(`.section-body[data-key="${key}"]`);
      const icon = title.querySelector("ha-icon");
      if (!body) return;
      const isCollapsed = body.style.display !== "none";
      _globalCollapsed[key] = isCollapsed;
      body.style.display = isCollapsed ? "none" : "";
      if (icon) icon.setAttribute("icon", isCollapsed ? "mdi:chevron-down" : "mdi:chevron-up");
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
    this._initialized = false;
  }

  set hass(hass) {
    this._hass = hass;
    // Resolve logo URL once, then render. Subsequent calls render immediately.
    if (!this._logoResolved) {
      this._logoResolved = true;
      this._resolveLogoUrl().then(() => this._render());
      return; // don't render yet — logo URL not ready
    } else {
      if (!this._logoUrl) return;
      this._render();
    }
  }

  getCardSize() { return 3; }

  static getConfigElement() {
    return document.createElement("cup-images-card-editor");
  }

  static getStubConfig(hass) {
    // Auto-select the first cup_component device for the card picker preview
    const entity = Object.values(hass?.entities ?? {}).find(
      (e) => e.platform === INTEGRATION_DOMAIN
    );
    return {
      device_id: entity?.device_id ?? "",
      _preview: true,
      ...CONFIG_DEFAULTS.preview,
    };
  }

  // ─── Logo resolution ─────────────────────────────────────────────────────────

  /**
   * Resolve the logo URL depending on HA version.
   * HA >= 2026.3: fetch a short-lived access token via WebSocket and build
   *               a local brands API URL (theme-aware, served locally).
   * HA <  2026.3: fall back to the public brands CDN URL synchronously.
   */
  async _resolveLogoUrl() {
    const version = this._hass?.config?.version ?? "";
    const [major, minor] = version.split(".").map(Number);
    const supportsLocalBrands = major > 2026 || (major === 2026 && minor >= 3);

    if (!supportsLocalBrands) {
      this._logoUrl = CARD_LOGO_CDN_URL;
      return;
    }

    const result = await this._hass.connection.sendMessagePromise({ type: "brands/access_token" });
    if (result.token) {
      this._logoUrl = `${CARD_LOGO_API_URL}?token=${result.token}`;
    }

  }

  // ─── Helpers ─────────────────────────────────────────────────────────────────

  _isCollapsed(key, count) {
    const mode = this._config.collapsed ?? CONFIG_DEFAULTS.collapsed;
    if (mode === "always") return true;
    if (mode === "never") return false;
    if (key in _globalCollapsed) return _globalCollapsed[key];
    return count === 0;
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
      (e) => e.device_id === this._config.device_id
        && e.entity_id.startsWith("sensor.")
        && e.translation_key === translationKey
    )?.entity_id;
  }

  /** @returns {{ monitored_images: number, updates_available: number }} */
  _resolveMetrics() {
    const deviceEntities = this._resolveDeviceEntities();
    const monitoredTotal = parseInt(this._hass.states[deviceEntities["monitored_images"]]?.state, 10) || 0;
    const updatesEntityId = this._resolveSensorEntityId("updates_available");
    const updatesAvailable = parseInt(this._hass.states[updatesEntityId]?.state, 10) || 0;
    return { monitored_images: monitoredTotal, updates_available: updatesAvailable };
  }

  /** @returns {string} */
  _resolveLastChecked() {
    const state = this._hass.states[this._resolveSensorEntityId("last_checked")]?.state;
    return state ? new Date(state).toLocaleString() : LABELS.lastCheckedUnknown;
  }

  _classifyImage(image) {
    const result = image?.result;
    if (result?.has_update === null || result?.has_update === undefined) return "unknown";
    if (result.has_update === false) return "up_to_date";
    const map = { major: "major_updates", minor: "minor_updates", patch: "patch_updates", other: "other_updates" };
    return map[result?.info?.version_update_type] ?? "other_updates";
  }

  _resolveSections() {
    const sectionMap = Object.fromEntries(DEFAULT_SECTIONS.map((s) => [s.key, s]));
    const deviceEntities = this._resolveDeviceEntities();
    const allImages = this._hass.states[deviceEntities["monitored_images"]]?.attributes?.images_list ?? [];
    const buckets = Object.fromEntries(ALL_SECTION_KEYS.map((k) => [k, []]));
    for (const image of allImages) buckets[this._classifyImage(image)].push(image);

    const excludedEntityId = deviceEntities["excluded_images"];
    if (excludedEntityId) {
      buckets["excluded_images"] = this._hass.states[excludedEntityId]?.attributes?.images_list ?? [];
    }

    const orderedKeys = this._config.order_sections ?? ALL_SECTION_KEYS;
    const remainingKeys = ALL_SECTION_KEYS.filter((k) => !orderedKeys.includes(k) && k !== "divider");
    const hiddenKeys = new Set(this._config.hide_sections ?? []);

    return [...orderedKeys, ...remainingKeys]
      .filter((key) => key === "divider" || (!hiddenKeys.has(key) && sectionMap[key]))
      .map((key) => key === "divider"
        ? { key: "divider", divider: true }
        : { ...sectionMap[key], images: buckets[key] ?? [] }
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
      <img src="${this._logoUrl}" alt="Logo Cup Component">
      <div class="hero-badge-wrapper">
        <span class="hero-badge monitored">
          <ha-icon icon="mdi:docker"></ha-icon>
          ${metrics.monitored_images} ${metrics.monitored_images > 1 ? LABELS.monitoredPlural : LABELS.monitoredSingular}
        </span>
        <span class="hero-badge ${metrics.updates_available > 0 ? "has-updates" : ""}">
          <ha-icon icon="${metrics.updates_available > 0 ? "mdi:arrow-up-circle" : "mdi:check-circle-outline"}"></ha-icon>
          ${metrics.updates_available > 0
        ? `${metrics.updates_available} ${metrics.updates_available > 1 ? LABELS.availablePlural : LABELS.availableSingular}`
        : LABELS.upToDate}
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
        <img src="${this._logoUrl}" alt="Logo Cup Component">
        <div class="hero-stats">
          <span class="hero-number">${metrics.monitored_images}<span class="hero-label">&nbsp;&nbsp;${metrics.monitored_images > 1 ? LABELS.upToDatePlural : LABELS.upToDateSingular}</span></span>
          <span class="hero-updates ${metrics.updates_available > 0 ? "has-updates" : ""}">
            <ha-icon icon="${metrics.updates_available > 0 ? "mdi:arrow-up-circle" : "mdi:check-circle-outline"}"></ha-icon>
            ${metrics.updates_available} ${metrics.updates_available > 1 ? LABELS.availablePlural : LABELS.availableSingular}
          </span>
        </div>
      </div>`;
  }

  // ─── Render ──────────────────────────────────────────────────────────────────

  _render() {
    if (!this._hass || !this._config) return;

    const sections = this._resolveSections();
    const metrics = this._resolveMetrics();
    const hasTitle = !!this._config.title;
    const showHero = !this._config.hide_hero;
    const showFooter = !this._config.hide_footer;
    const heroStyle = this._config.hero_style ?? CONFIG_DEFAULTS.hero_style;

    if (!this._initialized) {
      const heroPT = hasTitle ? "0px" : "12px";
      const heroPB = hasTitle ? "1px" : "6px";

      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          ha-card {
            padding-top: ${hasTitle ? "0" : (!showHero ? "16px" : "0")} !important;
            padding-bottom: ${showFooter ? "2px" : "16px"};
          }
          .card-header {
            color: var(--ha-card-header-color, --primary-text-color);
            font-family: var(--ha-card-header-font-family, inherit);
            font-size: var(--ha-card-header-font-size, 24px);
            font-weight: normal;
            margin-block-start: 0; margin-block-end: 0;
            letter-spacing: -0.012em; line-height: 48px;
            padding: 12px 16px 4px;
          }
          .card-header .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

          /* ── Hero: shared ── */
          .card-hero {
            display: flex; flex-direction: row; align-items: center;
            padding: ${heroPT} 16px ${heroPB};
          }

          /* ── Hero: badges style ── */
          .card-hero > img { width: 52px; height: 52px; object-fit: contain; flex-shrink: 0; }
          .hero-badge-wrapper { flex: 1; display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap; }
          .hero-badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 4px 12px 4px 8px; border-radius: 999px;
            font-size: 14px; font-weight: 600;
            background: rgba(67,160,71,0.15); color: var(--success-color, #43a047);
          }
          .hero-badge.monitored  { background: rgba(21,101,192,0.15); color: var(--primary-color, #1565c0); }
          .hero-badge.has-updates { background: rgba(219,68,55,0.15); color: var(--error-color, #db4437); }
          .hero-badge ha-icon { --mdc-icon-size: 20px; }

          /* ── Hero: classic style ── */
          .hero-counter { display: flex; align-items: center; gap: 12px; }
          .hero-counter > img { width: 52px; height: 52px; object-fit: contain; }
          .hero-stats { display: flex; flex-direction: column; gap: 4px; padding-left: 8px; }
          .hero-number {
            display: flex; align-items: baseline; white-space: nowrap;
            font-size: 32px; font-weight: 700; line-height: 1;
            color: var(--success-color, #43a047);
          }
          .hero-label { font-size: 16px; font-weight: 400; color: var(--success-color, #43a047); }
          .hero-updates {
            display: flex; align-items: center; gap: 4px;
            font-size: 13px; color: var(--secondary-text-color);
          }
          .hero-updates ha-icon { --mdc-icon-size: 14px; }
          .hero-updates.has-updates { color: var(--error-color, #db4437); }

          /* ── Sections ── */
          .sections-divider { border: none; border-top: 1px solid var(--divider-color); margin: 8px 16px; }
          .section { margin: 0 8px; }
          .section-title {
            display: flex; align-items: center; justify-content: space-between;
            font-size: var(--ha-font-size-s, 12px); font-weight: 500;
            text-transform: uppercase; letter-spacing: 0.1em;
            color: var(--secondary-text-color);
            padding: 8px 8px 4px; cursor: pointer; user-select: none;
          }
          .section-title:hover { color: var(--primary-text-color); }
          .section-title ha-icon { --mdc-icon-size: 16px; }
          .section-body { padding: 0 8px; }
          .image-row {
            display: flex; align-items: center; gap: 16px;
            min-height: 48px; padding: 8px;
            border-bottom: 1px solid var(--divider-color); box-sizing: border-box;
          }
          .image-row:last-child { border-bottom: none; }
          .image-icon-wrapper {
            display: flex; align-items: center; justify-content: center;
            width: 40px; height: 40px; flex-shrink: 0;
          }
          .image-icon-wrapper ha-icon { --mdc-icon-size: 24px; }
          .image-info {
            display: flex; flex-direction: column; justify-content: center;
            overflow: hidden; flex: 1;
          }
          .image-name {
            font-size: var(--ha-font-size-m, 14px); font-weight: 400;
            color: var(--primary-text-color);
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
          }
          .image-version {
            font-size: var(--ha-font-size-s, 12px); color: var(--secondary-text-color);
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
          }
          .image-version .version-arrow { margin: 0 4px; }
          .image-link { display: flex; align-items: center; color: var(--secondary-text-color); flex-shrink: 0; }
          .image-link:hover { color: var(--primary-text-color); }
          .image-link ha-icon { --mdc-icon-size: 18px; }
          .empty {
            font-size: var(--ha-font-size-m, 14px); color: var(--secondary-text-color);
            font-style: italic; padding: 2px 8px;
          }

          /* ── Footer ── */
          .card-footer {
            display: flex; align-items: center; justify-content: flex-end;
            padding: 0 16px 6px; margin-top: 4px;
          }
          .refresh-button {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 4px 8px; border-radius: 999px; border: none;
            background: none; cursor: pointer;
            color: var(--secondary-text-color); font-size: 10px;
          }
          .refresh-button:hover { color: var(--primary-text-color); background: var(--secondary-background-color); }
          .refresh-button ha-icon { --mdc-icon-size: 12px; }
        </style>
        <ha-card>
          ${hasTitle ? `<h1 class="card-header"><div class="name">${this._config.title}</div></h1><hr class="sections-divider">` : ""}
          ${showHero ? `
          <div class="card-hero">
            ${heroStyle === "classic" ? this._renderHeroClassic(metrics) : this._renderHeroBadges(metrics)}
          </div>
          <hr class="sections-divider">` : ""}
          ${sections.map((section) => {
        if (section.divider) return `<hr class="sections-divider">`;
        const collapsed = this._isCollapsed(section.key, section.images.length);
        return `
              <div class="section">
                <div class="section-title" data-key="${section.key}">
                  <span>${section.label} (<span class="section-count">${section.images.length}</span>)</span>
                  <ha-icon icon="${collapsed ? "mdi:chevron-down" : "mdi:chevron-up"}"></ha-icon>
                </div>
                <div class="section-body" data-key="${section.key}" style="${collapsed ? "display:none" : ""}">
                  ${this._renderImages(section)}
                </div>
              </div>`;
      }).join("")}
          ${showFooter ? `
          <div class="card-footer">
            <button class="refresh-button" id="refresh-btn">
              <ha-icon icon="mdi:clock-outline"></ha-icon> ${this._resolveLastChecked()}
            </button>
          </div>` : ""}
        </ha-card>
      `;

      this._initialized = true;
      this.shadowRoot.getElementById("refresh-btn")?.addEventListener("click", () => this._pressRefresh());

    } else {
      // Subsequent renders — patch only changing parts

      // Update hero metrics in place (same style, no structural change)
      if (heroStyle === "classic") {
        const heroNumber = this.shadowRoot.querySelector(".hero-number");
        if (heroNumber) heroNumber.innerHTML = `${metrics.monitored_images}<span class="hero-label">&nbsp;&nbsp;${metrics.monitored_images > 1 ? LABELS.upToDatePlural : LABELS.upToDateSingular}</span>`;

        const heroUpdates = this.shadowRoot.querySelector(".hero-updates");
        if (heroUpdates) {
          heroUpdates.className = `hero-updates${metrics.updates_available > 0 ? " has-updates" : ""}`;
          const updIcon = heroUpdates.querySelector("ha-icon");
          if (updIcon) updIcon.setAttribute("icon", metrics.updates_available > 0 ? "mdi:arrow-up-circle" : "mdi:check-circle-outline");
          heroUpdates.childNodes[heroUpdates.childNodes.length - 1].textContent =
            ` ${metrics.updates_available} ${metrics.updates_available > 1 ? LABELS.availablePlural : LABELS.availableSingular}`;
        }
      } else {
        const heroMonitored = this.shadowRoot.querySelector(".hero-badge.monitored");
        if (heroMonitored) heroMonitored.childNodes[heroMonitored.childNodes.length - 1].textContent =
          ` ${metrics.monitored_images} ${metrics.monitored_images > 1 ? LABELS.monitoredPlural : LABELS.monitoredSingular}`;

        const heroBadge = this.shadowRoot.querySelector(".hero-badge:not(.monitored)");
        if (heroBadge) {
          heroBadge.className = `hero-badge${metrics.updates_available > 0 ? " has-updates" : ""}`;
          const updIcon = heroBadge.querySelector("ha-icon");
          if (updIcon) updIcon.setAttribute("icon", metrics.updates_available > 0 ? "mdi:arrow-up-circle" : "mdi:check-circle-outline");
          heroBadge.childNodes[heroBadge.childNodes.length - 1].textContent =
            metrics.updates_available > 0
              ? ` ${metrics.updates_available} ${metrics.updates_available > 1 ? LABELS.availablePlural : LABELS.availableSingular}`
              : ` ${LABELS.upToDate}`;
        }
      }

      const footerBtn = this.shadowRoot.querySelector(".refresh-button");
      if (footerBtn) footerBtn.innerHTML = `<ha-icon icon="mdi:clock-outline"></ha-icon> ${this._resolveLastChecked()}`;

      sections.forEach((section) => {
        if (section.divider) return;
        const countEl = this.shadowRoot.querySelector(`.section-title[data-key="${section.key}"] .section-count`);
        if (countEl) countEl.textContent = section.images.length;
        const body = this.shadowRoot.querySelector(`.section-body[data-key="${section.key}"]`);
        if (body && body.style.display !== "none") body.innerHTML = this._renderImages(section);
      });
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
  _renderVersion(image) {
    const info = image?.result?.info;
    if (!info) return "";
    if (info.type === "digest") {
      const local = info.local_digests?.[0]?.substring(7, 19);
      const remote = info.remote_digest?.substring(7, 19);
      if (!local || !remote) return "";
      return `<span class="image-version">${local}<span class="version-arrow">→</span>${remote}</span>`;
    }
    const current = info.current_version;
    const next = info.new_version;
    if (!current && !next) return "";
    if (current && next && current !== next) return `<span class="image-version">${current}<span class="version-arrow">→</span>${next}</span>`;
    return `<span class="image-version">${current ?? next}</span>`;
  }

  /**
   * Render the image list HTML for a section.
   * @param {Object} section
   * @returns {string}
   */
  _renderImages(section) {
    if (section.images.length === 0) return `<div class="empty">${LABELS.noImages}</div>`;
    return section.images.map((image) => `
      <div class="image-row">
        <div class="image-icon-wrapper">
          <ha-icon icon="${section.icon}" style="color: ${section.color}"></ha-icon>
        </div>
        <div class="image-info">
          <span class="image-name">${image.reference ?? image.name ?? LABELS.imageUnknown}</span>
          ${this._renderVersion(image)}
        </div>
        ${image.url ? `<a class="image-link" href="${image.url}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:open-in-new"></ha-icon></a>` : ""}
      </div>
    `).join("");
  }
}

customElements.define("cup-images-card", CupImagesCard);

window.customCards = window.customCards ?? [];
window.customCards.push({
  type: "cup-images-card",
  name: "Cup Images Card",
  description: CARD_DESCRIPTION,
  preview: true,
});
