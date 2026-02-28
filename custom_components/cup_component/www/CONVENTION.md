# Cup Images Card — Developer Convention

## Overview

This file documents conventions for working on the `cup-images-card.js` custom Lovelace card
for the Home Assistant `cup_component` integration.

---

## File

```
custom_components/cup_component/www/cup-images-card.js
```

Home Assistant serves this file via a registered static HTTP route (see [Deployment](#deployment)).
After every modification, a **hard refresh** (`Ctrl+Shift+R`) is required in the browser to bypass the JS cache.

To verify the active version served by HA:

```javascript
fetch('/cup_component/cup-images-card.js?v='+Date.now())
.then(r=>r.text())
.then(t=>console.log(t.match(/const CARD_VERSION = "(\w+)"/)?.[1]))
```

---

## Versioning

Versions are named after **French cities**, in chronological order of sessions.  
Always bump `CARD_VERSION` at the end of each working session.

```javascript
const CARD_VERSION = "Le Mans"; // current
```

---

## Architecture

### Editor (`CupImagesCardEditor`)

Registered **before** `CupImagesCard` (required by HA).

Uses a **build-once pattern** to avoid DOM rebuild on every config change:

| Method | Role |
|---|---|
| `_buildDOM()` | Called once — builds static HTML structure, assigns selector schemas, calls `_updateValues()` and `_attachListeners()` |
| `_updateValues()` | Called on every config change — patches dynamic values without rebuilding DOM |
| `_attachListeners()` | Called once — attaches all event listeners using delegation where possible |

**Key rule:** HA passes a frozen config object to `setConfig()`. Always shallow-copy it:
```javascript
this._config = { ...config };
```

**Title field:** dispatches config directly via `_fireConfig()` (no `_updateValues()` call) to preserve input focus.

### Card (`CupImagesCard`)

Uses an **incremental render pattern**:

| Phase | Trigger | Action |
|---|---|---|
| First render | `_initialized === false` | Full `shadowRoot.innerHTML` rebuild |
| Subsequent renders | `_initialized === true` | Patch only changed DOM nodes |

Device entities are resolved once and cached in `_deviceEntities` until `setConfig()` is called again.

---

## Config Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `device_id` | `string` | — | **Required.** Device ID from the `cup_component` integration |
| `title` | `string` | — | Card title. Omit to hide the header entirely |
| `hero_style` | `"badges"` \| `"classic"` | `"badges"` | Hero block display style |
| `collapsed` | `"always"` \| `"never"` \| `"if_empty"` | `"if_empty"` | Default collapse behaviour for sections |
| `hide_hero` | `boolean` | `false` | Hide the hero metrics block |
| `hide_footer` | `boolean` | `false` | Hide the last checked footer |
| `hide_sections` | `string[]` | `[]` | Section keys to hide |
| `order_sections` | `string[]` | — | Section keys defining display order |
| `_preview` | `boolean` | — | Internal stub flag for card picker preview. Never persisted |

---

## Section Keys

```
major_updates, minor_updates, patch_updates, other_updates,
up_to_date, unknown, excluded_images
```

The special key `divider` can be used in `order_sections` to insert a visual separator.

---

## Hero Styles

### `badges` (default)
Logo on the left, two pill badges centered:
- Blue badge: Docker icon + monitored image count
- Green/Red badge: status icon + update count or "Up to date"

### `classic`
Logo + large green number (monitored images) + smaller update count line below.

---

## Labels

All user-facing strings are centralised in the `LABELS` constant.  
**Never hardcode strings** in HTML templates or JS logic.  
This makes future internationalisation straightforward: only `LABELS` needs to be updated.

```javascript
const LABELS = {
  // Card — hero
  monitoredSingular, monitoredPlural,
  upToDateSingular, upToDatePlural,
  availableSingular, availablePlural,
  upToDate,
  // Card — sections
  noImages, imageUnknown, lastCheckedUnknown,
  // Editor
  editorCollapsedBehaviour, editorHeroStyle,
  editorHideSections, editorHideHeroBlock, editorHideFooter,
  editorSectionOrder, editorAddButton,
};
```

---

## Editor Checkboxes — Important Rule

The `#hide-hero-cb` and `#hide-footer-cb` checkboxes do **not** have a `data-key` attribute.  
The section keys checkboxes **do** have `data-key`.

Always scope selectors accordingly to avoid cross-contamination:

```javascript
// Correct — targets section keys only
root.querySelectorAll("input[type=checkbox][data-key]")

// Wrong — also matches hide-hero-cb and hide-footer-cb
root.querySelectorAll(".checkbox-row input")
```

---

## Deployment

The card is automatically deployed when the integration is installed. No manual resource setup is required.

### How it works

Two complementary mechanisms are used:

| Mechanism | Role |
|---|---|
| `frontend_extra_module_url` in `manifest.json` | Loads the JS globally at frontend boot — defines the custom element in the browser |
| `JSModuleRegistration` in `frontend/__init__.py` | Registers the resource in Lovelace (storage mode) — makes the card available in the card picker |

> **YAML mode:** If Lovelace is configured in YAML mode, automatic resource registration is skipped. The resource must be declared manually in the YAML configuration.

### Static HTTP route

Registered once per HA session in `async_setup` via `JSModuleRegistration._async_register_path()`:

```
URL:    /cup_component/cup-images-card.js
Serves: custom_components/cup_component/www/cup-images-card.js
```

> **Note:** The static HTTP path cannot be deregistered at runtime — HA provides no public API for this. After a complete removal of the integration, the path remains active until the next HA restart.

### Versioning

The Lovelace resource URL is versioned using `INTEGRATION_VERSION` from `const.py`, which is read from `manifest.json` at module load time:

```
/cup_component/cup-images-card.js?v=1.2.3
```

If the version changes between HA restarts, `JSModuleRegistration` automatically updates the resource URL in Lovelace storage.

In dev environments, if `manifest.json` has no version field, `INTEGRATION_VERSION` falls back to a Unix timestamp — this guarantees the resource is always refreshed on every restart.

### Uninstallation

When the integration is permanently removed, `async_remove_entry` calls `JSModuleRegistration.async_unregister()` to delete the Lovelace resource from storage. The static HTTP path is not removed (see note above).

### Integration files involved

```
custom_components/cup_component/
├── manifest.json              # frontend_extra_module_url + dependencies (frontend, http)
├── __init__.py                # async_setup() → JSModuleRegistration, async_remove_entry() → async_unregister()
├── const.py                   # URL_BASE, LOVELACE_CARD_JS, LOVELACE_CARD_NAME, LOVELACE_MODULE_URL, INTEGRATION_VERSION
├── frontend/
│   └── __init__.py            # JSModuleRegistration class
└── www/
    └── cup-images-card.js     # The card JS file
```

### `manifest.json` requirements

```json
{
  "dependencies": ["frontend", "http"],
  "frontend_extra_module_url": "/cup_component/cup-images-card.js"
}
```

---

## Local Filesystem Access

Always use `docker_filesystem` tools to read/write this file. Never use `bash_tool`.

Allowed directory: `/workspaces/ha-cup-component/custom_components`
