// Met en cache la page et toutes les images pour un usage hors ligne.
const VERSION = '53ced9075d';
const CACHE = 'especes-corse-' + VERSION;
const ASSETS = [
 "./",
 "index.html",
 "manifest.json",
 "icons/icon-192.png",
 "icons/icon-512.png",
 "icons/apple-touch-icon.png",
 "images/merou-brun.jpg",
 "images/corb.jpg",
 "images/denti.jpg",
 "images/barracuda.jpg",
 "images/sar-commun.jpg",
 "images/sar-tete-noire.jpg",
 "images/saupe.jpg",
 "images/castagnole.jpg",
 "images/girelle-commune.jpg",
 "images/girelle-paon.jpg",
 "images/serran-ecriture.jpg",
 "images/murene.jpg",
 "images/congre.jpg",
 "images/rascasse-rouge.jpg",
 "images/barbier.jpg",
 "images/rouget-de-roche.jpg",
 "images/poulpe.jpg",
 "images/seiche.jpg",
 "images/langouste-rouge.jpg",
 "images/cigale-de-mer.jpg",
 "images/gorgone-rouge.jpg",
 "images/gorgone-jaune.jpg",
 "images/corail-rouge.jpg",
 "images/grande-nacre.jpg",
 "images/spirographe.jpg",
 "images/etoile-de-mer-rouge.jpg",
 "images/flabelline.jpg",
 "images/doris-dalmatien.jpg",
 "images/ver-de-feu.jpg",
 "images/anemone-verte.jpg",
 "images/posidonie.jpg",
 "images/padine.jpg",
 "images/caulerpe.jpg"
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request).then(res => {
      if (res.ok && new URL(e.request.url).origin === location.origin) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return res;
    }))
  );
});
