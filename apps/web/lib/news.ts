export type NewsItem = {
  id: string;
  title: string;
  link: string;
  source: string;
  author: string | null;
  publishedAt: string;
};

type NewsFeed = {
  source: string;
  url: string;
};

export const NEWS_FEEDS: NewsFeed[] = [
  { source: "InvestingLive Forex", url: "https://investinglive.com/feed/forex/" },
  {
    source: "InvestingLive Central Banks",
    url: "https://investinglive.com/feed/centralbank/",
  },
  { source: "InvestingLive FX Orders", url: "https://investinglive.com/feed/forexorders/" },
  { source: "Investing.com Forex", url: "https://www.investing.com/rss/news_1.rss" },
  { source: "Federal Reserve", url: "https://www.federalreserve.gov/feeds/press_all.xml" },
  { source: "Fed Speeches", url: "https://www.federalreserve.gov/feeds/speeches.xml" },
  { source: "ECB", url: "https://www.ecb.europa.eu/rss/press.xml" },
  { source: "Bank of England", url: "https://www.bankofengland.co.uk/rss/news" },
  { source: "BoE Speeches", url: "https://www.bankofengland.co.uk/rss/speeches" },
  { source: "Bank of Japan", url: "https://www.boj.or.jp/en/rss/whatsnew.xml" },
  { source: "RBA", url: "https://www.rba.gov.au/rss/rss-cb-media-releases.xml" },
  { source: "RBA Speeches", url: "https://www.rba.gov.au/rss/rss-cb-speeches.xml" },
  {
    source: "Bank of Canada",
    url: "https://www.bankofcanada.ca/content_type/press-releases/feed/",
  },
  { source: "BoC Speeches", url: "https://www.bankofcanada.ca/content_type/speeches/feed/" },
  { source: "SNB Monetary Policy", url: "https://www.snb.ch/public/rss/en/mopo" },
  { source: "SNB Speeches", url: "https://www.snb.ch/public/rss/en/speeches" },
];

const ITEM_LIMIT_PER_FEED = 15;
const TOTAL_ITEM_LIMIT = 120;
const FETCH_TIMEOUT_MS = 8000;
const FUTURE_ITEM_TOLERANCE_MS = 5 * 60 * 1000;

export async function fetchAllNews(): Promise<NewsItem[]> {
  const results = await Promise.allSettled(
    NEWS_FEEDS.map((feed) => fetchOne(feed.source, feed.url)),
  );
  const items: NewsItem[] = [];
  const seenLinks = new Set<string>();
  for (const r of results) {
    if (r.status !== "fulfilled") continue;
    for (const item of r.value) {
      if (seenLinks.has(item.link)) continue;
      seenLinks.add(item.link);
      items.push(item);
    }
  }
  const currentItems = filterCurrentNewsItems(items);
  currentItems.sort((a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt));
  return currentItems.slice(0, TOTAL_ITEM_LIMIT);
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
    return parseNewsFeed(xml, source).slice(0, ITEM_LIMIT_PER_FEED);
  } catch {
    return [];
  } finally {
    clearTimeout(t);
  }
}

export function parseNewsFeed(xml: string, source: string): NewsItem[] {
  return [
    ...parseBlocks(xml, "item", source),
    ...parseBlocks(xml, "entry", source),
  ];
}

export function filterCurrentNewsItems(items: NewsItem[], nowMs = Date.now()): NewsItem[] {
  return items.filter((item) => {
    const publishedAt = Date.parse(item.publishedAt);
    return Number.isFinite(publishedAt) && publishedAt <= nowMs + FUTURE_ITEM_TOLERANCE_MS;
  });
}

function parseBlocks(xml: string, tag: "item" | "entry", source: string): NewsItem[] {
  const items: NewsItem[] = [];
  const blockRegex = new RegExp(`<${tag}\\b[^>]*>([\\s\\S]*?)<\\/${tag}>`, "gi");
  let match: RegExpExecArray | null;
  while ((match = blockRegex.exec(xml)) !== null) {
    const block = match[1];
    const title = extractField(block, "title");
    const link = extractLink(block);
    const pubDate =
      extractField(block, "pubDate") ||
      extractField(block, "dc:date") ||
      extractField(block, "published") ||
      extractField(block, "updated");
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

function extractLink(block: string): string | null {
  const textLink = extractField(block, "link");
  if (textLink) return textLink;

  const href = /<link\b[^>]*\bhref=["']([^"']+)["'][^>]*\/?>/i.exec(block);
  return href ? decodeEntities(href[1].trim()) || null : null;
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
    .replace(/&#x([0-9a-f]+);/gi, (_, hex: string) =>
      String.fromCodePoint(Number.parseInt(hex, 16)),
    )
    .replace(/&#(\d+);/g, (_, decimal: string) =>
      String.fromCodePoint(Number.parseInt(decimal, 10)),
    )
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'");
}
