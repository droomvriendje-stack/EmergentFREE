"""
Product Migration Script - Migrate mockData.js products to MongoDB
Run this script to populate the database with all live products from droomvriendjes.nl
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'droomvriendje')

# All products from mockData.js - COMPLETE LIVE CATALOG
LIVE_PRODUCTS = [
    # DE SLIMME AI-SERIE - Leeuw (FM666-61)
    {
        "id": 14,
        "name": "Slimme Leeuw – Nachtlampje met AI Huilsensor & Projector – USB-C Oplaadbaar",
        "shortName": "Slimme Leeuw",
        "price": 49.95,
        "originalPrice": 59.95,
        "image": "/products/lion-main.png",
        "gallery": [
            "/products/lion-main.png",
            "/products/lion/Lion_Side_product_02.png",
            "/products/lion/Lion_back_prodcut_03.png",
            "/products/lion/Lion_dimenstions_product_04.png",
            "/products/lion/Lion_Macro_prodcut_05.png",
            "/products/lion/Lion_gift_product_06.png",
            "/products/lion/Lion_Lifestyle_prodcut_08.png",
            "/products/lion/Lion_Lifestyle_prodcut_09.png",
            "/products/lion/Lion_packaging_product_10.png"
        ],
        "description": "Ontmoet de slimste koning van de nacht. Deze Leeuw is uitgerust met een intelligente AI-huilsensor die direct reageert wanneer je baby onrustig wordt. Dankzij de drie verwisselbare kappen creëer je een magische sterrenhemel, een rustgevende oceaan of een zacht nachtlampje. Met 10 ingebouwde slaapliedjes en 5 witte ruis-geluiden biedt deze leeuw optimale ondersteuning bij het slapen. Volledig oplaadbaar via USB-C, dus geen gedoe met batterijen.",
        "features": [
            "AI Huilsensor - reageert automatisch op huilen",
            "3-in-1 Projectie: sterren, oceaan of nachtlampje",
            "10 slaapliedjes + 5 white noise geluiden",
            "USB-C oplaadbaar - geen batterijen nodig",
            "30 minuten auto-uit timer"
        ],
        "benefits": [
            "🤖 AI Huilsensor: Springt automatisch aan om je kindje te troosten",
            "🌟 3-in-1 Projectie: Kies uit sterren, oceaan of nachtlampje",
            "🔋 Duurzaam & Oplaadbaar: USB-C kabel inbegrepen",
            "🎵 10 slaapliedjes en 5 rustgevende geluiden"
        ],
        "rating": 4.9,
        "reviews": 2847,
        "badge": "BESTSELLER",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-61",
        "itemId": "KNUF_014",
        "itemCategory": "Knuffels",
        "itemCategory2": "AI Slaapknuffels",
        "itemCategory3": "Slimme Serie",
        "itemCategory4": "USB-C Oplaadbaar",
        "itemCategory5": "Met AI Huilsensor",
        "itemVariant": "goud-bruin",
        "series": "ai"
    },
    # DE INTERACTIEVE "NODDING OFF" SERIE - Schaap (FM666-78)
    {
        "id": 2,
        "name": "Slaperig Schaapje – Interactief Nachtlampje met Projector & 60 Melodieën",
        "shortName": "Slaperig Schaapje",
        "price": 54.95,
        "originalPrice": 64.95,
        "image": "/products/sheep-main.png",
        "gallery": [
            "/products/sheep-main.png",
            "/products/sheep/Sheep_side_prodcut_02.png",
            "/products/sheep/Sheep_back_prodcut_03.png",
            "/products/sheep/Sheep_dimenstions_product_04.png",
            "/products/sheep/Sheep_features_prodcut_05.png",
            "/products/sheep/sheep_gift_product_06.png",
            "/products/sheep/Sheep_Lifestyle_prodcut_07.png",
            "/products/sheep/Sheep_Lifestyle_prodcut_08.png",
            "/products/sheep/Sheep_Lifestyle_prodcut_09.png",
            "/products/sheep/Sheep_packaging_prodcut_10.png"
        ],
        "description": "Dit lieve Schaapje helpt je kindje heerlijk weg te dromen. Dankzij de unieke 'Nodding Off' functie maakt het schaapje een kalmerende, knikkende beweging die baby's helpt te ontspannen. Met maar liefst 60 slaapliedjes, 6 witte ruis-geluiden en 7 verschillende lichtmodi is dit het ultieme slaapvriendje.",
        "features": [
            "Nodding Off beweging - kalmerende knik-functie",
            "60 slaapliedjes + 6 white noise geluiden",
            "7 verschillende lichtmodi",
            "3 verwisselbare projectiekappen",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "🐑 Dynamische beweging: Kalmerende knik-functie",
            "🎶 60 melodieën en natuurlijke white noise",
            "🌈 7 lichtmodi voor perfecte sfeer",
            "✨ Sterrenhemel en onderwaterwereld projectie"
        ],
        "rating": 4.8,
        "reviews": 1923,
        "badge": "POPULAIR",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-78",
        "itemId": "KNUF_002",
        "itemCategory": "Knuffels",
        "itemCategory2": "Interactieve Knuffels",
        "itemCategory3": "Nodding Off Serie",
        "itemCategory4": "60 Melodieën",
        "itemCategory5": "Met Beweging",
        "itemVariant": "wit-grijs",
        "series": "nodding"
    },
    # DE INTERACTIEVE "NODDING OFF" SERIE - Panda (FM666-77)
    {
        "id": 3,
        "name": "Slaperige Panda – Interactief Nachtlampje met Projector & 60 Melodieën",
        "shortName": "Slaperige Panda",
        "price": 54.95,
        "originalPrice": 64.95,
        "image": "/products/panda-main.png",
        "gallery": [
            "/products/panda-main.png",
            "/products/panda/Panda_Side_product_02.png",
            "/products/panda/Panda_back_prodcut_03.png",
            "/products/panda/Panda_dimenstions_product_04.png",
            "/products/panda/Panda_Macro_prodcut_05.png",
            "/products/panda/Panda_gift_product_06.png",
            "/products/panda/Panda_Lifestyle_prodcut_07.png",
            "/products/panda/Panda_Lifestyle_prodcut_08.png",
            "/products/panda/Panda_Lifestyle_prodcut_09.png",
            "/products/panda/Panda_packaging_product_10.png"
        ],
        "description": "Onze Slaperige Panda is ontworpen om van bedtijd een feestje te maken. Dit interactieve projector-speelgoed combineert een zachte beweging met een indrukwekkend aanbod aan geluiden en lichteffecten.",
        "features": [
            "Nodding Off beweging - kalmerende knik-functie",
            "60 slaapliedjes + 6 white noise geluiden",
            "7 verschillende lichtmodi",
            "3 verwisselbare projectiekappen",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "🐼 Slaap-ondersteuning: Zachte, rustgevende beweging",
            "🎵 60 kalmerende liedjes en 6 witte-ruisopties",
            "🌟 3-in-1 projectie: sterrenhemel, oceaan of nachtlampje",
            "💡 7 lichtstanden voor perfecte sfeer"
        ],
        "rating": 4.9,
        "reviews": 1654,
        "badge": "NIEUW",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-77",
        "itemId": "KNUF_003",
        "itemCategory": "Knuffels",
        "itemCategory2": "Interactieve Knuffels",
        "itemCategory3": "Nodding Off Serie",
        "itemCategory4": "60 Melodieën",
        "itemCategory5": "Met Beweging",
        "itemVariant": "zwart-wit",
        "series": "nodding"
    },
    # DE INTERACTIEVE "NODDING OFF" SERIE - Dinosaurus (FM666-82)
    {
        "id": 4,
        "name": "Stoere Dinosaurus – Interactief Nachtlampje met Projector & 60 Melodieën",
        "shortName": "Stoere Dino",
        "price": 54.95,
        "originalPrice": 64.95,
        "image": "/products/dino-main.png",
        "gallery": [
            "/products/dino-main.png",
            "/products/dino/Dinno_Side_product_02.png",
            "/products/dino/Dinno_back_prodcut_03.png",
            "/products/dino/Dinno_dimenstions_product_04.png",
            "/products/dino/Dinno_Macro_prodcut_05.png",
            "/products/dino/Dinno_gift_product_06.png",
            "/products/dino/Dinno_Lifestyle_prodcut_07.png",
            "/products/dino/Dinno_Lifestyle_prodcut_08.png",
            "/products/dino/Dinno_Lifestyle_prodcut_09.png",
            "/products/dino/Dinno_packaging_product_10.png"
        ],
        "description": "Voor kleine avonturiers is er deze vriendelijke Dinosaurus. Dit interactieve nachtlampje waakt over de kamer met zijn unieke bewegingen en prachtige lichteffecten.",
        "features": [
            "Interactieve Nodding Off beweging",
            "60 slaapliedjes + 6 white noise geluiden",
            "7 lichtmodi voor avontuurlijke sfeer",
            "Verwisselbare kappen voor nieuwe ervaringen",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "🦖 Interactief design: Rustgevende beweging",
            "💡 7 lichtmodi en 60 slaapliedjes",
            "🌌 Sterrenhemel en oceaanwereld projectie",
            "🛡️ Geen kind meer bang in het donker"
        ],
        "rating": 4.8,
        "reviews": 1432,
        "badge": "FAVORIET",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-82",
        "itemId": "KNUF_004",
        "itemCategory": "Knuffels",
        "itemCategory2": "Interactieve Knuffels",
        "itemCategory3": "Nodding Off Serie",
        "itemCategory4": "60 Melodieën",
        "itemCategory5": "Met Beweging",
        "itemVariant": "groen",
        "series": "nodding"
    },
    # DE INTERACTIEVE "NODDING OFF" SERIE - Eenhoorn (FM666-74)
    {
        "id": 5,
        "name": "Magische Eenhoorn – Interactief Nachtlampje met Projector & 60 Melodieën",
        "shortName": "Magische Eenhoorn",
        "price": 54.95,
        "originalPrice": 64.95,
        "image": "/products/unicorn-main.png",
        "gallery": [
            "/products/unicorn-main.png",
            "/products/unicorn/Unicorn_Side_product_02.png",
            "/products/unicorn/Unicorn_back_prodcut_03.png",
            "/products/unicorn/Unicorn_dimenstions_product_04.png",
            "/products/unicorn/Unicorn_Macro_prodcut_05.png",
            "/products/unicorn/Unicorn_gift_product_06.png",
            "/products/unicorn/Unicorn_Lifestyle_prodcut_07.png",
            "/products/unicorn/Unicorn_Lifestyle_prodcut_08.png",
            "/products/unicorn/Unicorn_Lifestyle_prodcut_09.png",
            "/products/unicorn/Unicorn_packaging_product_10.png"
        ],
        "description": "Breng de magie in huis met deze prachtige Eenhoorn. Dit slaapvriendje beweegt zachtjes mee ('Nodding Off') terwijl het een warme gloed en rustgevende muziek verspreidt.",
        "features": [
            "Magische Nodding Off beweging",
            "60 melodieën + 6 white noise geluiden",
            "7 lichtmodi voor dromerige sfeer",
            "3 projectie-thema's: sterren, oceaan, nachtlamp",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "🦄 Magische sfeer: 7 lichtmodi",
            "🎶 60 melodieën en 6 witte ruis-opties",
            "✨ Interactieve beweging voor diepe rust",
            "💖 Veilig en geborgen gevoel"
        ],
        "rating": 4.9,
        "reviews": 2156,
        "badge": "MAGISCH",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-74",
        "itemId": "KNUF_005",
        "itemCategory": "Knuffels",
        "itemCategory2": "Interactieve Knuffels",
        "itemCategory3": "Nodding Off Serie",
        "itemCategory4": "60 Melodieën",
        "itemCategory5": "Met Beweging",
        "itemVariant": "roze-wit",
        "series": "nodding"
    },
    # Bruine Beer
    {
        "id": 7,
        "name": "Bruine Beertje – Nachtlampje met Sterrenprojector & Slaapgeluiden",
        "shortName": "Bruine Beer",
        "price": 49.95,
        "originalPrice": 59.95,
        "image": "/products/bearbrown-main.png",
        "gallery": [
            "/products/bearbrown-main.png",
            "/products/bearbrown/BearBrown_Side_product_02.png",
            "/products/bearbrown/BearBrown_back_prodcut_03.png",
            "/products/bearbrown/BearBrown_dimenstions_product_04.png",
            "/products/bearbrown/BearBrown_Macro_prodcut_05.png",
            "/products/bearbrown/BearBrown_gift_product_06.png",
            "/products/bearbrown/BearBrown_Lifestyle_prodcut_07.png",
            "/products/bearbrown/BearBrown_Lifestyle_prodcut_08.png",
            "/products/bearbrown/BearBrown_Lifestyle_prodcut_09.png",
            "/products/bearbrown/BearBrown_packaging_product_10.png"
        ],
        "description": "Deze lieve bruine beer is de perfecte slaapvriend voor je kindje. Met een zachte sterrenprojector en rustgevende slaapliedjes creëert dit beertje een geborgen sfeer.",
        "features": [
            "Sterrenhemel en oceaanprojectie",
            "10 rustgevende melodieën",
            "Zacht diffuus nachtlicht",
            "30 minuten auto-uit timer",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "🐻 Zachte knuffelpartner",
            "🌟 Magische sterrenprojectie",
            "🎵 Rustgevende slaapliedjes",
            "😴 Helpt bij doorslapen"
        ],
        "rating": 4.8,
        "reviews": 1456,
        "badge": "POPULAIR",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-72",
        "itemId": "KNUF_007",
        "itemCategory": "Knuffels",
        "itemCategory2": "Slaapknuffels",
        "itemCategory3": "Beren",
        "itemCategory4": "Medium",
        "itemCategory5": "Met Projectie",
        "itemVariant": "bruin",
        "series": "basic"
    },
    # Liggend Schaapje
    {
        "id": 8,
        "name": "Liggend Schaapje – Nachtlampje met Sterrenprojectie & Slaapmelodieën",
        "shortName": "Liggend Schaapje",
        "price": 49.95,
        "originalPrice": 59.95,
        "image": "/products/sheeptwo-main.png",
        "gallery": [
            "/products/sheeptwo-main.png",
            "/products/sheeptwo/SheepTwo_Side_product_02.png",
            "/products/sheeptwo/SheepTwo_back_prodcut_03.png",
            "/products/sheeptwo/SheepTwo_dimenstions_product_04.png",
            "/products/sheeptwo/SheepTwo_Macro_prodcut_05.png",
            "/products/sheeptwo/SheepTwo_gift_product_06.png",
            "/products/sheeptwo/SheepTwo_Lifestyle_prodcut_07.png",
            "/products/sheeptwo/SheepTwo_Lifestyle_prodcut_08.png",
            "/products/sheeptwo/SheepTwo_Lifestyle_prodcut_09.png",
            "/products/sheeptwo/SheepTwo_packaging_product_10.png"
        ],
        "description": "Dit lieve liggende schaapje is ontworpen om mee te knuffelen terwijl je kindje in slaap valt. Met zachte sterrenprojector en kalmerende melodieën.",
        "features": [
            "Liggend knuffeldesign",
            "Sterrenhemel projectie",
            "10 rustgevende melodieën",
            "Zacht diffuus nachtlicht",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "🐑 Lekker om mee te knuffelen in bed",
            "🌟 Magische sterrenprojectie",
            "🎵 Kalmerende slaapliedjes",
            "😴 Helpt bij inslapen"
        ],
        "rating": 4.7,
        "reviews": 1234,
        "badge": "NIEUW",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-79",
        "itemId": "KNUF_008",
        "itemCategory": "Knuffels",
        "itemCategory2": "Slaapknuffels",
        "itemCategory3": "Boerderijdieren",
        "itemCategory4": "Medium",
        "itemCategory5": "Liggend Design",
        "itemVariant": "wit-crème",
        "series": "basic"
    },
    # Pinguïn
    {
        "id": 9,
        "name": "Pinguïn Droomvriendje – Nachtlampje met Sterrenprojector & Witte Ruis",
        "shortName": "Pinguïn",
        "price": 49.95,
        "originalPrice": 59.95,
        "image": "/products/penguin-main.png",
        "gallery": [
            "/products/penguin-main.png",
            "/products/penguin/Penguin_Side_product_02.png",
            "/products/penguin/Penguin_back_prodcut_03.png",
            "/products/penguin/Penguin_dimenstions_product_04.png",
            "/products/penguin/Penguin_Macro_prodcut_05.png",
            "/products/penguin/Penguin_gift_product_06.png",
            "/products/penguin/Penguin_Lifestyle_prodcut_07.png",
            "/products/penguin/Penguin_Lifestyle_prodcut_08.png",
            "/products/penguin/Penguin_Lifestyle_prodcut_09.png",
            "/products/penguin/Penguin_packaging_product_10.png"
        ],
        "description": "Dit schattige pinguïntje brengt de magie van de poolnacht naar de kinderkamer. Met prachtige sterrenprojectie en rustgevende witte ruis-geluiden.",
        "features": [
            "Sterrenhemel en oceaanprojectie",
            "8 white noise geluiden",
            "Zacht LED nachtlicht",
            "30 minuten auto-uit timer",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "🐧 Uniek pinguïn design",
            "⭐ Magische sterrenhemel",
            "🎶 Kalmerende white noise",
            "💙 Rustgevende sfeer"
        ],
        "rating": 4.8,
        "reviews": 987,
        "badge": "POPULAIR",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-75",
        "itemId": "KNUF_009",
        "itemCategory": "Knuffels",
        "itemCategory2": "Slaapknuffels",
        "itemCategory3": "Pooldieren",
        "itemCategory4": "Medium",
        "itemCategory5": "Met Projectie",
        "itemVariant": "blauw-wit",
        "series": "basic"
    },
    # Grijze Teddy
    {
        "id": 13,
        "name": "Grijze Teddybeer – Premium Nachtlampje met Projector & Melodieën",
        "shortName": "Grijze Teddy",
        "price": 49.95,
        "originalPrice": 59.95,
        "image": "/products/beartwo-main.png",
        "gallery": [
            "/products/beartwo-main.png",
            "/products/beartwo/BearTwo_Side_product_02.png",
            "/products/beartwo/BearTwo_back_prodcut_03.png",
            "/products/beartwo/BearTwo_dimenstions_product_04.png",
            "/products/beartwo/BearTwo_Macro_prodcut_05.png",
            "/products/beartwo/BearTwo_gift_product_06.png",
            "/products/beartwo/BearTwo_Lifestyle_prodcut_07.png",
            "/products/beartwo/BearTwo_Lifestyle_prodcut_08.png",
            "/products/beartwo/BearTwo_Lifestyle_prodcut_09.png",
            "/products/beartwo/BearTwo_packaging_product_10.png"
        ],
        "description": "Deze elegante grijze teddybeer is de perfecte metgezel voor rustige nachten. Met premium sterrenprojectie en kalmerende hartslaggeluiden.",
        "features": [
            "Premium sterrenprojectie",
            "Hartslag en white noise geluiden",
            "Zacht diffuus nachtlicht",
            "30 minuten auto-uit timer",
            "Werkt op 3x AA-batterijen"
        ],
        "benefits": [
            "💤 Helpt sneller inslapen",
            "🧸 Knuffelbare beste vriend",
            "🌟 Geruststellend sterrenlicht",
            "😴 Ondersteunt doorslapen"
        ],
        "rating": 4.9,
        "reviews": 1567,
        "badge": "BESTSELLER",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "FM666-73",
        "itemId": "KNUF_013",
        "itemCategory": "Knuffels",
        "itemCategory2": "Slaapknuffels",
        "itemCategory3": "Beren",
        "itemCategory4": "Medium",
        "itemCategory5": "Met Nachtlamp",
        "itemVariant": "grijs",
        "series": "basic"
    },
    # DUO SET
    {
        "id": 15,
        "name": "Droomvriendjes Duo Set – Liggend Schaapje & Witte Beer met Projector",
        "shortName": "Duo Set",
        "price": 89.95,
        "originalPrice": 109.90,
        "image": "/products/duo-main.png",
        "gallery": [
            "/products/duo-main.png",
            "/products/duo/DUO_Side_product_02.png",
            "/products/duo/DUO_back_product_03.png",
            "/products/duo/Duo_gift1_produc_06.png",
            "/products/duo/DUO_gift2_product_06.png",
            "/products/duo/Duo_Lifestyle_prodcut_07.png",
            "/products/duo/Duo_Lifestyle01_prodcut_08.png",
            "/products/duo/DUO_Lifestyle_prodcut_09.png"
        ],
        "description": "De ultieme voordeelset: twee Droomvriendjes voor de prijs van bijna één! Deze set bevat het schattige Liggende Schaapje én de knuffelbare Witte Beer, beide met sterrenprojector en rustgevende melodieën.",
        "features": [
            "2 complete Droomvriendjes in 1 set",
            "Liggend Schaapje + Witte Beer",
            "Beide met sterrenprojectie en melodieën",
            "€20 voordeelkorting"
        ],
        "benefits": [
            "👫 Perfect voor twee kindjes",
            "🐑 Schaapje: Heerlijk knuffelbaar liggend design",
            "🐻 Beer: Zachte witte vacht",
            "💰 Bespaar €20 op de setprijs"
        ],
        "rating": 4.9,
        "reviews": 1847,
        "badge": "VOORDEELSET",
        "inStock": True,
        "ageRange": "Vanaf 0 maanden",
        "warranty": "30 dagen slaapgarantie",
        "sku": "DUO-001",
        "itemId": "KNUF_015",
        "itemCategory": "Knuffels",
        "itemCategory2": "Voordeelsets",
        "itemCategory3": "Duo Sets",
        "itemCategory4": "Large",
        "itemCategory5": "Met Projectie",
        "itemVariant": "wit-crème",
        "series": "basic"
    }
]


async def migrate_products():
    """Migrate all products to MongoDB"""
    try:
        import certifi
        client = AsyncIOMotorClient(mongo_url, tlsCAFile=certifi.where())
    except ImportError:
        client = AsyncIOMotorClient(mongo_url)
    
    database = client[db_name]
    products_collection = database.products
    
    print(f"🔄 Starting product migration to {db_name}...")
    print(f"📦 Total products to migrate: {len(LIVE_PRODUCTS)}")
    
    # Clear existing products
    result = await products_collection.delete_many({})
    print(f"🗑️ Cleared {result.deleted_count} existing products")
    
    # Add timestamps and prepare products
    now = datetime.now(timezone.utc).isoformat()
    products_to_insert = []
    
    for product in LIVE_PRODUCTS:
        product_doc = {
            **product,
            "createdAt": now,
            "updatedAt": now,
            "stock": 100,  # Default stock
            "visible": True
        }
        products_to_insert.append(product_doc)
    
    # Insert all products
    result = await products_collection.insert_many(products_to_insert)
    print(f"✅ Successfully inserted {len(result.inserted_ids)} products")
    
    # Verify
    count = await products_collection.count_documents({})
    print(f"📊 Total products in database: {count}")
    
    # List products
    print("\n📋 Products migrated:")
    async for product in products_collection.find({}, {"id": 1, "shortName": 1, "price": 1, "series": 1}):
        print(f"   - ID {product['id']}: {product['shortName']} (€{product['price']}) [{product.get('series', 'unknown')}]")
    
    client.close()
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate_products())
