### For testing purpose

from crawler.crawler import crawl_site

machin = crawl_site("https://press.accor.com/premier-semestre-2025une-activite-solide-dans-un-contextemacro-economique-complexe?lang=fra", max_depth=20, max_pages=30, delay=0.5, respect_robots=False)
print(machin)
