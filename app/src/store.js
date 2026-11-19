// Job storage: Firestore on Google Cloud, JSON file locally. Same interface for both.
import fs from 'node:fs';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { config } from './config.js';

export const events = new EventEmitter(); // emits 'job' with the latest job doc

class FileStore {
  constructor(file) {
    this.file = file;
    fs.mkdirSync(path.dirname(file), { recursive: true });
    this.jobs = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {};
  }
  async save(job) {
    this.jobs[job.id] = job;
    fs.writeFileSync(this.file, JSON.stringify(this.jobs, null, 2));
    return job;
  }
  async list(limit = 50) {
    return Object.values(this.jobs).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).slice(0, limit);
  }
  async get(id) {
    return this.jobs[id] || null;
  }
}

class FirestoreStore {
  constructor() {
    this.ready = (async () => {
      const { initializeApp, applicationDefault, getApps } = await import('firebase-admin/app');
      const { getFirestore } = await import('firebase-admin/firestore');
      if (!getApps().length) initializeApp({ credential: applicationDefault(), projectId: config.project });
      this.col = getFirestore().collection('jobs');
    })();
  }
  async save(job) {
    await this.ready;
    await this.col.doc(job.id).set(JSON.parse(JSON.stringify(job)));
    return job;
  }
  async list(limit = 50) {
    await this.ready;
    const snap = await this.col.orderBy('updatedAt', 'desc').limit(limit).get();
    return snap.docs.map((d) => d.data());
  }
  async get(id) {
    await this.ready;
    const d = await this.col.doc(id).get();
    return d.exists ? d.data() : null;
  }
}

const impl = config.store === 'firestore' ? new FirestoreStore() : new FileStore(config.dataFile);
console.log(`[store] using ${config.store}`);

export const store = {
  async save(job) {
    job.updatedAt = new Date().toISOString();
    const saved = await impl.save(job);
    events.emit('job', summary(saved));
    return saved;
  },
  list: (n) => impl.list(n),
  get: (id) => impl.get(id),
};

// Light version for the live dashboard feed (no photos).
export function summary(job) {
  const { photos, transcript, ...rest } = job;
  return { ...rest, hasPhotos: Boolean(photos?.before || photos?.after) };
}
