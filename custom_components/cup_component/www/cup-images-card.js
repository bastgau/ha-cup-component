/**
 * Cup Images Card
 * Custom card for the HA Cup Component integration.
 * Displays all monitored images grouped by update type.
 *
 * Config options:
 *   entity          (required) - Any sensor entity from the cup_component integration
 *   title           (optional) - Card title. Omit to hide the header entirely.
 *   hide_sections   (optional) - Array of section keys to hide (e.g. ["excluded_images", "unknown"])
 *   order_sections  (optional) - Array of section keys defining display order. Unlisted sections appear at the end.
 *   collapsed       (optional) - "always" | "never" | "if_empty" (default)
 *   hide_hero       (optional) - true to hide the hero metrics block
 *   hide_footer     (optional) - true to hide the last checked footer
 */

// ─── Static labels & assets ────────────────────────────────────────────────
const CARD_LOGO_URL = "https://brands.home-assistant.io/_/cup_component/dark_icon@2x.png";
const CARD_DESCRIPTION = "Displays all monitored Docker images grouped by update type.";

const LABELS = {
  // Hero
  upToDateSingular:    "up-to-date image",
  upToDatePlural:      "up-to-date images",
  availableSingular:   "image available",
  availablePlural:     "images available",
  // Sections
  noImages:            "No images",
  imageUnknown:        "Unknown",
  // Footer
  lastCheckedUnknown:  "Unknown",
};

const DEFAULT_SECTIONS = [
  { key: "major_updates",   label: "Major Updates", icon: "mdi:alert-circle",         color: "#db4437" },
  { key: "minor_updates",   label: "Minor Updates", icon: "mdi:arrow-up-circle",       color: "#f4a623" },
  { key: "patch_updates",   label: "Patch Updates", icon: "mdi:arrow-up-circle-outline", color: "#4a90d9" },
  { key: "other_updates",   label: "Other Updates", icon: "mdi:sync-circle",            color: "#9b59b6" },
  { key: "up_to_date",      label: "Up to Date",    icon: "mdi:check-circle-outline",  color: "#43a047" },
  { key: "unknown",         label: "Unknown",       icon: "mdi:help-circle-outline",   color: "#9e9e9e" },
  { key: "excluded_images", label: "Excluded",      icon: "mdi:minus-circle-outline",  color: "#757575" },
];

const ALL_SECTION_KEYS = DEFAULT_SECTIONS.map((s) => s.key);

// Global collapsed state — persists across HA re-instantiations
const _globalCollapsed = {};

class CupImagesCard extends HTMLElement {

  constructor() {
    super();
    this._deviceEntities = null;
    this._initialized = false;

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
    if (!config.entity) throw new Error("Please define a sensor entity.");
    this._config = config;
    this._deviceEntities = null;
    this._initialized = false;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return 3; }

  // ─── Helpers ────────────────────────────────────────────────────────────────

  _isCollapsed(key, count) {
    const mode = this._config.collapsed ?? "if_empty";
    if (mode === "always") return true;
    if (mode === "never") return false;
    if (key in _globalCollapsed) return _globalCollapsed[key];
    return count === 0;
  }

  /**
   * Resolve all entities belonging to the same device as the configured entity.
   * Results are cached until setConfig() is called again.
   * @returns {Object} Map of translation_key -> entity_id
   */
  _resolveDeviceEntities() {
    if (this._deviceEntities) return this._deviceEntities;
    const entityEntry = Object.values(this._hass.entities ?? {}).find(
      (e) => e.entity_id === this._config.entity
    );
    if (!entityEntry?.device_id) return {};
    const result = {};
    for (const entry of Object.values(this._hass.entities ?? {})) {
      if (entry.device_id === entityEntry.device_id && entry.translation_key) {
        result[entry.translation_key] = entry.entity_id;
      }
    }
    this._deviceEntities = result;
    return result;
  }

  /**
   * Find the entity_id of a sensor (not binary_sensor) by translation_key on the same device.
   * @param {string} translationKey
   * @returns {string|undefined}
   */
  _resolveSensorEntityId(translationKey) {
    const deviceId = Object.values(this._hass.entities ?? {}).find(
      (e) => e.entity_id === this._config.entity
    )?.device_id;
    return Object.values(this._hass.entities ?? {}).find(
      (e) => e.entity_id.startsWith("sensor.") && e.translation_key === translationKey && e.device_id === deviceId
    )?.entity_id;
  }

  /**
   * Resolve current metrics from device entities.
   * @returns {{ monitored_images: number, updates_available: number, up_to_date: number }}
   */
  _resolveMetrics() {
    const deviceEntities = this._resolveDeviceEntities();
    const monitoredEntityId = deviceEntities["monitored_images"] ?? this._config.entity;
    const monitoredTotal = parseInt(this._hass.states[monitoredEntityId]?.state, 10) || 0;
    // Explicitly target the sensor (not the binary_sensor) for updates_available
    const updatesEntityId = this._resolveSensorEntityId("updates_available");
    const updatesAvailable = parseInt(this._hass.states[updatesEntityId]?.state, 10) || 0;
    return {
      monitored_images: monitoredTotal,
      updates_available: updatesAvailable,
      up_to_date: monitoredTotal - updatesAvailable,
    };
  }

  /**
   * Resolve the last checked datetime string for the footer.
   * @returns {string}
   */
  _resolveLastChecked() {
    const entityId = this._resolveSensorEntityId("last_checked");
    const state = this._hass.states[entityId]?.state;
    return state ? new Date(state).toLocaleString() : "Unknown";
  }

  _classifyImage(image) {
    const result = image?.result;
    if (result?.has_update === null || result?.has_update === undefined) return "unknown";
    if (result.has_update === false) return "up_to_date";
    const mapping = { major: "major_updates", minor: "minor_updates", patch: "patch_updates", other: "other_updates" };
    return mapping[result?.info?.version_update_type] ?? "other_updates";
  }

  _resolveSections() {
    const sectionMap = Object.fromEntries(DEFAULT_SECTIONS.map((s) => [s.key, s]));
    const deviceEntities = this._resolveDeviceEntities();

    const monitoredEntityId = deviceEntities["monitored_images"] ?? this._config.entity;
    const allImages = this._hass.states[monitoredEntityId]?.attributes?.images_list ?? [];
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
      .map((key) => key === "divider" ? { key: "divider", divider: true } : { ...sectionMap[key], images: buckets[key] ?? [] });
  }

  // ─── Render ─────────────────────────────────────────────────────────────────

  /**
   * Render the card.
   * On first render: write full HTML structure.
   * On subsequent renders: update only counters and image lists in place,
   * preserving collapsed state managed directly in the DOM.
   */
  _render() {
    if (!this._hass || !this._config) return;

    const sections  = this._resolveSections();
    const metrics   = this._resolveMetrics();
    const hasTitle  = this._config.title !== undefined && this._config.title !== null;
    const showHero  = !this._config.hide_hero;
    const showFooter = !this._config.hide_footer;

    if (!this._initialized) {
      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          ha-card { padding-bottom: ${showFooter ? "2px" : "16px"}; padding-top: ${hasTitle ? "0px" : (!showHero ? "16px" : "0px")} !important;}
          .card-header {
            color: var(--ha-card-header-color, --primary-text-color);
            font-family: var(--ha-card-header-font-family, inherit);
            font-size: var(--ha-card-header-font-size, 24px);
            font-weight: normal;
            margin-block-start: 0;
            margin-block-end: 0;
            letter-spacing: -0.012em;
            line-height: 48px;
            padding: 12px 16px 4px;
          }
          .card-header .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

          /* Hero block — metrics */
          .card-hero {
            display: flex;
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
            padding: ${hasTitle ? "0px" : "12px"} 16px ${hasTitle ? "1px" : "6px"};
          }
          .hero-left {
            display: flex;
            flex-direction: column;
            gap: 8px;
          }
          .hero-counter {
            display: flex;
            align-items: center;
            gap: 12px;
          }
          .hero-counter > img {
            width: 52px;
            height: 52px;
            object-fit: contain;
          }
          .hero-stats {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding-left: 8px;
          }
          .hero-number {
            display: flex;
            align-items: baseline;
            white-space: nowrap;
            font-size: 32px;
            font-weight: 700;
            line-height: 1;
            color: var(--success-color, #43a047);
          }
          .hero-label {
            font-size: 16px;
            font-weight: 400;
            color: var(--success-color, #43a047);
          }
          .hero-updates {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 13px;
            color: var(--secondary-text-color);
          }
          .hero-updates ha-icon { --mdc-icon-size: 14px; }
          .hero-updates.has-updates { color: var(--error-color, #db4437); }
          .refresh-button {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 8px;
            border-radius: 999px;
            border: none;
            background: none;
            cursor: pointer;
            color: var(--secondary-text-color);
            font-size: 10px;
          }
          .refresh-button:hover { color: var(--primary-text-color); background: var(--secondary-background-color); }
          .refresh-button ha-icon { --mdc-icon-size: 12px; }

          /* Divider between hero/header and sections */
          .sections-divider { border: none; border-top: 1px solid var(--divider-color); margin: 8px 16px; }

          /* Section */
          .section { margin: 0 8px; }
          .section-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: var(--ha-font-size-s, 12px);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--secondary-text-color);
            padding: 8px 8px 4px;
            cursor: pointer;
            user-select: none;
          }
          .section-title:hover { color: var(--primary-text-color); }
          .section-title ha-icon { --mdc-icon-size: 16px; }
          .section-body { padding: 0 8px; }

          /* Image row — follows HA entity-row layout */
          .image-row {
            display: flex;
            align-items: center;
            gap: 16px;
            min-height: 48px;
            padding: 8px;
            border-bottom: 1px solid var(--divider-color);
            box-sizing: border-box;
          }
          .image-row:last-child { border-bottom: none; }
          .image-icon-wrapper {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            flex-shrink: 0;
          }
          .image-icon-wrapper ha-icon { --mdc-icon-size: 24px; }
          .image-info {
            display: flex;
            flex-direction: column;
            justify-content: center;
            overflow: hidden;
            flex: 1;
          }
          .image-name {
            font-size: var(--ha-font-size-m, 14px);
            font-weight: 400;
            color: var(--primary-text-color);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .image-version {
            font-size: var(--ha-font-size-s, 12px);
            color: var(--secondary-text-color);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .image-version .version-arrow { margin: 0 4px; }
          .image-link {
            display: flex;
            align-items: center;
            color: var(--secondary-text-color);
            flex-shrink: 0;
          }
          .image-link:hover { color: var(--primary-text-color); }
          .image-link ha-icon { --mdc-icon-size: 18px; }
          .empty {
            font-size: var(--ha-font-size-m, 14px);
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 2px 8px;
          }

          /* Footer — clickable last checked datetime (triggers refresh) */
          .card-footer {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding: 0 16px 6px;
            margin-top: 4px;
          }
        </style>
        <ha-card>
          ${hasTitle ? `<h1 class="card-header"><div class="name">${this._config.title}</div></h1><hr class="sections-divider">` : ""}
          ${showHero ? `
          <div class="card-hero">
            <div class="hero-left">
              <div class="hero-counter">
                <img src="${CARD_LOGO_URL}" alt="cup">
                <div class="hero-stats">
                  <span class="hero-number">${metrics.monitored_images}<span class="hero-label">&nbsp;&nbsp;${metrics.monitored_images > 1 ? LABELS.upToDatePlural : LABELS.upToDateSingular}</span></span>
                  <span class="hero-updates ${metrics.updates_available > 0 ? "has-updates" : ""}">
                    <ha-icon icon="${metrics.updates_available > 0 ? "mdi:arrow-up-circle" : "mdi:check-circle-outline"}"></ha-icon>
                    ${metrics.updates_available} ${metrics.updates_available > 1 ? LABELS.availablePlural : LABELS.availableSingular}
                  </span>
                </div>
              </div>
            </div>
          </div>` : ""}
          ${showHero ? `<hr class="sections-divider">` : ""}
          ${sections.map((section) => {
            if (section.divider) return `<hr class="sections-divider">`;
            const collapsed = this._isCollapsed(section.key, section.images.length);
            return `
              <div class="section">
                <div class="section-title" data-key="${section.key}">
                  <span class="section-label">${section.label} (<span class="section-count">${section.images.length}</span>)</span>
                  <ha-icon icon="${collapsed ? "mdi:chevron-down" : "mdi:chevron-up"}"></ha-icon>
                </div>
                <div class="section-body" data-key="${section.key}" style="${collapsed ? "display:none" : ""}">
                  ${this._renderImages(section)}
                </div>
              </div>
            `;
          }).join("")}
          ${showFooter ? `<div class="card-footer"><button class="refresh-button" id="refresh-btn"><ha-icon icon="mdi:clock-outline" style="--mdc-icon-size: 12px"></ha-icon> ${this._resolveLastChecked()}</button></div>` : ""}
        </ha-card>
      `;
      this._initialized = true;

      // Bind refresh button to the action_refresh button entity
      const refreshBtn = this.shadowRoot.getElementById("refresh-btn");
      if (refreshBtn) {
        refreshBtn.addEventListener("click", () => this._pressRefresh());
      }
    } else {
      // Subsequent renders: update metrics, footer and image lists in place
      const heroNumber = this.shadowRoot.querySelector(".hero-number");
      if (heroNumber) heroNumber.innerHTML = `${metrics.monitored_images}<span class="hero-label">&nbsp;&nbsp;${metrics.monitored_images > 1 ? LABELS.upToDatePlural : LABELS.upToDateSingular}</span>`;

      const heroUpdates = this.shadowRoot.querySelector(".hero-updates");
      if (heroUpdates) {
        heroUpdates.className = `hero-updates${metrics.updates_available > 0 ? " has-updates" : ""}`;
        const updIcon = heroUpdates.querySelector("ha-icon");
        if (updIcon) updIcon.setAttribute("icon", metrics.updates_available > 0 ? "mdi:arrow-up-circle" : "mdi:check-circle-outline");
        heroUpdates.childNodes[heroUpdates.childNodes.length - 1].textContent = ` ${metrics.updates_available} ${metrics.updates_available > 1 ? LABELS.availablePlural : LABELS.availableSingular}`;
      }

      const footerEl = this.shadowRoot.querySelector(".refresh-button");
      if (footerEl) footerEl.innerHTML = `<ha-icon icon="mdi:clock-outline" style="--mdc-icon-size: 12px"></ha-icon> ${this._resolveLastChecked()}`;

      sections.forEach((section) => {
        if (section.divider) return;
        const countEl = this.shadowRoot.querySelector(`.section-title[data-key="${section.key}"] .section-count`);
        if (countEl) countEl.textContent = section.images.length;

        const body = this.shadowRoot.querySelector(`.section-body[data-key="${section.key}"]`);
        if (body && body.style.display !== "none") {
          body.innerHTML = this._renderImages(section);
        }
      });
    }
  }

  // ─── Actions ────────────────────────────────────────────────────────────────

  /**
   * Press the action_refresh button entity via the HA button.press service.
   */
  async _pressRefresh() {
    const deviceEntities = this._resolveDeviceEntities();
    const buttonEntityId = deviceEntities["action_refresh"];
    if (!buttonEntityId) return;
    await this._hass.callService("button", "press", { entity_id: buttonEntityId });
  }

  // ─── Template helpers ────────────────────────────────────────────────────────

  /**
   * Render the version line for an image (current -> new).
   * Returns an empty string if no version info is available.
   * @param {Object} image - Image object from images_list.
   * @returns {string} HTML string.
   */
  _renderVersion(image) {
    const info = image?.result?.info;
    if (!info) return "";
    // For digest-type updates, display truncated local and remote digests
    if (info.type === "digest") {
      const local = info.local_digests?.[0]?.substring(7, 19);
      const remote = info.remote_digest?.substring(7, 19);
      if (!local || !remote) return "";
      return `<span class="image-version">${local}<span class="version-arrow">→</span>${remote}</span>`;
    }
    // For semver-type updates, display current and new version
    const current = info.current_version;
    const next = info.new_version;
    if (!current && !next) return "";
    if (current && next && current !== next) {
      return `<span class="image-version">${current}<span class="version-arrow">→</span>${next}</span>`;
    }
    return `<span class="image-version">${current ?? next}</span>`;
  }

  /**
   * Render the image list HTML for a section.
   * @param {Object} section - Section with images array.
   * @returns {string} HTML string.
   */
  _renderImages(section) {
    if (section.images.length === 0) {
      return `<div class="empty">${LABELS.noImages}</div>`;
    }
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
});
