// palette.js
// Builds the left-side palette: entity types grouped, with existing named
// instances listed under each, plus a "+ New" action that opens a creation
// form derived from Model.TYPE_SCHEMAS.

const Palette = (() => {

  class PaletteUI {
    constructor(containerEl, model, assetLib, opts = {}) {
      this.container = containerEl;
      this.model = model;
      this.assetLib = assetLib;
      this.onSelectForPlacement = opts.onSelectForPlacement || (() => {});
      this.onEditRequest = opts.onEditRequest || (() => {});
      this.onCreateRequest = opts.onCreateRequest || (() => {});
      this.selectedName = null;
    }

    setModel(model) {
      this.model = model;
      this.render();
    }

    render() {
      this.container.innerHTML = '';
      const types = Object.keys(Model.TYPE_SCHEMAS);

      // Group entity names by type, including any types not in the schema
      // (so the level still works even if a future EntityFactory type appears).
      const byType = new Map();
      for (const t of types) byType.set(t, []);
      for (const [name, entry] of Object.entries(this.model.entities)) {
        if (!byType.has(entry.type)) byType.set(entry.type, []);
        byType.get(entry.type).push(name);
      }

      for (const [type, names] of byType.entries()) {
        const section = document.createElement('div');
        section.className = 'palette-section';

        const header = document.createElement('div');
        header.className = 'palette-section-header';
        header.innerHTML = `<span>${type}</span>`;
        const addBtn = document.createElement('button');
        addBtn.className = 'palette-add-btn';
        addBtn.textContent = '+ New';
        addBtn.title = `Create a new ${type} instance`;
        addBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.onCreateRequest(type);
        });
        header.appendChild(addBtn);
        section.appendChild(header);

        const list = document.createElement('div');
        list.className = 'palette-list';
        names.sort().forEach(name => {
          list.appendChild(this._buildEntityRow(name, type));
        });
        section.appendChild(list);

        this.container.appendChild(section);
      }
    }

    _buildEntityRow(name, type) {
      const row = document.createElement('div');
      row.className = 'palette-row';
      if (name === this.selectedName) row.classList.add('selected');

      const swatch = document.createElement('div');
      swatch.className = 'palette-swatch';
      this._loadSwatch(swatch, name, type);
      row.appendChild(swatch);

      const label = document.createElement('span');
      label.className = 'palette-label';
      label.textContent = name;
      row.appendChild(label);

      const editBtn = document.createElement('button');
      editBtn.className = 'palette-edit-btn';
      editBtn.textContent = '✎';
      editBtn.title = 'Edit instance data';
      editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.onEditRequest(name);
      });
      row.appendChild(editBtn);

      row.addEventListener('click', () => {
        this.selectedName = name;
        this.render();
        this.onSelectForPlacement(name);
      });

      return row;
    }

    async _loadSwatch(el, name, type) {
      const schema = Model.TYPE_SCHEMAS[type];
      const data = this.model.entityData(name);
      if (!schema || !data) return;
      try {
        let canvas = null;
        let wasRandomized = false;
        if (schema.addressing === 'terrain') {
          canvas = await this.assetLib.getTerrainTile(
            data.coord_x, data.coord_y, this.assetLib.terrainNativeTileSize || 48
          );
        } else if (schema.addressing === 'sprite' && data.sprite) {
          const preview = await this.assetLib.getSpritePreview(data.sprite);
          canvas = preview ? preview.canvas : null;
          wasRandomized = preview ? !!preview.wasRandomized : false;
        }
        if (canvas) {
          el.innerHTML = '';
          const img = document.createElement('img');
          img.src = canvas.toDataURL();
          el.appendChild(img);
          if (wasRandomized) {
            el.title = `"${data.sprite}" has no exact sprite folder — previewing a randomly-picked variant (the real game picks one at random too, every time).`;
            el.classList.add('randomized-swatch');
          }
        }
      } catch (e) {
        // Leave the default placeholder swatch on failure.
      }
    }
  }

  // ---- Entity edit/create form ----------------------------------------
  // Renders a form for a given type's schema, pre-filled with existing data
  // if editing, or sensible defaults if creating new. Calls onSave(data) or
  // onCancel() when done.

  function buildEntityForm(containerEl, assetLib, type, existingData, opts = {}) {
    containerEl.innerHTML = '';
    const schema = Model.TYPE_SCHEMAS[type];
    if (!schema) {
      const msg = document.createElement('p');
      msg.textContent = `No form schema for type "${type}". Edit raw JSON below.`;
      containerEl.appendChild(msg);
      return buildRawJSONForm(containerEl, existingData, opts);
    }

    const data = existingData ? JSON.parse(JSON.stringify(existingData)) : {};
    const fieldEls = {};

    for (const field of schema.fields) {
      const wrap = document.createElement('div');
      wrap.className = 'form-field';
      const label = document.createElement('label');
      label.textContent = field.label;
      wrap.appendChild(label);

      const value = getNestedValue(data, field.key);
      let input;

      if (field.kind === 'int') {
        input = document.createElement('input');
        input.type = 'number';
        input.value = value !== undefined && value !== null ? value : 0;
      } else if (field.kind === 'bool') {
        input = document.createElement('input');
        input.type = 'checkbox';
        input.checked = !!value;
      } else if (field.kind === 'text') {
        input = document.createElement('input');
        input.type = 'text';
        input.value = value !== undefined && value !== null ? value : '';
      } else if (field.kind === 'sprite') {
        input = document.createElement('select');
        const folders = assetLib.listSpriteFolders();
        const blank = document.createElement('option');
        blank.value = '';
        blank.textContent = '(none)';
        input.appendChild(blank);

        const hasExactMatch = value && folders.includes(value);
        if (value && !hasExactMatch) {
          // The saved value doesn't match an exact folder name. It may still
          // be a valid randomized base name (e.g. "UnarmedAgent" with no
          // exact folder, only UnarmedAgent0..7) — check before assuming
          // it's just stale data, and label it clearly either way so the
          // saved value is never silently dropped from the dropdown.
          const resolution = assetLib.resolveSpriteFolder ? assetLib.resolveSpriteFolder(value) : null;
          const opt = document.createElement('option');
          opt.value = value;
          opt.selected = true;
          if (resolution && resolution.candidates.length > 0) {
            opt.textContent = `${value} (random: ${resolution.candidates.join(', ')})`;
          } else {
            opt.textContent = `${value} (no matching folder found!)`;
          }
          input.appendChild(opt);
        }

        folders.forEach(f => {
          const opt = document.createElement('option');
          opt.value = f;
          opt.textContent = f;
          if (f === value) opt.selected = true;
          input.appendChild(opt);
        });
      } else if (field.kind === 'entity_ref') {
        input = document.createElement('select');
        const blank = document.createElement('option');
        blank.value = '';
        blank.textContent = '(none)';
        input.appendChild(blank);
        Object.keys(opts.model ? opts.model.entities : {}).sort().forEach(n => {
          const opt = document.createElement('option');
          opt.value = n;
          opt.textContent = n;
          if (n === value) opt.selected = true;
          input.appendChild(opt);
        });
      } else if (field.kind === 'path' || field.kind === 'path_nullable') {
        input = buildPathEditor(value, field.kind === 'path_nullable');
      } else {
        input = document.createElement('input');
        input.type = 'text';
        input.value = value !== undefined ? JSON.stringify(value) : '';
      }

      input.dataset.fieldKey = field.key;
      input.dataset.fieldKind = field.kind;
      wrap.appendChild(input);
      containerEl.appendChild(wrap);
      fieldEls[field.key] = input;
    }

    return {
      collect() {
        const out = existingData ? JSON.parse(JSON.stringify(existingData)) : {};
        for (const field of schema.fields) {
          const el = fieldEls[field.key];
          let value;
          if (field.kind === 'int') value = parseInt(el.value, 10) || 0;
          else if (field.kind === 'bool') value = el.checked;
          else if (field.kind === 'text' || field.kind === 'sprite' || field.kind === 'entity_ref') {
            value = el.value;
          } else if (field.kind === 'path' || field.kind === 'path_nullable') {
            value = readPathEditor(el, field.kind === 'path_nullable');
          } else {
            try { value = JSON.parse(el.value); } catch (e) { value = el.value; }
          }
          setNestedValue(out, field.key, value);
        }
        return out;
      },
    };
  }

  function getNestedValue(obj, dottedKey) {
    return dottedKey.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);
  }

  function setNestedValue(obj, dottedKey, value) {
    const parts = dottedKey.split('.');
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof cur[parts[i]] !== 'object' || cur[parts[i]] === null) {
        cur[parts[i]] = {};
      }
      cur = cur[parts[i]];
    }
    cur[parts[parts.length - 1]] = value;
  }

  // Simple repeatable [dx, dy] row editor for path arrays. Stores its state
  // in a hidden textarea-like container so collect() can read it back; null
  // path (no patrol) is supported via a checkbox when nullable.
  function buildPathEditor(value, nullable) {
    const container = document.createElement('div');
    container.className = 'path-editor';

    let nullToggle = null;
    if (nullable) {
      nullToggle = document.createElement('label');
      nullToggle.className = 'path-null-toggle';
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = value === null || value === undefined;
      cb.addEventListener('change', () => {
        rowsContainer.style.display = cb.checked ? 'none' : '';
      });
      nullToggle.appendChild(cb);
      nullToggle.appendChild(document.createTextNode(' No patrol (static)'));
      container.appendChild(nullToggle);
      container._nullCheckbox = cb;
    }

    const rowsContainer = document.createElement('div');
    rowsContainer.className = 'path-rows';
    if (nullable && (value === null || value === undefined)) {
      rowsContainer.style.display = 'none';
    }
    container.appendChild(rowsContainer);
    container._rowsContainer = rowsContainer;

    const initial = Array.isArray(value) ? value : [];
    initial.forEach(pair => addPathRow(rowsContainer, pair[0], pair[1]));

    const addBtn = document.createElement('button');
    addBtn.type = 'button';
    addBtn.textContent = '+ waypoint';
    addBtn.className = 'path-add-btn';
    addBtn.addEventListener('click', () => addPathRow(rowsContainer, 0, 0));
    container.appendChild(addBtn);

    const hint = document.createElement('div');
    hint.className = 'path-hint';
    hint.textContent = 'Tip: select this entity then Shift+click the grid to add waypoints visually.';
    container.appendChild(hint);

    return container;
  }

  function addPathRow(rowsContainer, dx, dy) {
    const row = document.createElement('div');
    row.className = 'path-row';
    const dxInput = document.createElement('input');
    dxInput.type = 'number';
    dxInput.value = dx;
    dxInput.className = 'path-dx';
    const dyInput = document.createElement('input');
    dyInput.type = 'number';
    dyInput.value = dy;
    dyInput.className = 'path-dy';
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', () => row.remove());
    row.appendChild(document.createTextNode('dx:'));
    row.appendChild(dxInput);
    row.appendChild(document.createTextNode('dy:'));
    row.appendChild(dyInput);
    row.appendChild(removeBtn);
    rowsContainer.appendChild(row);
  }

  function readPathEditor(container, nullable) {
    if (nullable && container._nullCheckbox && container._nullCheckbox.checked) {
      return null;
    }
    const rows = container._rowsContainer.querySelectorAll('.path-row');
    const out = [];
    rows.forEach(row => {
      const dx = parseInt(row.querySelector('.path-dx').value, 10) || 0;
      const dy = parseInt(row.querySelector('.path-dy').value, 10) || 0;
      out.push([dx, dy]);
    });
    return out;
  }

  function buildRawJSONForm(containerEl, existingData, opts) {
    const textarea = document.createElement('textarea');
    textarea.className = 'raw-json-editor';
    textarea.value = JSON.stringify(existingData || {}, null, 2);
    containerEl.appendChild(textarea);
    return {
      collect() {
        try {
          return JSON.parse(textarea.value);
        } catch (e) {
          alert('Invalid JSON: ' + e.message);
          throw e;
        }
      },
    };
  }

  return { PaletteUI, buildEntityForm };
})();
