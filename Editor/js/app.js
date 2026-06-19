// app.js
// Top-level wiring for the Agent Glitch level editor. Connects file I/O,
// the level model, the asset library, the canvas, the palette, and the
// layer panel into a working application.

(function () {
  const state = {
    projectIO: null,
    assetLib: new Sprites.AssetLibrary(),
    model: null,
    currentLevelName: null,
    gridEditor: null,
    paletteUI: null,
    layerPanel: null,
    modal: null,
  };

  function el(id) { return document.getElementById(id); }

  function setStatus(msg, isError = false) {
    const statusEl = el('status-bar');
    statusEl.textContent = msg;
    statusEl.classList.toggle('error', isError);
  }

  function markDirty(dirty) {
    state.dirty = dirty;
    el('save-btn').disabled = !state.currentLevelName;
    el('save-btn').classList.toggle('dirty', dirty);
    const title = document.title.replace(/^\* /, '');
    document.title = dirty ? `* ${title}` : title;
  }

  // ---- Project open / level load / save / create -----------------------

  async function handleOpenProject() {
    try {
      Sprites.AssetLibrary; // no-op reference to ensure module loaded
      setStatus('Opening project folder…');
      state.projectIO = await FSIO.ProjectIO.open();
      setStatus('Indexing Assets folder (this can take a moment)…');
      await state.assetLib.loadFromDirectoryHandle(state.projectIO.assetsHandle);
      const blockSizeInput = el('block-size-input');
      state.assetLib.blockSize = parseInt(blockSizeInput.value, 10) || 96;

      const levels = await state.projectIO.listLevels();
      populateLevelDropdown(levels);
      setStatus(`Project loaded. Found ${levels.length} level(s) and ${state.assetLib.listSpriteFolders().length} sprite folders.`);
      el('level-select-row').style.display = '';
      el('new-level-btn').style.display = '';
    } catch (e) {
      console.error(e);
      setStatus(`Failed to open project: ${e.message}`, true);
    }
  }

  function populateLevelDropdown(levels) {
    const sel = el('level-select');
    sel.innerHTML = '';
    const blank = document.createElement('option');
    blank.value = '';
    blank.textContent = '— choose a level —';
    sel.appendChild(blank);
    levels.forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      sel.appendChild(opt);
    });
  }

  async function handleLoadLevel(name) {
    if (!name) return;
    try {
      setStatus(`Loading ${name}…`);
      const { aglText, agdText } = await state.projectIO.loadLevel(name);
      state.model = Model.LevelModel.fromFiles(aglText, agdText);
      state.currentLevelName = name;
      wireUpEditorsForNewModel();
      markDirty(false);
      setStatus(`Loaded ${name}: ${state.model.rows}×${state.model.cols} grid, ${Object.keys(state.model.entities).length} entity types.`);
    } catch (e) {
      console.error(e);
      setStatus(`Failed to load level: ${e.message}`, true);
    }
  }

  async function handleSaveLevel() {
    if (!state.model || !state.currentLevelName) return;
    try {
      setStatus('Saving…');
      const aglText = state.model.toAGL();
      const agdText = state.model.toAGD();
      await state.projectIO.saveLevel(state.currentLevelName, aglText, agdText);
      markDirty(false);
      setStatus(`Saved ${state.currentLevelName}.agl and .agd.`);
    } catch (e) {
      console.error(e);
      setStatus(`Failed to save: ${e.message}`, true);
    }
  }

  async function handleCreateLevel() {
    if (!state.projectIO) {
      setStatus('Open a project folder first.', true);
      return;
    }

    const modal = el('modal');
    const body = el('modal-body');
    body.innerHTML = '';
    el('modal-title').textContent = 'New Level';

    const nameWrap = document.createElement('div');
    nameWrap.className = 'form-field';
    const nameLabel = document.createElement('label');
    nameLabel.textContent = 'Level name (no extension, e.g. "level2a")';
    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.value = '';
    nameWrap.appendChild(nameLabel);
    nameWrap.appendChild(nameInput);
    body.appendChild(nameWrap);

    const rowsWrap = document.createElement('div');
    rowsWrap.className = 'form-field';
    const rowsLabel = document.createElement('label');
    rowsLabel.textContent = 'Rows';
    const rowsInput = document.createElement('input');
    rowsInput.type = 'number';
    rowsInput.value = 30;
    rowsInput.min = 1;
    rowsWrap.appendChild(rowsLabel);
    rowsWrap.appendChild(rowsInput);
    body.appendChild(rowsWrap);

    const colsWrap = document.createElement('div');
    colsWrap.className = 'form-field';
    const colsLabel = document.createElement('label');
    colsLabel.textContent = 'Columns';
    const colsInput = document.createElement('input');
    colsInput.type = 'number';
    colsInput.value = 28;
    colsInput.min = 1;
    colsWrap.appendChild(colsLabel);
    colsWrap.appendChild(colsInput);
    body.appendChild(colsWrap);

    const hint = document.createElement('p');
    hint.className = 'modal-hint';
    hint.textContent = 'You can resize the grid later from the Grid menu; these are just a starting size.';
    body.appendChild(hint);

    showModal(() => {
      const name = nameInput.value.trim();
      if (!name) { alert('Please enter a level name.'); return false; }
      if (!/^[a-zA-Z0-9_]+$/.test(name)) {
        alert('Level name should only contain letters, numbers, and underscores (it becomes the .agl/.agd filename).');
        return false;
      }
      const rows = parseInt(rowsInput.value, 10) || 30;
      const cols = parseInt(colsInput.value, 10) || 28;

      createNewLevelAsync(name, rows, cols);
      return true;
    });
  }

  async function createNewLevelAsync(name, rows, cols) {
    try {
      const exists = await state.projectIO.levelExists(name);
      if (exists) {
        alert(`"${name}" already exists in Levels and/or GameObjects. Pick a different name, or load it from the dropdown instead.`);
        return;
      }
      state.model = Model.LevelModel.blank(rows, cols);
      state.currentLevelName = name;
      wireUpEditorsForNewModel();
      markDirty(true); // new level isn't saved to disk yet — Save is required.

      // Refresh the dropdown so the new level shows up immediately and is
      // selected, without needing to reopen the project.
      const levels = await state.projectIO.listLevels();
      const allNames = levels.includes(name) ? levels : [...levels, name].sort();
      populateLevelDropdown(allNames);
      el('level-select').value = name;

      setStatus(`Created new ${rows}×${cols} level "${name}". Click Save to write it to disk.`);
    } catch (e) {
      console.error(e);
      setStatus(`Failed to create level: ${e.message}`, true);
    }
  }

  function wireUpEditorsForNewModel() {
    if (!state.gridEditor) {
      state.gridEditor = new GridCanvas.Editor(el('grid-canvas'), state.model, state.assetLib, { tileSize: 32 });
      state.gridEditor.onModelChanged = () => markDirty(true);
      state.gridEditor.onCellClick = (r, c) => {
        state.layerPanel.setCell([r, c]);
      };
      state.gridEditor.onPathEdited = () => markDirty(true);
      state.gridEditor.onTriggerResized = () => markDirty(true);
    } else {
      state.gridEditor.setModel(state.model);
    }

    if (!state.paletteUI) {
      state.paletteUI = new Palette.PaletteUI(el('palette-container'), state.model, state.assetLib, {
        onSelectForPlacement: (name) => {
          state.gridEditor.setTool('place', name);
          setStatus(`Placing "${name}" — click or drag on the grid. Switch to Erase to remove.`);
        },
        onEditRequest: (name) => openEntityEditor(name),
        onCreateRequest: (type) => openEntityCreator(type),
      });
    } else {
      state.paletteUI.setModel(state.model);
    }

    if (!state.layerPanel) {
      state.layerPanel = new Layers.LayerPanel(el('layers-container'), {
        onEditRequest: (name) => openEntityEditor(name),
        onChanged: () => { markDirty(true); state.gridEditor.requestRedraw(); },
        onPathEditToggle: (name) => {
          const isActive = state.gridEditor.pathEditEntity === name;
          state.gridEditor.setPathEditEntity(isActive ? null : name);
          setStatus(isActive
            ? 'Path editing stopped.'
            : `Path editing "${name}": Shift+click the grid to add waypoints.`);
        },
      });
    } else {
      state.layerPanel.setModel(state.model);
    }

    state.paletteUI.render();
    state.gridEditor.requestRedraw();
  }

  // ---- Entity create / edit modal --------------------------------------

  function openEntityCreator(type) {
    const modal = el('modal');
    const body = el('modal-body');
    body.innerHTML = '';
    el('modal-title').textContent = `New ${type}`;

    const nameWrap = document.createElement('div');
    nameWrap.className = 'form-field';
    const nameLabel = document.createElement('label');
    nameLabel.textContent = 'Entity name';
    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.value = state.model.generateName(defaultPrefixForType(type));
    nameWrap.appendChild(nameLabel);
    nameWrap.appendChild(nameInput);
    body.appendChild(nameWrap);

    const formBody = document.createElement('div');
    body.appendChild(formBody);
    const form = Palette.buildEntityForm(formBody, state.assetLib, type, null, { model: state.model });

    showModal(() => {
      const name = nameInput.value.trim();
      if (!name) { alert('Please enter a name.'); return false; }
      if (state.model.entities.hasOwnProperty(name)) {
        alert(`Entity "${name}" already exists.`);
        return false;
      }
      const data = form.collect();
      state.model.createEntity(name, type, data);
      state.paletteUI.render();
      markDirty(true);
      setStatus(`Created ${type} "${name}". Select it in the palette to place it on the grid.`);
      return true;
    });
  }

  function openEntityEditor(name) {
    const type = state.model.entityType(name);
    const data = state.model.entityData(name);
    const modal = el('modal');
    const body = el('modal-body');
    body.innerHTML = '';
    el('modal-title').textContent = `Edit ${name} (${type})`;

    const nameWrap = document.createElement('div');
    nameWrap.className = 'form-field';
    const nameLabel = document.createElement('label');
    nameLabel.textContent = 'Entity name';
    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.value = name;
    nameWrap.appendChild(nameLabel);
    nameWrap.appendChild(nameInput);
    body.appendChild(nameWrap);

    const formBody = document.createElement('div');
    body.appendChild(formBody);
    const form = Palette.buildEntityForm(formBody, state.assetLib, type, data, { model: state.model });

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'modal-delete-btn';
    deleteBtn.textContent = 'Delete this entity (removes all placements)';
    deleteBtn.addEventListener('click', () => {
      if (confirm(`Delete "${name}" and remove it from every cell it's placed in?`)) {
        state.model.deleteEntity(name);
        state.paletteUI.render();
        state.gridEditor.invalidateSpriteCache(name);
        markDirty(true);
        hideModal();
        setStatus(`Deleted "${name}".`);
      }
    });
    body.appendChild(deleteBtn);

    showModal(() => {
      const newName = nameInput.value.trim();
      if (!newName) { alert('Please enter a name.'); return false; }
      const newData = form.collect();
      try {
        if (newName !== name) {
          state.model.renameEntity(name, newName);
        }
        state.model.entities[newName].data = newData;
      } catch (e) {
        alert(e.message);
        return false;
      }
      state.gridEditor.invalidateSpriteCache(name);
      state.gridEditor.invalidateSpriteCache(newName);
      state.paletteUI.render();
      state.layerPanel.render();
      markDirty(true);
      setStatus(`Updated "${newName}".`);
      return true;
    });
  }

  function defaultPrefixForType(type) {
    const map = {
      Block: 'blk_', MovableBlock: 'mov_', Door: 'd_', Hazard: 'hz_',
      FallingHazard: 'fh_', MovingBlock: 'mb_', MovingHazard: 'mh_',
      Enemy: 'npc_', Player: 'p_', Objective: 'obj_',
      SaveTrigger: 't_save_', SwapLevelTrigger: 't_swap_',
      PropertyTrigger: 't_prop_', ObjectiveTrigger: 't_obj_', TextTrigger: 't_text_',
    };
    return map[type] || 'ent_';
  }

  function showModal(onSave) {
    const modal = el('modal');
    modal.style.display = 'flex';
    const saveBtn = el('modal-save-btn');
    const cancelBtn = el('modal-cancel-btn');

    const cleanup = () => {
      saveBtn.removeEventListener('click', saveHandler);
      cancelBtn.removeEventListener('click', cancelHandler);
    };
    const saveHandler = () => {
      const ok = onSave();
      if (ok !== false) {
        cleanup();
        hideModal();
      }
    };
    const cancelHandler = () => {
      cleanup();
      hideModal();
    };
    saveBtn.addEventListener('click', saveHandler);
    cancelBtn.addEventListener('click', cancelHandler);
  }

  function hideModal() {
    el('modal').style.display = 'none';
  }

  // ---- Toolbar --------------------------------------------------------

  function wireToolbar() {
    el('open-project-btn').addEventListener('click', handleOpenProject);
    el('level-select').addEventListener('change', (e) => handleLoadLevel(e.target.value));
    el('save-btn').addEventListener('click', handleSaveLevel);
    el('new-level-btn').addEventListener('click', handleCreateLevel);

    el('tool-place').addEventListener('click', () => {
      setActiveToolButton('tool-place');
      if (state.gridEditor) state.gridEditor.setTool('place', state.paletteUI.selectedName);
    });
    el('tool-erase').addEventListener('click', () => {
      setActiveToolButton('tool-erase');
      if (state.gridEditor) state.gridEditor.setTool('erase');
    });
    el('tool-select').addEventListener('click', () => {
      setActiveToolButton('tool-select');
      if (state.gridEditor) state.gridEditor.setTool('select');
    });

    el('zoom-in-btn').addEventListener('click', () => adjustZoom(0.15));
    el('zoom-out-btn').addEventListener('click', () => adjustZoom(-0.15));

    el('reshuffle-btn').addEventListener('click', () => {
      state.assetLib.reshuffleSpriteVariants();
      if (state.gridEditor) state.gridEditor.invalidateSpriteCache();
      if (state.paletteUI) state.paletteUI.render();
      setStatus('Re-rolled randomized sprite previews (UnarmedAgent-style variants). Nothing in the level data changed.');
    });

    el('block-size-input').addEventListener('change', (e) => {
      const v = parseInt(e.target.value, 10) || 96;
      state.assetLib.blockSize = v;
      localStorage.setItem('agentglitch_blockSize', String(v));
      if (state.gridEditor) state.gridEditor.invalidateSpriteCache();
    });

    el('terrain-tile-size-input').addEventListener('change', (e) => {
      const v = parseInt(e.target.value, 10) || 48;
      state.assetLib.terrainNativeTileSize = v;
      localStorage.setItem('agentglitch_terrainTileSize', String(v));
      if (state.gridEditor) state.gridEditor.invalidateSpriteCache();
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && state.gridEditor && state.gridEditor.pathEditEntity) {
        state.gridEditor.setPathEditEntity(null);
        setStatus('Path editing stopped.');
      }
      if (e.key === 'Escape') hideModal();
    });
  }

  function setActiveToolButton(activeId) {
    ['tool-place', 'tool-erase', 'tool-select'].forEach(id => {
      el(id).classList.toggle('active', id === activeId);
    });
  }

  function adjustZoom(delta) {
    if (!state.gridEditor) return;
    state.gridEditor.zoom = Math.max(0.25, Math.min(3, state.gridEditor.zoom + delta));
    state.gridEditor.requestRedraw();
  }

  // ---- Init -------------------------------------------------------------

  function loadPersistedSettings() {
    const savedBlockSize = localStorage.getItem('agentglitch_blockSize');
    const savedTerrainSize = localStorage.getItem('agentglitch_terrainTileSize');

    const blockSize = savedBlockSize ? parseInt(savedBlockSize, 10) : 96;
    const terrainSize = savedTerrainSize ? parseInt(savedTerrainSize, 10) : 48;

    el('block-size-input').value = blockSize;
    el('terrain-tile-size-input').value = terrainSize;
    state.assetLib.blockSize = blockSize;
    state.assetLib.terrainNativeTileSize = terrainSize;
  }

  document.addEventListener('DOMContentLoaded', () => {
    wireToolbar();
    loadPersistedSettings();
    try {
      FSIO.checkSupport();
    } catch (e) {
      setStatus(e.message, true);
      el('open-project-btn').disabled = true;
    }
  });
})();
