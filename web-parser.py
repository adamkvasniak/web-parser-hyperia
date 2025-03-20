# Vypracované zadanie pre Hyperia - Junior Python Developer
# Autor: Adam Kvasniak 
import json
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

class WebScraper:
    def __init__(self, url):
        """Inicializácia scraperu s danou URL adresou."""
        self.url = url
        self.browser = None
        self.page = None
        self.data = []

    def start_browser(self):
        """Spustí prehliadač Playwright a otvorí stránku."""
        self.browser = sync_playwright().start().chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.page.goto(self.url)

    def close_browser(self):
        """Zavrie prehliadač po skončení scrappingu."""
        if self.browser:
            self.browser.close()

    def extract_dates(self, text):
        """Extrahuje dátumy platnosti (valid_from, valid_to) a formátuje ich na YYYY-MM-DD."""
        text = text.replace("–", "-").strip()  # Normalizácia rôznych pomlčiek

        # Rozpoznanie plného rozsahu dátumov: DD.MM.YYYY - DD.MM.YYYY
        match_range = re.search(r"(\d{2})\.(\d{2})\.?(\d{4})? - (\d{2})\.(\d{2})\.(\d{4})", text)
        if match_range:
            day1, month1, year1, day2, month2, year2 = match_range.groups()
            year1 = year1 if year1 else year2  # Ak chýba prvý rok, použije sa druhý

            valid_from = f"{year1}-{month1}-{day1}"
            valid_to = f"{year2}-{month2}-{day2}"
            return valid_from, valid_to

        # Ak je uvedený iba jeden dátum (napr. 'von Dienstag 15.11.2022')
        match_single = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", text)
        if match_single:
            valid_from_date = datetime.strptime(match_single.group(0), "%d.%m.%Y")
            
            # Ak sa v texte nachádza názov dňa, predpokladá sa 7-dňová platnosť, inak 30 dní
            if re.search(r"Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag", text, re.IGNORECASE):
                valid_to_date = valid_from_date + timedelta(days=7)
            else:
                valid_to_date = valid_from_date + timedelta(days=30)

            valid_from = valid_from_date.strftime("%Y-%m-%d")
            valid_to = valid_to_date.strftime("%Y-%m-%d")
            return valid_from, valid_to

        return "", ""  # Ak sa nepodarí nájsť dátumy, vráti prázdne hodnoty

    def extract_shop_name(self):
        """Extrahuje názov obchodu porovnaním prvej časti odkazu so zoznamom obchodov."""
        # Získanie všetkých odkazov z <div class="letak-description">
        letak_links = self.page.locator(".letak-description a").evaluate_all("elements => elements.map(el => el.getAttribute('href'))")

        # Extrakcia prvej časti odkazu (napr. z /a/b/c → a)
        shop_keys = [link.split('/')[1] if link and '/' in link else "" for link in letak_links]

        # Získanie všetkých obchodov z <ul>, kde <a href="/a/">Názov obchodu</a>
        shop_elements = self.page.locator("#left-category-shops a")
        shop_links = shop_elements.evaluate_all("elements => elements.map(el => el.getAttribute('href'))")
        shop_names = shop_elements.all_text_contents()

        # Vytvorenie mapovania "/a/" → "Názov obchodu"
        shop_mapping = {link.strip("/").split('/')[0]: name for link, name in zip(shop_links, shop_names)}

        # Priradenie názvov obchodov k extrahovaným kľúčom
        return [shop_mapping.get(key, "Neznámy").strip() for key in shop_keys]
        

    def scrape(self):
        """Hlavná metóda na extrakciu všetkých potrebných údajov."""
        self.start_browser()

        # Získanie dátumov platnosti
        date_ranges = self.page.locator(".grid-item-content small.hidden-sm").all_text_contents()
        if not date_ranges:  # Ak hidden-sm neexistuje, použije sa visible-sm
            date_ranges = self.page.locator(".grid-item-content small.visible-sm").all_text_contents()

        # Parsovanie dátumov
        valid_from_list, valid_to_list = zip(*[self.extract_dates(date) for date in date_ranges])

        # Extrakcia titulkov
        titles = self.page.locator(".grid-item-content strong").all_text_contents()

        # Extrakcia URL obrázkov
        thumbnails = self.page.locator(".img-container img").evaluate_all(
            "elements => elements.map(el => el.getAttribute('src') || el.getAttribute('data-src'))"
        )

        # Extrakcia názvov obchodov
        shop_names = self.extract_shop_name()

        self.close_browser()  # Zavretie prehliadača po skončení scrappingu

        # Aktuálny čas parsovania
        parsed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Uloženie dát do JSON
        for i in range(min(len(titles), len(thumbnails), len(valid_from_list), len(valid_to_list), len(shop_names))):
            self.data.append({
                "title": titles[i],
                "thumbnail": thumbnails[i],
                "shop_name": shop_names[i],
                "valid_from": valid_from_list[i],
                "valid_to": valid_to_list[i],
                "parsed_time": parsed_time
            })

        return self.data

    def save_to_json(self, filename="output.json"):
        """Uloží extrahované dáta do JSON súboru."""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def print_data(self):
        """Vypíše extrahované dáta do konzoly."""
        print(json.dumps(self.data, indent=4, ensure_ascii=False))

# Spustenie scraperu
if __name__ == "__main__":
    url = "https://www.prospektmaschine.de/haus-und-garten/"  
    scraper = WebScraper(url)
    parsed_data = scraper.scrape()
    scraper.save_to_json()  # Uloženie výsledkov do JSON 
    scraper.print_data()  