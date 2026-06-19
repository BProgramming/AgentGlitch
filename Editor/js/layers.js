// layers.js
// Side panel showing the entities occupying the currently selected grid cell,
// stacked in z-order (CSV token order = draw order, last = topmost).
// Supports: click to focus/edit a layer, drag to reorder, delete a layer,
// add another entity to the same cell from the palette's current selection.

const Layers = (() => {

  class LayerPanel {
    constructor(containerEl, opts = {}) {
      this.container = containerEl;
      this.model = null;
      this.cell = null; // [r, c]
      this.onEditRequest = opts.onEditRequest || (() => {});
      this.onChanged = opts.onChanged || (() => {});
      this.onPathEditToggle = opts.onPathEditToggle || (() => {});
      this._dragFromIdx = null;
    }

    setModel(model) {
      this.model = model;
      this.setCell(null);
    }

    setCell(cell) {
      this.cell = cell;
      this.render();
    }

    render() {
      this.container.innerHTML = '';
      if (!this.cell || !this.model) {
        const empty = document.createElement('p');
        empty.className = 'layers-empty';
        empty.textContent = 'Click a grid cell to see what\'s placed there.';
        this.container.appendChild(empty);
        return;
      }

      const [r, c] = this.cell;
      const tokens = this.model.getCell(r, c);

      const header = document.createElement('div');
      header.className = 'layers-header';
      header.textContent = `Cell (row ${r}, col ${c}) — ${tokens.length} ${tokens.length === 1 ? 'entity' : 'entities'}`;
      this.container.appendChild(header);

      if (tokens.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'layers-empty';
        empty.textContent = 'Nothing placed here. Pick an entity from the palette and click this cell to add one.';
        this.container.appendChild(empty);
        return;
      }

      const list = document.createElement('div');
      list.className = 'layers-list';

      // Render topmost-first for intuitive "front to back" reading.
      const order = tokens.map((_, i) => i).reverse();
      order.forEach((idx, displayPos) => {
        const name = tokens[idx];
        list.appendChild(this._buildLayerRow(name, idx, displayPos, tokens.length));
      });

      this.container.appendChild(list);
    }

    _buildLayerRow(name, actualIdx, displayPos, total) {
      const row = document.createElement('div');
      row.className = 'layer-row';
      row.draggable = true;
      row.dataset.actualIdx = actualIdx;

      const dragHandle = document.createElement('span');
      dragHandle.className = 'layer-drag-handle';
      dragHandle.textContent = '⠿';
      row.appendChild(dragHandle);

      const typeLabel = document.createElement('span');
      typeLabel.className = 'layer-type';
      const type = this.model.entityType(name);
      typeLabel.textContent = type || '?';
      row.appendChild(typeLabel);

      const nameLabel = document.createElement('span');
      nameLabel.className = 'layer-name';
      nameLabel.textContent = name;
      row.appendChild(nameLabel);

      if (displayPos === 0) {
        const topBadge = document.createElement('span');
        topBadge.className = 'layer-top-badge';
        topBadge.textContent = 'top';
        row.appendChild(topBadge);
      }

      const data = this.model.entityData(name);
      if (data && Array.isArray(data.path)) {
        const pathBtn = document.createElement('button');
        pathBtn.className = 'layer-path-btn';
        pathBtn.textContent = '⟶ path';
        pathBtn.title = 'Edit patrol path (Shift+click grid to add points)';
        pathBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.onPathEditToggle(name);
        });
        row.appendChild(pathBtn);
      }

      const editBtn = document.createElement('button');
      editBtn.className = 'layer-edit-btn';
      editBtn.textContent = '✎';
      editBtn.title = 'Edit this entity\'s data';
      editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.onEditRequest(name);
      });
      row.appendChild(editBtn);

      const delBtn = document.createElement('button');
      delBtn.className = 'layer-delete-btn';
      delBtn.textContent = '🗑';
      delBtn.title = 'Remove from this cell';
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const [r, c] = this.cell;
        this.model.removeEntityFromCell(r, c, name);
        this.render();
        this.onChanged();
      });
      row.appendChild(delBtn);

      row.addEventListener('dragstart', (e) => {
        this._dragFromIdx = actualIdx;
        e.dataTransfer.effectAllowed = 'move';
      });
      row.addEventListener('dragover', (e) => e.preventDefault());
      row.addEventListener('drop', (e) => {
        e.preventDefault();
        const toIdx = actualIdx;
        if (this._dragFromIdx !== null && this._dragFromIdx !== toIdx) {
          const [r, c] = this.cell;
          this.model.reorderCellEntity(r, c, this._dragFromIdx, toIdx);
          this.render();
          this.onChanged();
        }
        this._dragFromIdx = null;
      });

      return row;
    }
  }

  return { LayerPanel };
})();
