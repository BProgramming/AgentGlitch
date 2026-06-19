// model.js
// Core data model for the Agent Glitch level editor.
// Handles parsing/serializing .agl (CSV grid) and .agd (entity dict JSON) files,
// and provides the in-memory representation the rest of the app edits.

const Model = (() => {

  // ---- Entity type schemas --------------------------------------------
  // Describes the "data" fields for each known entity type, used to build
  // forms for creating/editing instances. "kind" drives which input widget
  // the editor shows. This is intentionally permissive: unknown types are
  // still loaded and editable as raw JSON, just without a friendly form.

  const TYPE_SCHEMAS = {
    Block: {
      addressing: 'terrain', // uses coord_x/coord_y into Terrain.png
      fields: [
        { key: 'coord_x', kind: 'int', label: 'Terrain Col' },
        { key: 'coord_y', kind: 'int', label: 'Terrain Row' },
      ],
    },
    MovableBlock: {
      addressing: 'terrain',
      fields: [
        { key: 'coord_x', kind: 'int', label: 'Terrain Col' },
        { key: 'coord_y', kind: 'int', label: 'Terrain Row' },
      ],
    },
    MovingBlock: {
      addressing: 'terrain',
      fields: [
        { key: 'coord_x', kind: 'int', label: 'Terrain Col' },
        { key: 'coord_y', kind: 'int', label: 'Terrain Row' },
        { key: 'path', kind: 'path', label: 'Path (relative steps)' },
        { key: 'speed', kind: 'int', label: 'Speed' },
        { key: 'hold_for_collision', kind: 'bool', label: 'Hold For Collision' },
      ],
    },
    Door: {
      addressing: 'terrain',
      fields: [
        { key: 'unlocked_coord_x', kind: 'int', label: 'Unlocked Col' },
        { key: 'unlocked_coord_y', kind: 'int', label: 'Unlocked Row' },
        { key: 'locked_coord_x', kind: 'int', label: 'Locked Col' },
        { key: 'locked_coord_y', kind: 'int', label: 'Locked Row' },
        { key: 'direction', kind: 'int', label: 'Direction' },
        { key: 'is_locked', kind: 'bool', label: 'Is Locked' },
        { key: 'speed', kind: 'int', label: 'Speed' },
      ],
    },
    Hazard: {
      addressing: 'sprite',
      fields: [
        { key: 'sprite', kind: 'sprite', label: 'Sprite Folder' },
        { key: 'hit_sides', kind: 'text', label: 'Hit Sides (e.g. ULR)' },
      ],
    },
    FallingHazard: {
      addressing: 'sprite',
      fields: [
        { key: 'sprite', kind: 'sprite', label: 'Sprite Folder' },
        { key: 'hit_sides', kind: 'text', label: 'Hit Sides' },
        { key: 'drop_x', kind: 'int', label: 'Drop X' },
        { key: 'drop_y', kind: 'int', label: 'Drop Y' },
      ],
    },
    MovingHazard: {
      addressing: 'sprite',
      fields: [
        { key: 'sprite', kind: 'sprite', label: 'Sprite Folder' },
        { key: 'path', kind: 'path', label: 'Path (relative steps)' },
        { key: 'speed', kind: 'int', label: 'Speed' },
      ],
    },
    Enemy: {
      addressing: 'sprite',
      fields: [
        { key: 'sprite', kind: 'sprite', label: 'Sprite Folder' },
        { key: 'hp', kind: 'int', label: 'HP' },
        { key: 'path', kind: 'path_nullable', label: 'Patrol Path' },
        { key: 'is_hostile', kind: 'bool', label: 'Is Hostile' },
        { key: 'bark', kind: 'text', label: 'Bark File' },
      ],
    },
    Player: {
      addressing: 'sprite',
      fields: [
        { key: 'face_left', kind: 'bool', label: 'Face Left' },
      ],
    },
    Objective: {
      addressing: 'sprite',
      fields: [
        { key: 'sprite', kind: 'sprite', label: 'Sprite Folder' },
        { key: 'text', kind: 'text', label: 'Objective Text' },
        { key: 'trigger', kind: 'text', label: 'Trigger Name(s)' },
      ],
    },
    SaveTrigger: {
      addressing: 'trigger',
      fields: [
        { key: 'width', kind: 'int', label: 'Width' },
        { key: 'height', kind: 'int', label: 'Height' },
      ],
    },
    SwapLevelTrigger: {
      addressing: 'trigger',
      fields: [
        { key: 'width', kind: 'int', label: 'Width' },
        { key: 'height', kind: 'int', label: 'Height' },
      ],
    },
    PropertyTrigger: {
      addressing: 'trigger',
      fields: [
        { key: 'width', kind: 'int', label: 'Width' },
        { key: 'height', kind: 'int', label: 'Height' },
        { key: 'input.target', kind: 'entity_ref', label: 'Target Entity' },
        { key: 'input.property', kind: 'text', label: 'Property' },
        { key: 'input.value', kind: 'bool', label: 'Value' },
      ],
    },
    ObjectiveTrigger: {
      addressing: 'trigger',
      fields: [
        { key: 'width', kind: 'int', label: 'Width' },
        { key: 'height', kind: 'int', label: 'Height' },
        { key: 'input.target', kind: 'entity_ref', label: 'Target Objective' },
        { key: 'input.value', kind: 'bool', label: 'Value' },
      ],
    },
    TextTrigger: {
      addressing: 'trigger',
      fields: [
        { key: 'width', kind: 'int', label: 'Width' },
        { key: 'height', kind: 'int', label: 'Height' },
        { key: 'input.file', kind: 'text', label: 'Text File' },
        { key: 'input.type', kind: 'bool', label: 'Type' },
      ],
    },
  };

  function isTriggerType(type) {
    const schema = TYPE_SCHEMAS[type];
    return !!schema && schema.addressing === 'trigger';
  }

  // ---- CSV parsing / serialization -------------------------------------
  // .agl files use CRLF line endings and comma-separated cells. Cells may
  // contain zero, one, or multiple space-separated entity-name tokens
  // (multiple = stacked entities at that grid coordinate).
  // We preserve CRLF on save to match the existing toolchain exactly.

  function parseCSV(text) {
    // Normalize to \n internally for splitting, but remember to re-emit \r\n.
    const lines = text.replace(/\r\n/g, '\n').split('\n');
    // Drop a single trailing empty line caused by a final newline.
    while (lines.length && lines[lines.length - 1] === '') lines.pop();
    const grid = lines.map(line => splitCSVLine(line));
    return grid;
  }

  function splitCSVLine(line) {
    // Simple split on comma is sufficient here: tokens are plain identifiers
    // (no embedded commas/quotes appear in the existing files), but we guard
    // against stray whitespace around commas just in case.
    return line.split(',').map(cell => cell.trim());
  }

  function cellToTokens(cell) {
    if (!cell) return [];
    return cell.split(' ').map(t => t.trim()).filter(t => t.length > 0);
  }

  function tokensToCell(tokens) {
    return tokens.join(' ');
  }

  function serializeCSV(grid) {
    // Match the source toolchain's format exactly: rows joined by CRLF,
    // with NO trailing line terminator after the final row.
    const lines = grid.map(row => row.map(cell => cell || '').join(','));
    return lines.join('\r\n');
  }

  // ---- Level model ------------------------------------------------------
  // The level model wraps the raw grid (array of array of token-arrays)
  // plus the entity dict (name -> {type, data}).
  //
  // grid[row][col] = array of entity-name strings (possibly empty)

  class LevelModel {
    constructor() {
      this.grid = []; // array of rows; each row is array of string[] (tokens per cell)
      this.entities = {}; // name -> { type, data }
      this.rows = 0;
      this.cols = 0;
    }

    static fromFiles(aglText, agdText) {
      const m = new LevelModel();
      const rawGrid = parseCSV(aglText);
      m.rows = rawGrid.length;
      m.cols = rawGrid.reduce((max, row) => Math.max(max, row.length), 0);
      m.grid = rawGrid.map(row => {
        const tokenRow = row.map(cell => cellToTokens(cell));
        while (tokenRow.length < m.cols) tokenRow.push([]);
        return tokenRow;
      });
      m.entities = JSON.parse(agdText);
      return m;
    }

    static blank(rows, cols) {
      const m = new LevelModel();
      m.rows = rows;
      m.cols = cols;
      m.grid = Array.from({ length: rows }, () =>
        Array.from({ length: cols }, () => [])
      );
      m.entities = {};
      return m;
    }

    toAGL() {
      const rawGrid = this.grid.map(row => row.map(tokens => tokensToCell(tokens)));
      return serializeCSV(rawGrid);
    }

    toAGD() {
      // Preserve key order roughly as-is (insertion order); pretty-print with
      // 2-space indent to match the source files.
      return JSON.stringify(this.entities, null, 2);
    }

    getCell(r, c) {
      if (r < 0 || r >= this.rows || c < 0 || c >= this.cols) return [];
      return this.grid[r][c];
    }

    setCell(r, c, tokens) {
      this.grid[r][c] = tokens;
    }

    addEntityToCell(r, c, name) {
      const cell = this.getCell(r, c);
      if (!cell.includes(name)) cell.push(name);
    }

    removeEntityFromCell(r, c, name) {
      const cell = this.getCell(r, c);
      const idx = cell.indexOf(name);
      if (idx >= 0) cell.splice(idx, 1);
    }

    reorderCellEntity(r, c, fromIdx, toIdx) {
      const cell = this.getCell(r, c);
      const [item] = cell.splice(fromIdx, 1);
      cell.splice(toIdx, 0, item);
    }

    // Find every grid cell where a given entity name appears.
    findPlacements(name) {
      const out = [];
      for (let r = 0; r < this.rows; r++) {
        for (let c = 0; c < this.cols; c++) {
          if (this.grid[r][c].includes(name)) out.push([r, c]);
        }
      }
      return out;
    }

    entityType(name) {
      const e = this.entities[name];
      return e ? e.type : null;
    }

    entityData(name) {
      const e = this.entities[name];
      return e ? e.data : null;
    }

    // Generate a unique entity name from a base prefix, e.g. "npc_lab" -> "npc_lab5"
    generateName(base) {
      let i = 0;
      let candidate = base;
      while (this.entities.hasOwnProperty(candidate)) {
        candidate = `${base}${i}`;
        i++;
      }
      return candidate;
    }

    createEntity(name, type, data) {
      this.entities[name] = { type, data };
    }

    deleteEntity(name) {
      delete this.entities[name];
      for (let r = 0; r < this.rows; r++) {
        for (let c = 0; c < this.cols; c++) {
          this.removeEntityFromCell(r, c, name);
        }
      }
    }

    renameEntity(oldName, newName) {
      if (oldName === newName) return;
      if (this.entities.hasOwnProperty(newName)) {
        throw new Error(`Entity "${newName}" already exists`);
      }
      this.entities[newName] = this.entities[oldName];
      delete this.entities[oldName];
      for (let r = 0; r < this.rows; r++) {
        for (let c = 0; c < this.cols; c++) {
          const cell = this.grid[r][c];
          const idx = cell.indexOf(oldName);
          if (idx >= 0) cell[idx] = newName;
        }
      }
    }

    resizeGrid(newRows, newCols) {
      // Grow/shrink grid, preserving existing content where possible.
      const newGrid = Array.from({ length: newRows }, (_, r) =>
        Array.from({ length: newCols }, (_, c) =>
          (r < this.rows && c < this.cols) ? this.grid[r][c] : []
        )
      );
      this.grid = newGrid;
      this.rows = newRows;
      this.cols = newCols;
    }
  }

  return {
    TYPE_SCHEMAS,
    isTriggerType,
    parseCSV,
    serializeCSV,
    cellToTokens,
    tokensToCell,
    LevelModel,
  };
})();
