/**
 * The shape of web/.data/wiki.json, written by scripts/extract_wiki.py from the wiki's data.
 * Mirrors the Python exactly; when the extractor changes, this file changes with it.
 */

export type Lang = "ja" | "en" | "es" | "fr" | "zh" | "ko" | "pt-br" | "it" | "ar" | "ru" | "id" | "de" | "tr";
export type Dir = "ltr" | "rtl";

export interface FileFacts {
  name: string;
  url: string;
  bytes: number;
  bytesDisplay: string;
  sizeDisplay: string;
  sha256: string;
}

export interface NativeFile extends FileFacts {
  platform: string;
  label: string;
  ext: string;
}

export interface Requirement {
  label: string;
  value: string;
}

export type Availability = "available" | "soon" | "archived";

/** A model's current file on its own page (ASTRAEA, Tsubomi, Noctua). */
export interface ModelDownload {
  version: string;
  requirements: Requirement[];
  file: FileFacts;
}

export interface Product {
  id: string;
  name: string;
  jp: string | null;
  availability: Availability;
  category: string;
  badge: string | null;
  tagline: string;
  headline: string;
  story: string | null;
  icon: string;
  art: string | null;
  version: string;
  compat: string;
  href: string;
  requires: string[];
  about: string;
  lede?: string;
}

/** Cherry Controls inline grammar. */
export type ControlToken =
  | string
  | { t: "key"; id: string; label: string; dir: Dir }
  | { t: "en"; v: string }
  | { t: "release"; v: string }
  | { t: "path"; steps: string[]; sep: string }
  | { t: "nobreak"; v: string };

export interface ControlCard {
  id: string;
  anchor: string;
  title: ControlToken[];
  facts: ControlToken[][];
  keys: { action: ControlToken[]; how: ControlToken[] }[];
  lists: { title: ControlToken[]; items: ControlToken[][] }[];
}

export interface Release {
  id: string;
  brand: string;
  version: string;
  date: string | null;
  type: string;
  series: string;
  title: string;
  summary: string;
  highlights: string[];
  balance: string[];
  warnings: string[];
  limits: string[];
  paragraphs?: string[];
}

export interface ChangelogBrand {
  id: string;
  name: string;
  releases: Release[];
}

export interface RecipeShared {
  total: number;
  sources: Record<string, string>;
  cats: { index: number; name: string; icon: string | null; count: number }[];
  allTabIcon: string | null;
  items: Record<string, { ja: string; en: string; icon: string | null; kind: "flat" | "cube" | "icon" | "none" }>;
  recipes: {
    key: string;
    cat: number;
    result: string;
    count: number;
    grid: (string | 0)[] | null;
    station: string;
    search: string;
    how?: string;
    fusion?: { id: string; n: number }[];
    /** A machine recipe (data/recipes_machines.json): its inputs ("any": a tag or alternatives), every output. */
    inputs?: { id: string; n: number; any?: boolean }[];
    outputs?: { id: string; n: number; nMax?: number; chance?: number; every?: number }[];
    facts?: { time?: number; water?: number; xp?: number; dimension?: "overworld" | "nether" | "end"; share?: number };
  }[];
  stations: { id: string; item: string | null; count: number }[];
  kindsUnknown: string[];
}

export interface RecipeLabels {
  search: string;
  countSuffix: string;
  empty: string;
  all: string;
  howTo: string;
  noRecipe: string;
  stations: string;
  stationNoneFabricator: string;
  stationNoneTsubomi: string;
  selectPrompt: string;
  tree: string;
  madeIn: string;
  recipeN: string;
  tsubomiName: string;
  preview: { title: string; pause: string; rotate: string; drag: string; note: Record<"flat" | "cube" | "icon" | "none", string> };
  machine: {
    any: string;
    outputs: string;
    chance: string;
    /** A by-product that comes out only on every Nth completed run (OUKA 1.6.0); counted, not a chance. */
    every: string;
    time: string;
    water: string;
    xp: string;
    vein: string;
    drill: string;
    overworld: string;
    nether: string;
    end: string;
  };
}

export interface ChangelogLabels {
  brand: string;
  all: string;
  allSeries: string;
  series: string;
  search: string;
  empty: string;
  updated: string;
  note: string;
  showMore: string;
  showFewer: string;
  highlights: string;
  balance: string;
  warnings: string;
  limits: string;
  corvusNote: string;
  types: Record<string, string>;
  none: string;
}

export interface SkinLabels {
  lede: string;
  note: string;
  slim: string;
  pinLabel: string;
  unlock: string;
  working: string;
  wrong: string;
  done: string;
  downloadPng: string;
  locked: string;
  lockedHint: string;
  unlocked: string;
  pose: string;
  poses: { stand: string; wave: string; t: string; sit: string };
  walk: string;
  drag: string;
  noWebgl: string;
  blobError: string;
}

export interface StoreText {
  lang: string;
  dir: Dir;
  discover: string;
  mods: string;
  library: string;
  updates: string;
  search: string;
  noResults: string;
  searchHint: string;
  libraryEmptyTitle: string;
  libraryEmptyBody: string;
  browse: string;
  updatesEmptyTitle: string;
  updatesEmptyBody: string;
  updatesAvailable: string;
  account: string;
  autoUpdateTitle: string;
  autoUpdateDesc: string;
  featured: string;
  category: string;
  compat: string;
  version: string;
  get: string;
  open: string;
  update: string;
  archived: string;
  comingSoon: string;
  stop: string;
  close: string;
  available: string;
  archivedTitle: string;
  archivedBody: string;
  demoNote: string;
  demoOpen: string;
  simulate: string;
  updateAll: string;
  reset: string;
  settingsNote: string;
  region: string;
  readMore: string;
  announce: { started: string; stopped: string; done: string; update: string; nothing: string; reset: string };
}

export interface LangData {
  lang: Lang;
  dir: Dir;
  hreflang: string;
  name: string;
  chrome: {
    siteTitle: string;
    skipLink: string;
    home: string;
    launcher: string;
    brands: string;
    recipes: string;
    changelog: string;
    upcoming: string;
    skin: string;
    discord: string;
    download: string;
    menu: string;
    close: string;
    language: string;
    primary: string;
    footerBrands: string;
    footerGetStarted: string;
    footerReference: string;
    footerStatus: string;
    legalTitle: string;
    tagline: string;
    footerNote: string;
    arrow: string;
    copy: string;
    copied: string;
    fileSize: string;
    sha256: string;
    version: string;
    launcherVersion: string;
    primaryCta: string;
  };
  home: {
    title: string;
    eyebrow: string;
    sub: string;
    description: string;
    ctaStore: string;
    symbolLabel: string;
    brandsTitle: string;
    hint: string;
    explore: string;
    skinTile: string;
    storeTagline: string;
  };
  products: Record<string, Product>;
  launcher: {
    title: string;
    description: string;
    hub: { title: string; tagline: string; brandsTitle: string; brandsHint: string; scroll: string; skip: string; downloadLabel: string };
    text: StoreText;
    modsHeading: string;
    macNote: string;
    whatsNew: string;
    notesEnglishOnly: string;
    versionHistory: string;
    guideTitle: string;
    guideNote: string;
    guideIntro: string;
    guide: { id: string; title: string; html: string }[];
    body: string;
    nativeNote: string;
    nativeHeading: string;
    jarNote: string;
    cta: string;
    perch: Record<string, string>;
    perchToggle: { title: string; description: string };
    storeStrings: Record<string, string>;
  };
  launcherFiles: { version: string; native: NativeFile[]; jar: FileFacts; notes: string[] };
  download: {
    title: string;
    heading: string;
    description: string;
    body: string;
    nativeHeading: string;
    nativeNote: string;
    changelogLink: string;
    aureum: { heading: string; body: string; note: string; cta: string; version: string; file: FileFacts };
    astraea: ModelDownload | null;
    tsubomi: ModelDownload | null;
    halia: ModelDownload | null;
    agent: ModelDownload | null;
    noctua: ModelDownload | null;
    discord: { heading: string; body: string; cta: string };
    alphaNote: string;
    alphaVersion: string;
  };
  brands: {
    ouka: {
      title: string;
      description: string;
      eyebrow: string;
      line: string;
      player: { track: string; play: string; pause: string };
      release: { version: string; codename: string; file: FileFacts; requirements: Requirement[] };
    };
    cherry: {
      title: string;
      description: string;
      eyebrow: string;
      line: string;
      controlsLabel: string;
      release: { version: string; codename: string; file: FileFacts; requirements: Requirement[] };
    };
    aureum: {
      title: string;
      description: string;
      version: string;
      tagline: string;
      download: { label: string; url: string };
      detailsLabel: string;
      statsHeading: string;
      stats: { value: string; label: string }[];
      sections: { heading: string; paragraphs: string[]; requirements?: { heading: string; items: string[] } }[];
      closingLine: string;
      sha256: string;
    };
    controls: {
      title: string;
      description: string;
      heading: string;
      controlsFor: string;
      note: ControlToken[];
      layout: ControlToken[];
      cards: ControlCard[];
    };
  };
  alpha: {
    title: string;
    description: string;
    version: string;
    lede: string;
    ctaRetirement: string;
    ctaChangelog: string;
    sections: { heading: string; body: string }[];
  };
  changelog: {
    title: string;
    description: string;
    labels: ChangelogLabels;
    noteBrands: string[];
    brands: ChangelogBrand[];
  };
  recipes: {
    title: string;
    navTitle: string;
    description: string;
    intro: string;
    labels: RecipeLabels;
    names: Record<string, string>;
    subs: Record<string, string>;
    search: Record<string, string>;
    catNames: string[];
  };
  skin: { title: string; description: string; labels: SkinLabels };
  /** Every advance notice the Coming-next board has published (data/teasers.json), newest first. */
  teasers: Teaser[];
  upcoming: {
    title: string;
    description: string;
    intro: string;
    disclaimer: string;
    more: string;
    nodes: { id: string; kind: string; icon: string; status: string; headline: string; body: string; href: string; linkName: string }[];
  };
  discord: {
    title: string;
    nav: string;
    description: string;
    lede: string;
    invite: string;
    invite_note: string;
    setup_title: string;
    s1_h: string;
    s1_p: string;
    s2_h: string;
    s2_p: string;
    s3_h: string;
    s3_p: string;
    s4_h: string;
    s4_p: string;
    cmds_title: string;
    th_cmd: string;
    th_what: string;
    th_who: string;
    who_all: string;
    who_admin: string;
    posts_title: string;
    posts_p: string;
    post_update: string;
    post_upcoming: string;
    post_intake: string;
    lang_title: string;
    lang_p: string;
    lang_note: string;
    privacy_title: string;
    privacy_p: string;
    rate_note: string;
    eyebrow: string;
    status: {
      statusTitle: string;
      statusInvite: string;
      statusPermissions: string;
      statusLatest: string;
      statusFeed: string;
      published: string;
      statusNote: string;
    };
    groups: { name: string; gloss: string; subcommands: { name: string; admin: boolean; gloss: string; params: string[] }[] }[];
  };
  notFound: { heading: string; body: string };
  typeBadge: Record<string, string>;
  pageTitles: Record<string, string>;
}

/** One film the studio has posted (data/announcements.json). */
export interface Film {
  id: string;
  brand: string;
  kind: "trailer" | "launch" | "teaser" | "film" | "indev";
  date: string;
  title: string;
  seconds: number;
  file: string;
  poster: string;
  bytes: number;
}

export interface Wiki {
  schema: string;
  films: Film[];
  build: { commit: string; branch: string; dataDirty: boolean };
  site: {
    title: string;
    baseUrl: string;
    basePath: string;
    sections: string[];
    languages: { code: Lang; name: string; dir: Dir; hreflang: string }[];
    notFoundTitle: string;
  };
  versions: Record<string, string>;
  store: { jar: string; version: string };
  discord: {
    clientId: string;
    permissions: string;
    invite: string | null;
    languages: string[];
    languageNames: Record<string, string>;
    routeKinds: string[];
    latest: { title: string; date: string };
    feed: { date: string; count: number };
  };
  skinGate: {
    blob: string;
    plain_name: string;
    plain_sha256: string;
    plain_bytes: number;
    salt_hex: string;
    iterations: number;
    magic: string;
  };
  /** The public skin (data/skin_public.json), or null while the skin is sealed. */
  skinPublic: { file: string; name: string; sha256: string; bytes: number } | null;
  recipes: RecipeShared;
  alpha: { retired: boolean; version: string; date: string; modules: number };
  langs: Record<Lang, LangData>;
}

/** One advance notice of the Coming-next board, kept after it left the board. */
export interface Teaser {
  id: string;
  /** The brand it announced (ouka, cherry, ...): the icon, the colour and the changelog filter. */
  brand: string;
  name: string;
  icon: string;
  /** The day it first appeared on the board, and the day it left it (null while it is still there). */
  announced: string;
  retired: string | null;
  headline: string;
  target: string;
  body: string;
  items: string[];
  /** The page it pointed at (the brand's own page), relative to the language root. */
  href: string;
}
