================================================================
Schoolspedia.in — Complete Project
Author: Sahajul (schoolspedia@gmail.com), Tezpur, Assam
================================================================

FOLDER STRUCTURE:
-----------------
Schoolspedia-Project/
├── schools.csv                    ← AAPKA DATA — yahan rakho
├── LocalDataHub_Village_Master_v2.csv  ← VILLAGE DATA — yahan rakho
├── index.html                     ← Homepage
├── robots.txt                     ← Google ke liye
├── generator/
│   └── generator.py               ← Main script — ye sab pages banata hai
├── templates/
│   └── school-detail.html         ← School page ka design template
├── static/
│   └── css/
│       └── style.css              ← Global CSS
├── pages/
│   ├── about.html                 ← About Us page
│   ├── privacy.html               ← Privacy Policy
│   ├── disclaimer.html            ← Disclaimer
│   ├── terms.html                 ← Terms & Conditions
│   └── contact.html               ← Contact Us
└── articles/
    ├── index.html                 ← Articles listing page
    ├── how-to-find-school-udise-code.html
    ├── government-vs-private-schools-india.html
    └── ... (20 articles total)

================================================================
STEP 1 — SETUP (Ek baar karna hai)
================================================================

1. Schoolspedia-Project folder ko Desktop par rakho

2. Dono CSV files isi folder mein rakho:
   - schools.csv
   - LocalDataHub_Village_Master_v2.csv

3. CMD mein pandas install karo (ek baar):
   pip install pandas

================================================================
STEP 2 — DOMAIN UPDATE (IMPORTANT!)
================================================================

generator.py file Notepad mein kholo.
Line 16 par ye dikhega:
   BASE_URL = "https://schoolspedia.in"

Isko apne actual domain se replace karo, jaise:
   BASE_URL = "https://schoolspedia.in"

Save karo.

================================================================
STEP 3 — GENERATOR CHALAO
================================================================

Schoolspedia-Project folder kholo → address bar mein CMD type karo → Enter

PEHLE TEST (500 schools):
   python generator\generator.py --input schools.csv --village LocalDataHub_Village_Master_v2.csv --output output --limit 500

Sab theek laga toh POORA RUN karo:
   python generator\generator.py --input schools.csv --village LocalDataHub_Village_Master_v2.csv --output output

Time: ~2-3 ghante (16 lakh pages)
Output folder: Schoolspedia-Project/output/

================================================================
STEP 4 — POLICY PAGES COPY KARO
================================================================

Generator ke baad, pages/ folder ki files output/ mein copy karo:

output/
├── about/         ← pages/about.html ko yahan index.html karke rakho
├── privacy/       ← pages/privacy.html
├── disclaimer/    ← pages/disclaimer.html
├── terms/         ← pages/terms.html
└── contact/       ← pages/contact.html

Aur articles/ folder bhi output/ mein copy karo.

================================================================
STEP 5 — HOSTINGER PAR UPLOAD
================================================================

1. output/ folder ko ZIP banao
2. Hostinger File Manager → public_html → Upload ZIP
3. ZIP extract karo

================================================================
STEP 6 — ADSENSE APPLY
================================================================

Pehle website live hone ke baad:

1. school-detail.html mein AdSense code add karo:
   <!-- <script async src="...ca-pub-XXXXXXXX..."></script> -->
   Isko uncomment karo apna publisher ID daalke

2. Google AdSense → Add Site → schoolspedia.in
3. Approval ke liye zaruri hai:
   ✓ About Us page (pages/about.html) ✓
   ✓ Privacy Policy (pages/privacy.html) ✓
   ✓ Contact Us (pages/contact.html) ✓
   ✓ 20 original articles ✓
   ✓ 600+ words per school page ✓
   ✓ Real data (UDISE + Census) ✓

================================================================
STEP 7 — SITEMAP SUBMIT KARO
================================================================

Google Search Console → search.google.com/search-console

Submit karo:
   https://schoolspedia.in/sitemap.xml
   https://schoolspedia.in/sitemap-states.xml
   https://schoolspedia.in/sitemap-schools-1.xml
   (aur jitne bhi sitemap-schools-N.xml bane)

================================================================
CONTACT
================================================================
Sahajul — schoolspedia@gmail.com — Tezpur, Assam
================================================================
