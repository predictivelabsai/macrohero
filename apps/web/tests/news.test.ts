import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

type NewsFeed = {
  source: string;
  url: string;
};

type NewsItem = {
  id: string;
  title: string;
  link: string;
  source: string;
  author: string | null;
  publishedAt: string;
};

const newsModule = (await import(new URL("../lib/news.ts", import.meta.url).href)) as Record<
  string,
  unknown
>;

test("news pane refreshes itself on an interval and cleans it up", () => {
  const source = readFileSync(
    new URL("../app/(app)/chat/news-pane.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /setInterval\(/);
  assert.match(source, /clearInterval\(/);
  assert.match(source, /NEWS_REFRESH_INTERVAL_MS/);
});

test("news sources are focused on FX wires and major FX central banks", () => {
  const feeds = newsModule.NEWS_FEEDS as NewsFeed[] | undefined;

  assert.ok(Array.isArray(feeds), "NEWS_FEEDS should be exported");

  const feedUrls = feeds.map((feed) => feed.url);
  const sources = feeds.map((feed) => feed.source);

  assert.ok(feedUrls.includes("https://investinglive.com/feed/forex/"));
  assert.ok(feedUrls.some((url) => url.includes("investinglive.com/feed/centralbank")));
  assert.ok(feedUrls.some((url) => url.includes("federalreserve.gov/feeds")));
  assert.ok(feedUrls.some((url) => url.includes("ecb.europa.eu/rss/press")));
  assert.ok(feedUrls.some((url) => url.includes("bankofengland.co.uk/rss")));
  assert.ok(feedUrls.some((url) => url.includes("boj.or.jp/en/rss/whatsnew.xml")));
  assert.ok(feedUrls.some((url) => url.includes("rba.gov.au/rss/rss-cb")));
  assert.ok(feedUrls.some((url) => url.includes("bankofcanada.ca/content_type")));
  assert.ok(feedUrls.some((url) => url.includes("snb.ch/public/rss/en/mopo")));
  assert.ok(!sources.includes("Financial Times"));
});

test("parseNewsFeed handles central-bank RDF feeds with dc:date timestamps", () => {
  const parseNewsFeed = newsModule.parseNewsFeed as (
    xml: string,
    source: string,
  ) => NewsItem[];

  assert.equal(typeof parseNewsFeed, "function", "parseNewsFeed should be exported");

  const items = parseNewsFeed(
    `
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:dc="http://purl.org/dc/elements/1.1/">
      <item rdf:about="https://www.bankofcanada.ca/2026/06/fad-press-release-2026-06-10/">
        <title>Bank of Canada maintains the policy rate at 2¼%</title>
        <link>https://www.bankofcanada.ca/2026/06/fad-press-release-2026-06-10/</link>
        <dc:creator>Bank of Canada</dc:creator>
        <dc:date>2026-06-10T09:47:13+00:00</dc:date>
      </item>
    </rdf:RDF>
    `,
    "Bank of Canada",
  );

  assert.equal(items.length, 1);
  assert.equal(items[0].source, "Bank of Canada");
  assert.equal(items[0].author, "Bank of Canada");
  assert.equal(items[0].publishedAt, "2026-06-10T09:47:13.000Z");
});

test("filterCurrentNewsItems excludes future-dated feed entries", () => {
  const filterCurrentNewsItems = newsModule.filterCurrentNewsItems as (
    items: NewsItem[],
    nowMs: number,
  ) => NewsItem[];

  assert.equal(
    typeof filterCurrentNewsItems,
    "function",
    "filterCurrentNewsItems should be exported",
  );

  const items: NewsItem[] = [
    {
      id: "past",
      title: "Published headline",
      link: "https://example.com/past",
      source: "Example",
      author: null,
      publishedAt: "2026-06-22T09:55:00.000Z",
    },
    {
      id: "future",
      title: "Scheduled event",
      link: "https://example.com/future",
      source: "Example",
      author: null,
      publishedAt: "2026-06-22T11:00:00.000Z",
    },
  ];

  const filtered = filterCurrentNewsItems(items, Date.parse("2026-06-22T10:00:00.000Z"));

  assert.deepEqual(
    filtered.map((item) => item.id),
    ["past"],
  );
});
