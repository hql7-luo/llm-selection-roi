"""25 hard and 15 trap inquiries, written by hand, each with its answer key.

Hard cases test reading, not pattern matching: corrections, old numbers next to new ones,
quantities in words or containers, prices per 1,000, dates relative to the email date,
Russian or mixed-language text. Trap cases are messages that look like inquiries but are not
(spam, phishing, fee scams, products we do not sell). Every company and person is fictional.
"""

from .labels import gold_record, item

# Each case: id, language, format, received date, text, then what the email actually asks for
HARD = [
    dict(id="H01", language="en", format="email", received="2026-10-06",
         text="Subject: RE: carton quote\n\nHi,\n\nFollowing up on my email from Monday: please change the quantity. "
              "We now need 12,000 pcs instead of 10,000 pcs of the folding cartons 90x60x150 mm, 350gsm. "
              "Same terms as before, FOB Ningbo.\n\nThanks,\nJonas\nNordkarton GmbH",
         items=[item("folding_carton", ["90x60x150", "350gsm"], 12000)], incoterm="FOB"),
    dict(id="H02", language="en", format="email", received="2026-10-08",
         text="Dear supplier,\n\nLast year we bought 5,000 sqm of thermal CTP plates from another factory. "
              "This year our volume is lower, around 3,500 sqm, size 1030x790, 0.30 mm. Please offer CIF "
              "Novorossiysk, delivery before 30 November.\n\nRegards,\nAndrey, Polygraph-Resurs LLC",
         items=[item("ctp_plate", ["1030x790", "0.3mm"], 3500)], incoterm="CIF",
         destination="Novorossiysk", delivery="2026-11-30"),
    dict(id="H03", language="en", format="email", received="2026-10-03",
         text="Hello,\n\nPlease quote the following for our Minsk plant:\n1) Printing blankets 1050x840x1.95 mm: 80 pcs\n"
              "2) Fountain solution, alcohol-free: 600 L\n\nTerms DAP Minsk. Delivery within 45 days.\n\n"
              "Pavel\nMinsk Label House",
         items=[item("blanket", ["1050x840", "1.95mm"], 80), item("fountain_solution", ["alcohol-free"], 600)],
         incoterm="DAP", destination="Minsk", delivery="45 days"),
    dict(id="H04", language="en", format="chat", received="2026-10-10",
         text="pls quote 25k self-adhesive labels 50x30mm semi gloss, CFR Jebel Ali. target USD 9 per 1000 pcs\n"
              "Rashid / Gulf Print Trading",
         items=[item("label", ["50x30", "semi-gloss"], 25000, price=0.009)], incoterm="CFR",
         destination="Jebel Ali"),
    dict(id="H05", language="ru", format="email", received="2026-10-05",
         text="Добрый день!\n\nНужен увлажняющий раствор без спирта, 50 канистр по 20 л. Поставка DAP Алматы, "
              "до 20.11.2026.\n\nАйгерим, Steppe Print LLP",
         items=[item("fountain_solution", ["alcohol-free"], 1000)], incoterm="DAP", destination="Almaty",
         delivery="2026-11-20"),
    dict(id="H06", language="en", format="email", received="2026-10-09",
         text="Hi, we would like 2 pallets of corrugated boxes 600x400x400 mm, 5-ply. CIF Hamburg please. "
              "What is your price?\nJonas",
         items=[item("corrugated_box", ["600x400x400", "5ply"], None)], incoterm="CIF", destination="Hamburg"),
    dict(id="H07", language="en", format="email", received="2026-10-13",
         text="Subject: Inquiry PO-2026-1045\n\nGood day,\n\nQuantity: 1,500 sqm of PS plates 745x605, 0.30 mm. "
              "DAP Tashkent.\nPlease reply within 2 days.\n\nDilshod Karimov\nTashkent Pack LLC\n"
              "Tel: +998 71 200 3344\nOffice 12, Building 7",
         items=[item("ps_plate", ["745x605", "0.3mm"], 1500)], incoterm="DAP", destination="Tashkent"),
    dict(id="H08", language="en", format="email", received="2026-10-12",
         text="Hello,\n\nWe need folding cartons 200x150x60 mm, 400gsm, 30,000 pcs, CIF Santos. The cartons must "
              "arrive at our dock by the end of next month.\n\nLucas\nSantos Embalagens Ltda.",
         items=[item("folding_carton", ["200x150x60", "400gsm"], 30000)], incoterm="CIF", destination="Santos",
         delivery="2026-11-30"),
    dict(id="H09", language="en", format="email", received="2026-10-15",
         text="Hi,\nCould you send 2 sample blankets 790x660, 1.96 mm thick, by DHL to our office in Istanbul for "
              "a press test? If they work well we will order about 200 pcs per quarter.\nEmre, Bosphorus Ambalaj",
         items=[item("blanket", ["790x660", "1.96mm"], 2)], destination="Istanbul"),
    dict(id="H10", language="en", format="email", received="2026-10-07",
         text="Dear Sir or Madam,\n\nWe are interested in thermal CTP plates 745x605, 0.28 mm, 2,000 m². "
              "Target price 2,85 EUR/m². Delivery CIF St. Petersburg within 6 weeks after order.\n\n"
              "Best regards,\nOlga\nSeverny Print LLC",
         items=[item("ctp_plate", ["745x605", "0.28mm"], 2000, price=2.85, currency="EUR")], incoterm="CIF",
         destination="Saint Petersburg", delivery="42 days"),
    dict(id="H11", language="mixed", format="chat", received="2026-10-11",
         text="Hello! Нам нужны офсетные краски: cyan 800 kg. Условия CFR Vladivostok. Target 4.1 USD/kg.\nSergey",
         items=[item("offset_ink", ["cyan"], 800, price=4.1)], incoterm="CFR", destination="Vladivostok"),
    dict(id="H12", language="en", format="email", received="2026-10-02",
         text="Hello,\n\nWe need 10,000 kraft paper bags 320x110x420 mm, 120gsm, and 5,000 LED shelf lights for our "
              "new stores. DDP Moscow, before 2026-12-01.\n\nOlga",
         items=[item("paper_bag", ["320x110x420", "120gsm"], 10000)], incoterm="DDP", destination="Moscow",
         delivery="2026-12-01"),
    dict(id="H13", language="en", format="table", received="2026-10-14",
         text="Please see our requirement:\n\nItem            | Size / grade        | Qty\n"
              "Corrugated box  | 300x200x150, 3-ply  | 20 000\n\nDAP Almaty, within 30 days.\nSteppe Print LLP",
         items=[item("corrugated_box", ["300x200x150", "3ply"], 20000)], incoterm="DAP", destination="Almaty",
         delivery="30 days"),
    dict(id="H14", language="en", format="email", received="2026-10-16",
         text="Dear team,\n\nPlease quote PS plates 1030x790, 0.30mm, 5,000 sqm, CIF Novorossiysk.\n\n"
              "P.S. Sorry, the port should be Saint Petersburg, not Novorossiysk.\n\nOlga",
         items=[item("ps_plate", ["1030x790", "0.3mm"], 5000)], incoterm="CIF", destination="Saint Petersburg"),
    dict(id="H15", language="en", format="email", received="2026-10-18",
         text="Hi,\n\nYour price is too high. We need 15,000 pcs of paper bags 260x120x350, 100gsm at USD 0.17. "
              "CIF Mombasa.\n\nWanjiru\n\n> On Oct 2, Eastline Sales wrote:\n> We can offer 8,000 pcs at USD 0.21 "
              "per bag, FOB Ningbo, 25 days.\n> Please confirm.",
         items=[item("paper_bag", ["260x120x350", "100gsm"], 15000, price=0.17)], incoterm="CIF",
         destination="Mombasa"),
    dict(id="H16", language="en", format="email", received="2026-10-04",
         text="Good morning,\n\nWe would like twelve hundred kilograms of process black offset ink, delivered DAP "
              "Minsk within three weeks.\n\nPavel",
         items=[item("offset_ink", ["black"], 1200)], incoterm="DAP", destination="Minsk", delivery="21 days"),
    dict(id="H17", language="en", format="email", received="2026-10-09",
         text="Hello,\n\nWe need 120,000 thermal labels 70x40 mm. The price should include sea freight and insurance "
              "up to Jebel Ali port. Delivery by December 10.\n\nRashid",
         items=[item("label", ["70x40", "thermal"], 120000)], incoterm="CIF", destination="Jebel Ali",
         delivery="2026-12-10"),
    dict(id="H18", language="en", format="chat", received="2026-10-14",
         text="Hi there, Sanne from Lowlands Packaging. We need 6,000 corrugated boxes 300x200x150, 3-ply, "
              "delivered DDP to our warehouse in Rotterdam by Dec. 5. Can you do it?",
         items=[item("corrugated_box", ["300x200x150", "3ply"], 6000)], incoterm="DDP", destination="Rotterdam",
         delivery="2026-12-05"),
    dict(id="H19", language="ru", format="email", received="2026-10-06",
         text="Уважаемые коллеги!\n\nООО «Белпринт Снаб» просит выставить коммерческое предложение на офсетное "
              "полотно 1060х860х1,95 мм в количестве 120 шт. Поставка DAP Минск. Срок: до конца ноября.\n\n"
              "С уважением,\nПавел",
         items=[item("blanket", ["1060x860", "1.95mm"], 120)], incoterm="DAP", destination="Minsk",
         delivery="2026-11-30"),
    dict(id="H20", language="en", format="chat", received="2026-10-17",
         text="URGENT!! need 300 sqm CTP 650x550 0.24mm, air freight to Tashkent asap. regular customer. Dilshod",
         items=[item("ctp_plate", ["650x550", "0.24mm"], 300)], destination="Tashkent"),
    dict(id="H21", language="en", format="email", received="2026-10-08",
         text="Dear Sales,\n\nPlease quote 8,000 corrugated boxes 400x300x250 mm, 5-ply. Our target is USD 480 per "
              "1,000 boxes, FOB Ningbo, ready for shipment before 2026-12-10.\n\nEmre",
         items=[item("corrugated_box", ["400x300x250", "5ply"], 8000, price=0.48)], incoterm="FOB",
         delivery="2026-12-10"),
    dict(id="H22", language="en", format="email", received="2026-10-12",
         text="Hello,\n\nOur annual need is about 60,000 folding cartons 120x80x200 mm, 300gsm. For now we want a "
              "first shipment of 15,000 pcs, CIF Hamburg, within 35 days.\n\nJonas",
         items=[item("folding_carton", ["120x80x200", "300gsm"], 15000)], incoterm="CIF", destination="Hamburg",
         delivery="35 days"),
    dict(id="H23", language="ru", format="email", received="2026-10-10",
         text="Здравствуйте!\n\nПросим цену на позитивные PS пластины 745х605 мм, 0,30 мм, количество 3 500 м². "
              "CIF Новороссийск, в течение 40 дней.\n\nАндрей",
         items=[item("ps_plate", ["745x605", "0.3mm"], 3500)], incoterm="CIF", destination="Novorossiysk",
         delivery="40 days"),
    dict(id="H24", language="ru", format="chat", received="2026-10-13",
         text="Добрый день! Интересует офсетная краска magenta, 600 кг, DAP Москва. Целевая цена 280 руб/кг.\nОльга",
         items=[item("offset_ink", ["magenta"], 600, price=280, currency="RUB")], incoterm="DAP",
         destination="Moscow"),
    dict(id="H25", language="en", format="email", received="2026-10-19",
         text="Hello,\n\nPlease send your best price for alcohol-free fountain solution. We will decide the quantity "
              "after we see the price. Our factory is in Almaty.\n\nAigerim",
         items=[item("fountain_solution", ["alcohol-free"], None)], destination="Almaty"),
]

# Traps: nothing to extract; the right answer is "no items, low priority"
TRAPS = [
    dict(id="T01", language="en", format="email", received="2026-10-02", kind="spam",
         text="Subject: Get your website on Google page 1\n\nHi,\nI noticed your website is not ranking for "
              "\"printing plates supplier\". Our SEO team can bring you to the first page in 30 days. Price from "
              "USD 199 per month. Reply YES for a free audit.\nMike"),
    dict(id="T02", language="en", format="email", received="2026-10-03", kind="phishing",
         text="Subject: New RFQ waiting on your account\n\nDear Supplier,\nA buyer from Germany sent you an inquiry "
              "for 50,000 folding cartons. To view the buyer's details, please log in here within 24 hours: "
              "http://alibaba-rfq-center.example.net/login\n\nTrade Service Team"),
    dict(id="T03", language="en", format="email", received="2026-10-05", kind="generic",
         text="Dear Sir,\nPlease send your price list and catalogue.\nThanks"),
    dict(id="T04", language="en", format="email", received="2026-10-06", kind="off_catalog",
         text="Hello, we are looking for 20,000 PET bottles 500 ml with caps, CIF Mombasa. Please quote.\nWanjiru"),
    dict(id="T05", language="en", format="email", received="2026-10-07", kind="phishing",
         text="Dear Supplier,\nWe plan a big order of 500,000 corrugated boxes for a government project. First you "
              "must register as our approved vendor. The registration fee is USD 300, payable by money transfer. "
              "After payment we will send the PO.\nProcurement Office"),
    dict(id="T06", language="en", format="email", received="2026-10-08", kind="spam",
         text="Hi! We are a freight forwarder. Best rates Ningbo to Novorossiysk: USD 2,950 per 40HQ, CIF and DAP "
              "service available, 35 days transit. Contact us for your next shipment.\nAlex, FastLine Logistics"),
    dict(id="T07", language="en", format="email", received="2026-10-09", kind="spam",
         text="Invitation: visit us at PrintTech Expo 2026, Hall 3, Booth B12, November 18-20, Istanbul. "
              "Register now for a free ticket."),
    dict(id="T08", language="en", format="email", received="2026-10-10", kind="other",
         text="Hello, I am a recent graduate looking for a job as a sales assistant in your company. "
              "My CV is attached. Thank you for your time."),
    dict(id="T09", language="en", format="email", received="2026-10-11", kind="off_catalog",
         text="Need 3,000 meters of steel pipe DN50, DAP Tashkent, delivery within 30 days. Please send offer.\n"
              "Dilshod"),
    dict(id="T10", language="en", format="email", received="2026-10-12", kind="phishing",
         text="Notice: your shipment No. 77812 is held at customs. To release it, pay the clearance fee of USD 86 "
              "here: http://cargo-release.example.org\nExpress Delivery Service"),
    dict(id="T11", language="ru", format="email", received="2026-10-13", kind="spam",
         text="Здравствуйте! Предлагаем услуги по продвижению вашего бизнеса на маркетплейсах. "
              "Первый месяц со скидкой 50%. Ждём ответа!"),
    dict(id="T12", language="en", format="chat", received="2026-10-14", kind="generic",
         text="hi i want buy your products what you have? send me prices"),
    dict(id="T13", language="ru", format="chat", received="2026-10-15", kind="off_catalog",
         text="Добрый день! Нужны пластиковые стаканы 200 мл, 100 000 шт, DAP Москва.\nОльга"),
    dict(id="T14", language="en", format="email", received="2026-10-16", kind="generic",
         text="Dear Supplier,\nWe are interested in your products. Kindly send FOB price for all items in your "
              "catalogue, with MOQ and delivery time.\nBest regards,\nPurchasing Department"),
    dict(id="T15", language="en", format="email", received="2026-10-17", kind="spam",
         text="How was your experience with our platform this month? Please rate us from 1 to 10 in this short "
              "survey: http://survey.example.com"),
]


# Turn the hand-written cases into (inquiries, answer key)
def build_handwritten():
    inquiries, gold = [], []
    for case in HARD:
        inquiries.append({k: case[k] for k in ("id", "language", "format", "received", "text")}
                         | {"difficulty": "hard"})
        gold.append(gold_record(case["id"], case["items"], case.get("incoterm"), case.get("destination"),
                                case.get("delivery")))
    for case in TRAPS:
        inquiries.append({k: case[k] for k in ("id", "language", "format", "received", "text")}
                         | {"difficulty": "trap"})
        gold.append(gold_record(case["id"], [], kind=case["kind"]))
    return inquiries, gold
