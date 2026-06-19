// fsio.js
// File System Access API wrapper. Lets the user pick their AgentGlitch
// project root folder once, then locates Assets/ and Levels/ subfolders,
// and provides read/write helpers for .agl/.agd files in place on disk.

const FSIO = (() => {

  function checkSupport() {
    if (!('showDirectoryPicker' in window)) {
      throw new Error(
        'This browser does not support the File System Access API. ' +
        'Please use a recent version of Chrome or Edge.'
      );
    }
  }

  // --- Remembering the last-picked project folder --------------------
  // The File System Access API can't be pointed at an arbitrary absolute
  // path string (a webpage isn't allowed to know your filesystem layout) —
  // but a directory *handle* the user already granted access to can be
  // persisted (here, in IndexedDB) and reused later, including as the
  // `startIn` hint so the native picker opens already inside it. In
  // practice this means: the first time you pick your AgentGlitch folder,
  // every later launch's picker starts right there.

  const DB_NAME = 'agent-glitch-editor';
  const STORE_NAME = 'handles';
  const LAST_ROOT_KEY = 'last-root-handle';

  function openHandleDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        req.result.createObjectStore(STORE_NAME);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function saveLastRootHandle(handle) {
    try {
      const db = await openHandleDB();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        tx.objectStore(STORE_NAME).put(handle, LAST_ROOT_KEY);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch (e) {
      console.warn('Could not persist last-used folder handle:', e);
    }
  }

  async function loadLastRootHandle() {
    try {
      const db = await openHandleDB();
      return await new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const req = tx.objectStore(STORE_NAME).get(LAST_ROOT_KEY);
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => reject(req.error);
      });
    } catch (e) {
      return null;
    }
  }

  async function pickProjectRoot() {
    checkSupport();
    const lastHandle = await loadLastRootHandle();
    const options = { mode: 'readwrite' };
    if (lastHandle) {
      // Re-using the previous handle as startIn opens the native picker
      // already inside (or right alongside) the last folder you chose,
      // rather than wherever the OS feels like defaulting to.
      options.startIn = lastHandle;
    }
    const handle = await window.showDirectoryPicker(options);
    await saveLastRootHandle(handle);
    return handle;
  }

  async function findSubdirectory(rootHandle, name) {
    try {
      return await rootHandle.getDirectoryHandle(name, { create: false });
    } catch (e) {
      return null;
    }
  }

  // Case-insensitive subdirectory lookup, since folder casing has been
  // inconsistent across this project's history ("Assets" vs "assets").
  async function findSubdirectoryCI(rootHandle, name) {
    const exact = await findSubdirectory(rootHandle, name);
    if (exact) return exact;
    const lower = name.toLowerCase();
    for await (const [entryName, handle] of rootHandle.entries()) {
      if (handle.kind === 'directory' && entryName.toLowerCase() === lower) {
        return handle;
      }
    }
    return null;
  }

  async function readTextFile(dirHandle, fileName) {
    const fileHandle = await dirHandle.getFileHandle(fileName, { create: false });
    const file = await fileHandle.getFile();
    return await file.text();
  }

  async function writeTextFile(dirHandle, fileName, contents) {
    const fileHandle = await dirHandle.getFileHandle(fileName, { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(contents);
    await writable.close();
  }

  async function fileExists(dirHandle, fileName) {
    try {
      await dirHandle.getFileHandle(fileName, { create: false });
      return true;
    } catch (e) {
      return false;
    }
  }

  async function listFilesWithExtension(dirHandle, ext) {
    const names = [];
    for await (const [name, handle] of dirHandle.entries()) {
      if (handle.kind === 'file' && name.toLowerCase().endsWith(ext.toLowerCase())) {
        names.push(name);
      }
    }
    return names.sort();
  }

  // Project bundles: locates the Levels folder (Assets/Levels, holding
  // .agl files) and the GameObjects folder (Assets/ReferenceDicts/GameObjects,
  // holding the matching .agd dicts) — these are two different folders, not
  // one, despite both files sharing a base name like "level1a".
  class ProjectIO {
    constructor(rootHandle, assetsHandle, levelsHandle, gameObjectsHandle) {
      this.rootHandle = rootHandle;
      this.assetsHandle = assetsHandle;
      this.levelsHandle = levelsHandle;
      this.gameObjectsHandle = gameObjectsHandle;
    }

    static async open() {
      const rootHandle = await pickProjectRoot();
      const assetsHandle = await findSubdirectoryCI(rootHandle, 'Assets');
      if (!assetsHandle) {
        throw new Error('Could not find an "Assets" folder under the selected directory.');
      }

      let levelsHandle = await findSubdirectoryCI(assetsHandle, 'Levels');
      if (!levelsHandle) {
        // Some layouts may have Levels alongside Assets rather than inside it.
        levelsHandle = await findSubdirectoryCI(rootHandle, 'Levels');
      }
      if (!levelsHandle) {
        throw new Error('Could not find a "Levels" folder under Assets or the project root.');
      }

      let gameObjectsHandle = null;
      const refDicts = await findSubdirectoryCI(assetsHandle, 'ReferenceDicts');
      if (refDicts) {
        gameObjectsHandle = await findSubdirectoryCI(refDicts, 'GameObjects');
      }
      if (!gameObjectsHandle) {
        throw new Error('Could not find "Assets/ReferenceDicts/GameObjects" — that\'s where .agd level dicts are expected to live.');
      }

      return new ProjectIO(rootHandle, assetsHandle, levelsHandle, gameObjectsHandle);
    }

    async listLevels() {
      const aglFiles = await listFilesWithExtension(this.levelsHandle, '.agl');
      return aglFiles.map(f => f.replace(/\.agl$/i, ''));
    }

    async loadLevel(baseName) {
      const aglText = await readTextFile(this.levelsHandle, `${baseName}.agl`);
      let agdText;
      try {
        agdText = await readTextFile(this.gameObjectsHandle, `${baseName}.agd`);
      } catch (e) {
        throw new Error(`Found ${baseName}.agl in Levels but no matching ${baseName}.agd in ReferenceDicts/GameObjects.`);
      }
      return { aglText, agdText };
    }

    async saveLevel(baseName, aglText, agdText) {
      await writeTextFile(this.levelsHandle, `${baseName}.agl`, aglText);
      await writeTextFile(this.gameObjectsHandle, `${baseName}.agd`, agdText);
    }

    async levelExists(baseName) {
      const aglExists = await fileExists(this.levelsHandle, `${baseName}.agl`);
      const agdExists = await fileExists(this.gameObjectsHandle, `${baseName}.agd`);
      return aglExists || agdExists;
    }

    async loadMeta() {
      // meta.agd lives alongside the per-level dicts' parent folder
      // (Assets/ReferenceDicts/), one level up from GameObjects.
      const refDicts = await findSubdirectoryCI(this.assetsHandle, 'ReferenceDicts');
      const dir = refDicts || this.assetsHandle;
      try {
        return await readTextFile(dir, 'meta.agd');
      } catch (e) {
        return null;
      }
    }
  }

  return {
    checkSupport,
    pickProjectRoot,
    findSubdirectory,
    findSubdirectoryCI,
    readTextFile,
    writeTextFile,
    fileExists,
    listFilesWithExtension,
    ProjectIO,
  };
})();
