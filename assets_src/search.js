// Moteur de recherche commun (accords, résumés, dépliants, CCN).
// - petits mots ignorés, pluriels tolérés, apostrophes normalisées
// - synonymes et sigles (liste fermée, vérifiée sur le texte des accords)
// - correction des fautes de frappe (uniquement vers des mots présents dans les textes de la page)
// - liste de mots clés cliquables + suggestions à la saisie
// Un « mot » de requête est une chaîne « a|b|c » : le passage est retenu s'il contient l'une des variantes.
const STOP = new Set(['de','du','des','la','le','les','un','une','au','aux','a','et','ou','en','dans','par','pour','sur','sous','avec','sans','ce','ces','cet','cette','se','sa','son','ses','leur','leurs','que','qui','quoi','est','sont','il','elle','ils','elles','ne','pas','ni','mais','donc','car','y','l','d','s','n','c','j','qu','m','t']);

// Groupes de synonymes (dans les deux sens).
const SYN_GROUPS = [
  ['salaire', 'remuneration'],
  ['heures supplementaires', 'heures sup'],
  ['teletravail', 'travail a domicile', 'travail a distance'],
  ['nuit', 'nocturne'],
  ['mutuelle', 'complementaire sante', 'frais de sante'],
  ['arret maladie', 'arret de travail'],
  ['grossesse', 'enceinte', 'maternite'],
  ['restauration', 'repas', 'cantine'],
  ['preavis', 'delai de prevenance'],
  ['licenciement', 'rupture du contrat'],
  ['demission', 'depart volontaire'],
  ['dreets', 'direccte'],
  ['percol', 'epargne retraite'],
  ['temps partiel', 'mi temps'],
  ['fin de carriere', 'senior']
];
// Sens unique : ce que l'on tape -> ce qu'on cherche en plus.
const SYN_ONE_WAY = {
  'paie': ['salaire', 'remuneration'],
  'paye': ['salaire', 'remuneration'],
  'tele travail': ['teletravail'],
  'hs': ['heures supplementaires'],
  'cet': ['compte epargne temps'],
  'att': ['amenagement du temps de travail'],
  'vap': ['validation des acquis professionnels'],
  'cse': ['comite social et economique'],
  'cssct': ['commission sante securite et conditions de travail'],
  'lrar': ['lettre recommandee'],
  'rtt': ['reduction du temps de travail'],
  'pee': ["plan d'epargne d'entreprise"],
  'rqth': ['handicap'],
  'velo': ['forfait mobilite'],
  'covoiturage': ['forfait mobilite'],
  'comite social et economique': ['cse'],
  'reduction du temps de travail': ['rtt'],
  "plan d'epargne d'entreprise": ['pee'],
  'validation des acquis professionnels': ['vap'],
  'compte epargne temps': ['cet']
};
const SYN = {};
SYN_GROUPS.forEach(g => g.forEach(t => { SYN[t] = (SYN[t] || []).concat(g.filter(x => x !== t)); }));
Object.keys(SYN_ONE_WAY).forEach(k => { SYN[k] = (SYN[k] || []).concat(SYN_ONE_WAY[k]); });
const PHRASE_KEYS = Object.keys(SYN).filter(k => k.indexOf(' ') !== -1 || k.indexOf("'") !== -1).sort((a, b) => b.length - a.length);

// ---- Vocabulaire (pour la correction des fautes de frappe) ----
let vocabSource = null;
let VOCAB = null;
function setVocabSource(fn) { vocabSource = fn; VOCAB = null; }
function getVocab() {
  if (VOCAB) return VOCAB;
  VOCAB = new Map();
  const texts = vocabSource ? vocabSource() : [];
  texts.forEach(t => {
    (t.match(/[a-z0-9]{4,}/g) || []).forEach(w => VOCAB.set(w, (VOCAB.get(w) || 0) + 1));
  });
  VOCAB_SORTED = Array.from(VOCAB.keys()).sort();
  return VOCAB;
}
let VOCAB_SORTED = [];
function vocabHasPrefix(w) {
  getVocab();
  let lo = 0, hi = VOCAB_SORTED.length;
  while (lo < hi) { const m = (lo + hi) >> 1; if (VOCAB_SORTED[m] < w) lo = m + 1; else hi = m; }
  return lo < VOCAB_SORTED.length && VOCAB_SORTED[lo].startsWith(w);
}
// Distance de Damerau-Levenshtein (avec transposition), plafonnée.
function editDist(a, b, max) {
  const la = a.length, lb = b.length;
  if (Math.abs(la - lb) > max) return max + 1;
  let prev2 = null, prev = [];
  for (let j = 0; j <= lb; j++) prev.push(j);
  for (let i = 1; i <= la; i++) {
    const cur = [i];
    let best = i;
    for (let j = 1; j <= lb; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      let v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
      if (prev2 && i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) v = Math.min(v, prev2[j - 2] + 1);
      cur.push(v);
      if (v < best) best = v;
    }
    if (best > max) return max + 1;
    prev2 = prev; prev = cur;
  }
  return prev[lb];
}
function typoFix(w) {
  if (w.length < 5 || vocabHasPrefix(w)) return null;
  const max = w.length >= 9 ? 2 : 1;
  const v = getVocab();
  let best = [];
  let bestD = max + 1;
  VOCAB_SORTED.forEach(c => {
    if (Math.abs(c.length - w.length) > max) return;
    const d = editDist(w, c, max);
    if (d > max) return;
    if (d < bestD) { bestD = d; best = [c]; } else if (d === bestD) best.push(c);
  });
  if (!best.length) return null;
  best.sort((x, y) => v.get(y) - v.get(x));
  return best.slice(0, 2);
}

// ---- Note affichée sous la barre de recherche ----
let lastNoteKey = null;
function setSearchNote(corr, syn) {
  const key = JSON.stringify([corr, syn]);
  if (key === lastNoteKey) return;
  lastNoteKey = key;
  const inp = document.querySelector('.search-bar input');
  if (!inp) return;
  const bar = inp.closest('.search-bar');
  let el = document.getElementById('search-note');
  if (!el) {
    el = document.createElement('div');
    el.id = 'search-note';
    el.className = 'search-note';
    bar.parentNode.insertBefore(el, bar.nextSibling);
  }
  const parts = [];
  if (corr.length) parts.push('Faute de frappe corrigée : ' + corr.map(c => '« ' + c[0] + ' » → « ' + c[1] + ' »').join(', '));
  if (syn.length) parts.push('Recherche élargie à : ' + syn.map(s => s[0] + ' (' + s[1].join(', ') + ')').join(' ; '));
  el.textContent = parts.join(' — ');
  el.style.display = parts.length ? 'block' : 'none';
}

function queryWords(q) {
  q = q.replace(/[’‘`]/g, "'");
  let rest = ' ' + q + ' ';
  const toks = [], corr = [], syn = [];
  PHRASE_KEYS.forEach(k => {
    const re = new RegExp('(^|[^a-z0-9])' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![a-z0-9])');
    if (re.test(rest)) {
      rest = rest.replace(re, ' ');
      toks.push([k].concat(SYN[k]));
      syn.push([k, SYN[k]]);
    }
  });
  const ws = rest.split(/[^a-z0-9]+/).filter(w => w.length >= 2);
  let k = ws.filter(w => !STOP.has(w));
  if (!k.length && !toks.length) k = ws;
  k = [...new Set(k.map(w => (w.length > 4 && /[sx]$/.test(w)) ? w.slice(0, -1) : w))];
  k.forEach(w => {
    const alts = [w];
    (SYN[w] || []).forEach(s => alts.push(s));
    if (SYN[w]) syn.push([w, SYN[w]]);
    const fix = typoFix(w);
    if (fix) { fix.forEach(f => alts.push(f)); corr.push([w, fix[0]]); }
    toks.push(alts);
  });
  setSearchNote(corr, syn);
  return toks.map(a => a.join('|'));
}
function altTerms(ts) { return ts.flatMap(t => t.split('|')).filter(Boolean); }
function atWordStart(nt, i) { return i === 0 || !/[a-z0-9]/.test(nt[i - 1]); }
// Un terme n'est retenu qu'en début de mot : « formation » trouve « formations » mais pas « information ».
function hasTerm(nt, t) {
  const alts = t.indexOf('|') === -1 ? [t] : t.split('|');
  for (const a of alts) {
    let i = 0;
    while ((i = nt.indexOf(a, i)) !== -1) {
      // sigles courts (cet, cse, rtt...) : mot entier seulement, pour ne pas trouver « cette »
      const endOk = a.length > 3 || !/[a-z0-9]/.test(nt[i + a.length] || ' ');
      if (atWordStart(nt, i) && endOk) return true;
      i += 1;
    }
  }
  return false;
}
function hasAlt(t, w) { return w.split('|').some(x => t.includes(x)); }
// Passages contenant le mot tel que tapé en premier.
function litFirst(arr, get, q) {
  const lit = [], oth = [];
  arr.forEach(p => (hasTerm(get(p), q) ? lit : oth).push(p));
  return lit.concat(oth);
}

// ---- Mots clés cliquables (relevés dans les accords, présents dans au moins 2 documents) ----
const KEYWORDS = ['congés', 'maternité', 'heures supplémentaires', 'astreinte', 'travail de nuit', 'temps partiel',
  'télétravail', 'compte épargne temps', 'forfait jours', 'prime', 'indemnité', 'ancienneté', 'préavis', 'retraite',
  'mutuelle', 'prévoyance', 'arrêt maladie', 'décès', 'handicap', 'formation', 'intéressement', 'épargne salariale',
  'don de jours', 'congé humanitaire', 'égalité professionnelle', 'déconnexion', 'chèques syndicaux',
  'vote électronique', 'mobilité durable', 'jours fériés', 'dimanche', 'rémunération', 'CDD', 'licenciement',
  'transport', 'entretien professionnel', 'indemnité de départ', 'reprise d\'ancienneté', 'frais de santé',
  'harcèlement', 'apprentissage', 'validation des acquis'];
const KW_TOP = 14;
function initKeywords() {
  const inp = document.querySelector('.search-bar input');
  if (!inp || document.getElementById('kw-row')) return;
  const dl = document.createElement('datalist');
  dl.id = 'kw-list';
  KEYWORDS.slice().sort((a, b) => a.localeCompare(b, 'fr')).forEach(k => { const o = document.createElement('option'); o.value = k; dl.appendChild(o); });
  document.body.appendChild(dl);
  inp.setAttribute('list', 'kw-list');
  inp.setAttribute('autocomplete', 'off');
  const bar = inp.closest('.search-bar');
  const row = document.createElement('div');
  row.id = 'kw-row';
  row.className = 'kw-row';
  const lab = document.createElement('span');
  lab.className = 'kw-label';
  lab.textContent = 'Mots clés :';
  row.appendChild(lab);
  const pick = k => { inp.value = k; inp.dispatchEvent(new Event('input', { bubbles: true })); inp.focus(); };
  KEYWORDS.forEach((k, i) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'kw' + (i >= KW_TOP ? ' kw-extra' : '');
    b.textContent = k;
    if (i >= KW_TOP) b.style.display = 'none';
    b.addEventListener('click', () => pick(k));
    row.appendChild(b);
  });
  const more = document.createElement('button');
  more.type = 'button';
  more.className = 'kw kw-more';
  more.textContent = 'Plus de mots clés';
  more.addEventListener('click', () => {
    const open = more.dataset.open !== '1';
    more.dataset.open = open ? '1' : '0';
    row.querySelectorAll('.kw-extra').forEach(b => { b.style.display = open ? '' : 'none'; });
    more.textContent = open ? 'Moins de mots clés' : 'Plus de mots clés';
  });
  row.appendChild(more);
  bar.parentNode.insertBefore(row, bar.nextSibling);
  inp.addEventListener('input', () => { if (!inp.value.trim()) setSearchNote([], []); });
}
