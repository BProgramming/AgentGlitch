// canvas.js
// Grid canvas rendering + interaction for the level editor.
//
// Responsibilities:
//  - Draw the grid, every placed entity (using sprite previews from Sprites.AssetLibrary)
//  - Show a small "stack badge" on cells with 2+ entities
//  - Handle click-to-place (from palette selection), click-to-select, drag-paint
//  - Render & let the user drag-resize a trigger's width/height rectangle
//  - Render & let the user Shift+click to append patrol path waypoints
//
// This module does not know about the side panels directly; it communicates
// via callbacks (onCellClick, onSelectionChange, onPathEdited, onTriggerResized)
// so app.js can wire it to the rest of the UI without tight coupling.

const GridCanvas = (() => {

  class Editor {
    constructor(canvasEl, model, assetLib, opts = {}) {
      this.canvas = canvasEl;
      this.ctx = canvasEl.getContext('2d');
      this.model = model;
      this.assetLib = assetLib;

      this.tileSize = opts.tileSize || 32; // on-screen pixel size per grid cell
      this.zoom = 1;

      this.selectedCell = null; // [r, c] of last-clicked cell
      this.activeTool = 'place'; // 'place' | 'erase' | 'select'
      this.placingEntityName = null; // entity name to stamp when tool === 'place'

      // Path-edit mode: when set, Shift+click appends a waypoint to this entity's path.
      this.pathEditEntity = null; // entity name currently being path-edited

      // Trigger-resize drag state
      this.triggerDrag = null; // { name, anchorR, anchorC, startX, startY, handle }

      this.isMouseDown = false;
      this.lastPaintedCell = null;

      this._spriteDrawCache = new Map(); // entity name -> resolved draw info (async-loaded)

      this.onCellClick = null;       // (r, c, event) => void
      this.onSelectionChange = null; // (selection) => void
      this.onPathEdited = null;      // (entityName, newPath) => void
      this.onTriggerResized = null;  // (entityName, width, height) => void
      this.onModelChanged = null;    // () => void, called after any grid mutation

      this._bindEvents();
    }

    setModel(model) {
      this.model = model;
      this.selectedCell = null;
      this._spriteDrawCache.clear();
      this.requestRedraw();
    }

    setTool(tool, entityName = null) {
      this.activeTool = tool;
      this.placingEntityName = entityName;
    }

    setPathEditEntity(name) {
      this.pathEditEntity = name;
      this.requestRedraw();
    }

    screenToCell(px, py) {
      const c = Math.floor(px / (this.tileSize * this.zoom));
      const r = Math.floor(py / (this.tileSize * this.zoom));
      return [r, c];
    }

    cellToScreen(r, c) {
      return [
        c * this.tileSize * this.zoom,
        r * this.tileSize * this.zoom,
      ];
    }

    _bindEvents() {
      const canvas = this.canvas;

      canvas.addEventListener('mousedown', (e) => {
        const rect = canvas.getBoundingClientRect();
        const px = e.clientX - rect.left;
        const py = e.clientY - rect.top;
        const [r, c] = this.screenToCell(px, py);
        if (r < 0 || r >= this.model.rows || c < 0 || c >= this.model.cols) return;

        // Shift+click: append a patrol path waypoint if we're in path-edit mode.
        if (e.shiftKey && this.pathEditEntity) {
          this._appendPathWaypoint(r, c);
          return;
        }

        // Check if we're grabbing a trigger resize handle first.
        const handleHit = this._hitTestTriggerHandle(px, py);
        if (handleHit) {
          this.triggerDrag = handleHit;
          return;
        }

        this.isMouseDown = true;
        this.lastPaintedCell = [r, c];
        this._handlePrimaryClick(r, c, e);
      });

      canvas.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        const px = e.clientX - rect.left;
        const py = e.clientY - rect.top;

        if (this.triggerDrag) {
          this._updateTriggerDrag(px, py);
          return;
        }

        if (!this.isMouseDown) return;
        const [r, c] = this.screenToCell(px, py);
        if (r < 0 || r >= this.model.rows || c < 0 || c >= this.model.cols) return;
        if (this.lastPaintedCell && this.lastPaintedCell[0] === r && this.lastPaintedCell[1] === c) return;
        // Drag-paint only for place/erase tools, not select.
        if (this.activeTool === 'place' || this.activeTool === 'erase') {
          this.lastPaintedCell = [r, c];
          this._handlePrimaryClick(r, c, e);
        }
      });

      window.addEventListener('mouseup', () => {
        this.isMouseDown = false;
        this.lastPaintedCell = null;
        if (this.triggerDrag) {
          const { name } = this.triggerDrag;
          const data = this.model.entityData(name);
          if (this.onTriggerResized) this.onTriggerResized(name, data.width, data.height);
          this.triggerDrag = null;
          this.requestRedraw();
        }
      });

      canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    }

    _handlePrimaryClick(r, c, event) {
      if (this.activeTool === 'place' && this.placingEntityName) {
        this.model.addEntityToCell(r, c, this.placingEntityName);
        if (this.onModelChanged) this.onModelChanged();
      } else if (this.activeTool === 'erase') {
        const cell = this.model.getCell(r, c);
        if (cell.length > 0) {
          // Erase removes the topmost (last) token by default; full clear
          // happens via the layer panel for stacked cells.
          this.model.setCell(r, c, []);
          if (this.onModelChanged) this.onModelChanged();
        }
      } else {
        this.selectedCell = [r, c];
      }
      if (this.onCellClick) this.onCellClick(r, c, event);
      this.requestRedraw();
    }

    _appendPathWaypoint(r, c) {
      const name = this.pathEditEntity;
      const data = this.model.entityData(name);
      if (!data) return;
      const placements = this.model.findPlacements(name);
      if (placements.length === 0) return;
      const [originR, originC] = placements[0];

      const path = Array.isArray(data.path) ? data.path : [];
      // Determine the "current" absolute position by walking the path from origin.
      let curR = originR, curC = originC;
      for (const [dx, dy] of path) {
        curC += dx;
        curR += dy;
      }
      const dx = c - curC;
      const dy = r - curR;
      const newPath = [...path, [dx, dy]];
      data.path = newPath;
      if (this.onPathEdited) this.onPathEdited(name, newPath);
      this.requestRedraw();
    }

    _hitTestTriggerHandle(px, py) {
      if (!this.selectedCell) return null;
      const [r, c] = this.selectedCell;
      const cellTokens = this.model.getCell(r, c);
      for (const name of cellTokens) {
        const type = this.model.entityType(name);
        if (!Model.isTriggerType(type)) continue;
        const data = this.model.entityData(name);
        const w = Math.max(1, data.width || 1);
        const h = Math.max(1, data.height || 1);
        const [x0, y0] = this.cellToScreen(r, c);
        const x1 = x0 + w * this.tileSize * this.zoom;
        const y1 = y0 + h * this.tileSize * this.zoom;
        const handleSize = 10;
        if (Math.abs(px - x1) < handleSize && Math.abs(py - y1) < handleSize) {
          return { name, anchorR: r, anchorC: c, handle: 'br' };
        }
      }
      return null;
    }

    _updateTriggerDrag(px, py) {
      const { name, anchorR, anchorC } = this.triggerDrag;
      const data = this.model.entityData(name);
      const [x0, y0] = this.cellToScreen(anchorR, anchorC);
      const cellPx = this.tileSize * this.zoom;
      const newW = Math.max(1, Math.round((px - x0) / cellPx));
      const newH = Math.max(1, Math.round((py - y0) / cellPx));
      data.width = newW;
      data.height = newH;
      this.requestRedraw();
    }

    requestRedraw() {
      if (this._redrawScheduled) return;
      this._redrawScheduled = true;
      requestAnimationFrame(() => {
        this._redrawScheduled = false;
        this.draw();
      });
    }

    draw() {
      const ctx = this.ctx;
      const { rows, cols } = this.model;
      const cellPx = this.tileSize * this.zoom;

      // Size the canvas to the actual grid content, not the viewport — this
      // is what lets the surrounding #canvas-area's native scrollbars work.
      // Panning is handled entirely by browser scroll now, so offsetX/Y are
      // intentionally not applied here (they'd double up with scrolling).
      this.canvas.width = Math.max(1, Math.round(cols * cellPx));
      this.canvas.height = Math.max(1, Math.round(rows * cellPx));

      ctx.fillStyle = '#F6F6F4';
      ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

      ctx.save();

      // Grid lines
      ctx.strokeStyle = 'rgba(0,0,0,0.08)';
      ctx.lineWidth = 1;
      for (let c = 0; c <= cols; c++) {
        ctx.beginPath();
        ctx.moveTo(c * cellPx, 0);
        ctx.lineTo(c * cellPx, rows * cellPx);
        ctx.stroke();
      }
      for (let r = 0; r <= rows; r++) {
        ctx.beginPath();
        ctx.moveTo(0, r * cellPx);
        ctx.lineTo(cols * cellPx, r * cellPx);
        ctx.stroke();
      }

      // Entities
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const tokens = this.model.getCell(r, c);
          if (tokens.length === 0) continue;
          this._drawCellEntities(r, c, tokens, cellPx);
        }
      }

      // Selection highlight
      if (this.selectedCell) {
        const [r, c] = this.selectedCell;
        ctx.strokeStyle = '#5cc8ff';
        ctx.lineWidth = 2;
        ctx.strokeRect(c * cellPx + 1, r * cellPx + 1, cellPx - 2, cellPx - 2);
      }

      // Trigger rectangles for selected cell's trigger entities
      if (this.selectedCell) {
        const [r, c] = this.selectedCell;
        for (const name of this.model.getCell(r, c)) {
          const type = this.model.entityType(name);
          if (!Model.isTriggerType(type)) continue;
          this._drawTriggerRect(name, r, c, cellPx);
        }
      }

      // Patrol path for entity in path-edit mode
      if (this.pathEditEntity) {
        this._drawPatrolPath(this.pathEditEntity, cellPx);
      }

      ctx.restore();
    }

    _drawCellEntities(r, c, tokens, cellPx) {
      const ctx = this.ctx;
      const x = c * cellPx;
      const y = r * cellPx;

      // Draw the topmost (last) token's sprite as the visible tile.
      const topName = tokens[tokens.length - 1];
      const drawInfo = this._spriteDrawCache.get(topName);
      if (drawInfo && drawInfo.canvas) {
        ctx.drawImage(drawInfo.canvas, x, y, cellPx, cellPx);
        if (drawInfo.wasRandomized) {
          this._drawRandomizedMarker(x, y, cellPx);
        }
      } else {
        // Placeholder while sprite loads (or if missing): colored rect + label.
        ctx.fillStyle = this._colorForType(this.model.entityType(topName));
        ctx.fillRect(x + 1, y + 1, cellPx - 2, cellPx - 2);
        ctx.fillStyle = 'rgba(255,255,255,0.92)';
        const fontSize = Math.max(7, Math.min(11, cellPx * 0.24));
        ctx.font = `${fontSize}px monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        this._drawWrappedLabel(topName, x + cellPx / 2, y + cellPx / 2, cellPx - 4, fontSize);
        this._requestSpriteLoad(topName);
      }

      // Stack badge if more than one entity occupies this cell.
      if (tokens.length > 1) {
        const badgeSize = Math.max(12, cellPx * 0.28);
        ctx.fillStyle = '#ff7a45';
        ctx.beginPath();
        ctx.arc(x + cellPx - badgeSize / 2 - 2, y + badgeSize / 2 + 2, badgeSize / 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#1a1c20';
        ctx.font = `bold ${badgeSize * 0.7}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(tokens.length), x + cellPx - badgeSize / 2 - 2, y + badgeSize / 2 + 2 + 1);
      }
    }

    _drawWrappedLabel(name, cx, cy, maxWidth, fontSize) {
      const ctx = this.ctx;
      // Split on underscores so long entity names (e.g. "t_unlock_lab") wrap
      // sensibly across up to 2 lines rather than getting hard-truncated.
      const parts = name.split('_');
      let lines = [];
      let current = '';
      for (const part of parts) {
        const candidate = current ? `${current}_${part}` : part;
        if (ctx.measureText(candidate).width <= maxWidth || !current) {
          current = candidate;
        } else {
          lines.push(current);
          current = part;
        }
        if (lines.length === 1 && !current.includes('_')) {
          // After wrapping once, keep remaining parts on line 2 even if long;
          // truncate line 2 with ellipsis if it still overflows.
        }
      }
      if (current) lines.push(current);
      if (lines.length > 2) {
        lines = [lines[0], lines.slice(1).join('_')];
      }
      lines = lines.map(line => this._ellipsize(line, maxWidth));

      const lineHeight = fontSize * 1.15;
      const startY = cy - ((lines.length - 1) * lineHeight) / 2;
      lines.forEach((line, i) => {
        ctx.fillText(line, cx, startY + i * lineHeight);
      });
    }

    _ellipsize(text, maxWidth) {
      const ctx = this.ctx;
      if (ctx.measureText(text).width <= maxWidth) return text;
      let truncated = text;
      while (truncated.length > 1 && ctx.measureText(truncated + '…').width > maxWidth) {
        truncated = truncated.slice(0, -1);
      }
      return truncated + '…';
    }

    _colorForType(type) {
      const palette = {
        Block: '#3a3f47', MovableBlock: '#5a6072', Door: '#a86b32',
        Hazard: '#b8333f', FallingHazard: '#8a2030', MovingBlock: '#3f6f8f',
        MovingHazard: '#7f2a4a', Enemy: '#7a3fa0', Player: '#2f9e5c',
        Objective: '#d4af37', SaveTrigger: '#2c8f8f', SwapLevelTrigger: '#2c8f8f',
        PropertyTrigger: '#2c8f8f', ObjectiveTrigger: '#2c8f8f', TextTrigger: '#2c8f8f',
      };
      return palette[type] || '#444';
    }

    // Small corner marker drawn on cells whose sprite came from a randomly
    // picked numeric-suffix variant (e.g. data says "UnarmedAgent" but the
    // editor is previewing "UnarmedAgent3"). This is a reminder that what's
    // shown is one possible preview, not a fixed in-game appearance — the
    // real game re-randomizes this choice every time the entity is built.
    _drawRandomizedMarker(x, y, cellPx) {
      const ctx = this.ctx;
      const size = Math.max(10, cellPx * 0.22);
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(x + cellPx - size, y);
      ctx.lineTo(x + cellPx, y);
      ctx.lineTo(x + cellPx, y + size);
      ctx.closePath();
      ctx.fillStyle = 'rgba(154, 92, 219, 0.85)';
      ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${size * 0.55}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('?', x + cellPx - size * 0.32, y + size * 0.38);
      ctx.restore();
    }

    async _requestSpriteLoad(name) {
      if (this._spriteDrawCache.has(name)) return;
      this._spriteDrawCache.set(name, null); // mark in-flight
      const type = this.model.entityType(name);
      const data = this.model.entityData(name);
      if (!type || !data) return;
      const schema = Model.TYPE_SCHEMAS[type];
      try {
        let canvas = null;
        let wasRandomized = false;
        if (schema && schema.addressing === 'terrain') {
          const tileSizeSetting = this.assetLib.terrainNativeTileSize || 48;
          canvas = await this.assetLib.getTerrainTile(data.coord_x, data.coord_y, tileSizeSetting);
        } else if (schema && schema.addressing === 'sprite' && data.sprite) {
          const preview = await this.assetLib.getSpritePreview(data.sprite);
          canvas = preview ? preview.canvas : null;
          wasRandomized = preview ? !!preview.wasRandomized : false;
        }
        this._spriteDrawCache.set(name, { canvas, wasRandomized });
        this.requestRedraw();
      } catch (e) {
        console.warn(`Failed to load sprite for ${name}:`, e);
        this._spriteDrawCache.set(name, { canvas: null, wasRandomized: false });
      }
    }

    invalidateSpriteCache(name = null) {
      if (name) this._spriteDrawCache.delete(name);
      else this._spriteDrawCache.clear();
      this.requestRedraw();
    }

    _drawTriggerRect(name, anchorR, anchorC, cellPx) {
      const ctx = this.ctx;
      const data = this.model.entityData(name);
      const w = Math.max(1, data.width || 1);
      const h = Math.max(1, data.height || 1);
      const x = anchorC * cellPx;
      const y = anchorR * cellPx;
      const pxW = w * cellPx;
      const pxH = h * cellPx;

      ctx.fillStyle = 'rgba(44,143,143,0.25)';
      ctx.fillRect(x, y, pxW, pxH);
      ctx.strokeStyle = '#2c8f8f';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(x, y, pxW, pxH);
      ctx.setLineDash([]);

      // Resize handle, bottom-right corner.
      ctx.fillStyle = '#2c8f8f';
      ctx.fillRect(x + pxW - 6, y + pxH - 6, 8, 8);
    }

    _drawPatrolPath(name, cellPx) {
      const data = this.model.entityData(name);
      if (!data || !Array.isArray(data.path)) return;
      const placements = this.model.findPlacements(name);
      if (placements.length === 0) return;
      const [originR, originC] = placements[0];

      const ctx = this.ctx;
      ctx.strokeStyle = '#ffd166';
      ctx.fillStyle = '#ffd166';
      ctx.lineWidth = 2;

      let curR = originR, curC = originC;
      let px0 = curC * cellPx + cellPx / 2;
      let py0 = curR * cellPx + cellPx / 2;

      ctx.beginPath();
      ctx.arc(px0, py0, 5, 0, Math.PI * 2);
      ctx.fill();

      for (const [dx, dy] of data.path) {
        curC += dx;
        curR += dy;
        const px1 = curC * cellPx + cellPx / 2;
        const py1 = curR * cellPx + cellPx / 2;
        ctx.beginPath();
        ctx.moveTo(px0, py0);
        ctx.lineTo(px1, py1);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(px1, py1, 5, 0, Math.PI * 2);
        ctx.fill();
        px0 = px1; py0 = py1;
      }
    }
  }

  return { Editor };
})();
