import rss from "@astrojs/rss";
import { getCollection } from "astro:content";

export async function GET(context) {
  const posts = await getCollection("blog");
  posts.sort((a, b) => b.data.datePublished.localeCompare(a.data.datePublished));

  return rss({
    title: "China Massage Guide",
    description: "Evidence-based guides, articles, and comparisons about Chinese massage, Tui Na, and TCM bodywork.",
    site: context.site,
    items: posts.map((post) => ({
      title: post.data.title,
      description: post.data.description,
      pubDate: new Date(post.data.datePublished),
      link: `/blog/${post.id}/`,
    })),
    customData: "<language>en-us</language>",
  });
}
