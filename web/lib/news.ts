export type NewsItem = {
  id: string;
  title: string;
  link: string;
  source: string;
  author: string | null;
  publishedAt: string;
};

const FEEDS: Array<{ source: string; url: string }> = [
  { source: "Federal Reserve", url: "https://www.federalreserve.gov/feeds/press_all.xml" },
  { source: "ECB", url: "https://www.ecb.europa.eu/rss/press.xml" },
  { source: "Bank of England", url: "https://www.bankofengland.co.uk/rss/news" },
  { source: "Financial Times", url: "https://www.ft.com/news-feed?format=rss" },
];

const ITEM_LIMIT_PER_FEED = 25;
const FETCH_TIMEOUT_MS = 8000;

export async function fetchAllNews(): Promise<NewsItem[]> {
  const results = await Promise.allSettled(FEEDS.map((f) => fetchOne(f.source, f.url)));
  const items: NewsItem[] = [];
  for (const r of results) {
    if (r.status === "fulfilled") items.push(...r.value);
  }
  items.sort((a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt));
  return items;
}

async function fetchOne(source: string, url: string): Promise<NewsItem[]> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      cache: "no-store",
      signal: controller.signal,
      headers: { "User-Agent": "MacroHero/1.0 (+https://macrohero.chat)" },
    });
    if (!res.ok) return [];
    const xml = await res.text();
    return parseRSS(xml, source).slice(0, ITEM_LIMIT_PER_FEED);
  } catch {
    return [];
  } finally {
    clearTimeout(t);
  }
}

function parseRSS(xml: string, source: string): NewsItem[] {
  const items: NewsItem[] = [];
  const itemRegex = /<item\b[^>]*>([\s\S]*?)<\/item>/gi;
  let match: RegExpExecArray | null;
  while ((match = itemRegex.exec(xml)) !== null) {
    const block = match[1];
    const title = extractField(block, "title");
    const link = extractField(block, "link");
    const pubDate = extractField(block, "pubDate");
    const author =
      extractField(block, "dc:creator") ||
      extractField(block, "author") ||
      null;
    if (!title || !link || !pubDate) continue;
    const ts = new Date(pubDate);
    if (Number.isNaN(ts.getTime())) continue;
    items.push({
      id: `${source}|${link}`,
      title,
      link,
      source,
      author: author && author.length > 0 ? author : null,
      publishedAt: ts.toISOString(),
    });
  }
  return items;
}

function extractField(block: string, tag: string): string | null {
  const escaped = tag.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`<${escaped}\\b[^>]*>([\\s\\S]*?)<\\/${escaped}>`, "i");
  const m = re.exec(block);
  if (!m) return null;
  let text = m[1].trim();
  const cdata = text.match(/^<!\[CDATA\[([\s\S]*?)\]\]>$/);
  if (cdata) text = cdata[1];
  return decodeEntities(text.trim()) || null;
}

function decodeEntities(s: string): string {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'");
}
