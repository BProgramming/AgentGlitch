// sprites.js
// Sprite asset loading for the level editor. Handles:
//  - Walking the Assets directory tree via the File System Access API
//  - Loading Terrain.png as a tile atlas addressed by coord_x/coord_y
//  - Loading per-entity sprites: animate.png (horizontal frame strips) or
//    picker.png (static preview), with automatic 48->96 (or whatever the
//    configured block size is) upscaling applied via canvas drawing,
//    never by mutating the source image.

const Sprites = (() => {

  // Cache: path string -> loaded {img, width, height}
  const imageCache = new Map();

  async function loadImageFromFileHandle(fileHandle) {
    const file = await fileHandle.getFile();
    const url = URL.createObjectURL(file);
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = (e) => reject(new Error(`Failed to decode image: ${e}`));
      img.src = url;
    });
  }

  function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // Walk a directory handle recursively, calling onFile(path, fileHandle) for
  // every file found. path is an array of path segments relative to root.
  async function walkDirectory(dirHandle, onFile, pathPrefix = []) {
    for await (const [name, handle] of dirHandle.entries()) {
      const path = [...pathPrefix, name];
      if (handle.kind === 'file') {
        await onFile(path, handle);
      } else if (handle.kind === 'directory') {
        await walkDirectory(handle, onFile, path);
      }
    }
  }

  // AssetLibrary indexes the Assets folder so sprite lookups by folder name
  // (e.g. "LabTech", "ElectricFence") or Terrain.png are O(1).
  class AssetLibrary {
    constructor() {
      this.rootHandle = null;
      // sprite folder name -> { animateHandle?, pickerHandle?, otherAnimHandles: Map<animName, handle> }
      this.spriteFolders = new Map();
      this.terrainHandle = null;
      this.blockSize = 96; // default render size; can be changed in the UI settings
    this.terrainNativeTileSize = 48; // default native Terrain.png tile size, per the real asset
      this._terrainImg = null;
      this._spriteImageCache = new Map(); // folder name -> { img, frameW, frameH, frameCount, scale }
      this._resolvedSpriteCache = new Map(); // requested name -> resolution result
    }

    async loadFromDirectoryHandle(assetsDirHandle) {
      this.rootHandle = assetsDirHandle;
      this.spriteFolders.clear();
      this._spriteImageCache.clear();
      this.terrainHandle = null;

      await walkDirectory(assetsDirHandle, async (path, fileHandle) => {
        const lowerPath = path.map(p => p.toLowerCase());
        if (path.length >= 2 && lowerPath[0] === 'terrain' &&
            lowerPath[lowerPath.length - 1] === 'terrain.png') {
          // Prefer the exact "Terrain.png", ignore "Terrain - Copy.png" / "Terrain_old.png"
          if (path[path.length - 1] === 'Terrain.png') {
            this.terrainHandle = fileHandle;
          }
          return;
        }
        if (path.length >= 3 && lowerPath[0] === 'sprites') {
          const folderName = path[1]; // e.g. "LabTech"
          const fileName = path[path.length - 1];
          if (!this.spriteFolders.has(folderName)) {
            this.spriteFolders.set(folderName, { animations: new Map() });
          }
          const entry = this.spriteFolders.get(folderName);
          // strip extension for animation key, e.g. "animate.png" -> "animate"
          const animName = fileName.replace(/\.[^/.]+$/, '');
          entry.animations.set(animName, fileHandle);
        }
      });
    }

    listSpriteFolders() {
      return Array.from(this.spriteFolders.keys()).sort();
    }

    hasSprite(folderName) {
      return this.spriteFolders.has(folderName);
    }

    // Mirrors EntityFactory's sprite resolution: try an exact folder-name
    // match first; if that doesn't exist, look for folders that share the
    // same base name but end in a numeric suffix (e.g. "UnarmedAgent" with
    // no exact folder -> "UnarmedAgent0".."UnarmedAgent7") and pick one.
    //
    // Real in-game randomization happens fresh every time EntityFactory
    // builds the entity, so the level data itself never records which
    // variant was chosen — there's nothing to "get right" here, it's
    // genuinely random at runtime. This picks one variant and sticks with
    // it for the rest of the editor session (cached per requested name) so
    // the preview doesn't flicker to a different skin/gender on every
    // redraw, which would be more confusing than helpful.
    resolveSpriteFolder(requestedName) {
      if (this.spriteFolders.has(requestedName)) {
        return { folderName: requestedName, wasRandomized: false, candidates: [requestedName] };
      }
      if (this._resolvedSpriteCache.has(requestedName)) {
        return this._resolvedSpriteCache.get(requestedName);
      }

      // Find every folder matching "<requestedName><digits>" exactly.
      const suffixPattern = new RegExp(`^${escapeRegExp(requestedName)}(\\d+)$`);
      const candidates = this.listSpriteFolders().filter(name => suffixPattern.test(name));

      let result;
      if (candidates.length === 0) {
        result = { folderName: null, wasRandomized: false, candidates: [] };
      } else {
        const chosen = candidates[Math.floor(Math.random() * candidates.length)];
        result = { folderName: chosen, wasRandomized: true, candidates };
      }
      this._resolvedSpriteCache.set(requestedName, result);
      return result;
    }

    // Clears the per-session random-variant cache, e.g. if you want a fresh
    // random pick rather than what was already chosen this session.
    reshuffleSpriteVariants() {
      this._resolvedSpriteCache.clear();
    }

    async getTerrainImage() {
      if (this._terrainImg) return this._terrainImg;
      if (!this.terrainHandle) return null;
      const img = await loadImageFromFileHandle(this.terrainHandle);
      this._terrainImg = img;
      return img;
    }

    // Returns a canvas (or null) containing the scaled single frame for a
    // Terrain.png coordinate. coord_x/coord_y are grid indices into the
    // terrain atlas, each cell assumed to be `nativeTileSize` px (defaults to
    // blockSize, but terrain atlases are commonly authored at native scale
    // already — see getTerrainTile for the actual sizing logic used).
    async getTerrainTile(coordX, coordY, nativeTileSize = 96) {
      const img = await this.getTerrainImage();
      if (!img) return null;
      const sx = coordX * nativeTileSize;
      const sy = coordY * nativeTileSize;
      const canvas = document.createElement('canvas');
      canvas.width = this.blockSize;
      canvas.height = this.blockSize;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(
        img,
        sx, sy, nativeTileSize, nativeTileSize,
        0, 0, this.blockSize, this.blockSize
      );
      return canvas;
    }

    // Loads (and caches) the best available preview image for a sprite
    // folder: prefers picker.png (static), falls back to the first frame of
    // animate.png, falls back to the first available animation's first frame.
    // `requestedName` is resolved the same way EntityFactory resolves
    // sprite names — exact match first, then numeric-suffix sibling chosen
    // at random — so a name like "UnarmedAgent" with no exact folder will
    // still render using one of UnarmedAgent0..UnarmedAgent7.
    // Returns { canvas, frameCount, frameW, frameH, resolvedFolderName, wasRandomized, candidates }.
    async getSpritePreview(requestedName) {
      const resolution = this.resolveSpriteFolder(requestedName);
      const folderName = resolution.folderName;
      if (!folderName) return null;

      if (this._spriteImageCache.has(folderName)) {
        const cached = this._spriteImageCache.get(folderName);
        return { ...cached, resolvedFolderName: folderName, wasRandomized: resolution.wasRandomized, candidates: resolution.candidates };
      }
      const entry = this.spriteFolders.get(folderName);
      if (!entry) return null;

      let sourceHandle = entry.animations.get('picker');
      let isPicker = true;
      if (!sourceHandle) {
        sourceHandle = entry.animations.get('animate');
        isPicker = false;
      }
      if (!sourceHandle) {
        // fall back to any animation present (e.g. idle.png for Actor sprites)
        const firstKey = entry.animations.keys().next().value;
        if (firstKey) {
          sourceHandle = entry.animations.get(firstKey);
          isPicker = false;
        }
      }
      if (!sourceHandle) return null;

      const img = await loadImageFromFileHandle(sourceHandle);
      const result = this._buildPreview(img, isPicker);
      this._spriteImageCache.set(folderName, result);
      return { ...result, resolvedFolderName: folderName, wasRandomized: resolution.wasRandomized, candidates: resolution.candidates };
    }

    // Loads a specific named animation strip (e.g. "animate", "idle", "run")
    // for a sprite folder, returning frame metadata + the raw image so the
    // caller can draw any frame, scaled to blockSize.
    async getAnimation(folderName, animName) {
      const entry = this.spriteFolders.get(folderName);
      if (!entry) return null;
      const handle = entry.animations.get(animName);
      if (!handle) return null;
      const img = await loadImageFromFileHandle(handle);
      return this._frameInfo(img);
    }

    _frameInfo(img) {
      // Horizontal strip: frame height == image height, frame count == width/height.
      const frameH = img.height;
      const frameCount = Math.max(1, Math.round(img.width / frameH));
      const frameW = img.width / frameCount;
      const scale = this.blockSize / frameH;
      return { img, frameW, frameH, frameCount, scale };
    }

    _buildPreview(img, isPicker) {
      if (isPicker) {
        // Static image, no frame slicing: scale whole image to blockSize tall,
        // preserving aspect ratio for width.
        const scale = this.blockSize / img.height;
        const canvas = document.createElement('canvas');
        canvas.width = img.width * scale;
        canvas.height = this.blockSize;
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, canvas.width, canvas.height);
        return { canvas, frameCount: 1, frameW: canvas.width, frameH: canvas.height };
      }
      // animate.png or similar: take the first frame only for the preview.
      const info = this._frameInfo(img);
      const canvas = document.createElement('canvas');
      canvas.width = info.frameW * info.scale;
      canvas.height = this.blockSize;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(
        info.img,
        0, 0, info.frameW, info.frameH,
        0, 0, canvas.width, canvas.height
      );
      return { canvas, frameCount: info.frameCount, frameW: canvas.width, frameH: canvas.height };
    }
  }

  return { AssetLibrary, walkDirectory, loadImageFromFileHandle };
})();
