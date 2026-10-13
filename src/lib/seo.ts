// Shared meta-description helpers (answer-first SERP snippets).
export const cl = (v: unknown): string => {
  const raw = String(v ?? "");
  const partial = raw.includes("?");
  let s = raw
    .replace(/<[^>]*>/g, "")
    .replace(/\[\[[^\]|]*\|([^\]]*)\]\]/g, "$1")
    .replace(/\[[^\]|]*\|([^\]]*)\]/g, "$1")
    .replace(/\[\[([^\]]*)\]\]/g, "$1")
    .replace(/[[\]]/g, "")
    .split("|")[0]
    .replace(/[{}]/g, "")
    .replace(/\*+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (partial) {
    s = s.replace(/\?+/g, "").replace(/^[-–—\s,]+|[-–—\s,]+$/g, "").trim();
  }
  return s.replace(/^(?:none|n\/a|-|unknown)$/i, "");
};

export const pick = (...vals: unknown[]): string => {
  for (const v of vals) { const s = cl(v); if (s) return s; }
  return "";
};

const isText = (p: unknown): p is string => typeof p === "string" && p.trim().length > 0;

export const clip = (s: string, n = 158): string => {
  const t = String(s ?? "").replace(/\s+/g, " ").replace(/\s+([.,;:!?])/g, "$1").trim();
  if (t.length <= n) return t;
  return t.slice(0, n - 1).replace(/[\s,;:—–-]+$/, "") + "\u2026";
};

export const desc = (...parts: unknown[]): string =>
  clip(parts.filter(isText).join(" ").replace(/\s+/g, " ").replace(/\s+\./g, "."));

export const stats = (...parts: unknown[]): string => {
  const kept = parts.filter(isText) as string[];
  if (!kept.length) return "";
  return kept.join(", ").replace(/[\s,;:]+$/, "") + ".";
};

export const introSentence = (intro: unknown, n = 150): string => {
  const s = cl(intro);
  if (!s) return "";
  const m = s.match(/^.{40,}?[.!?](?=\s|$)/);
  return clip(m ? m[0] : s, n);
};

export const best = (intro: unknown, fallback: string, minLen = 30, n = 155): string => {
  const s = introSentence(intro, n);
  return s.length >= minLen ? s : fallback;
};
