#!/usr/bin/env python3
# Schoolspedia.in Generator
# Domain: schoolspedia.in | Email: schoolspedia@gmail.com
#
import os, re, csv, sys, math, shutil, argparse
from datetime import datetime
from collections import defaultdict


def minify_html(h):
    h = re.sub(r"<!--(?!\[if).*?-->", "", h, flags=re.DOTALL)
    h = re.sub(r">\s{2,}<", "><", h)
    h = re.sub(r"^\s+", "", h, flags=re.MULTILINE)
    h = re.sub(r"\n{2,}", "\n", h)
    return h.strip()




BASE_URL           = "https://schoolspedia.in"
SITE_NAME          = "Schoolspedia.in"
BATCH_SITEMAP_SIZE = 50000

CSS_LINK = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet"><link rel="stylesheet" href="/style.css">'


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def clean(value, strip_prefix=True):
    if not value or str(value).strip() in ('nan','','N/A','None'):
        return 'N/A'
    value = str(value).strip()
    if strip_prefix:
        value = re.sub(r'^\d+-\s*', '', value).strip()
    return value or 'N/A'

def fmt_num(val):
    """Format number with commas"""
    try:
        n = int(float(str(val).replace(',','')))
        return f"{n:,}"
    except:
        return str(val) if val else 'N/A'

def fmt_pct(val):
    try:
        return f"{float(val):.1f}"
    except:
        return 'N/A'

def safe_float(val):
    try:
        return float(str(val).replace(',',''))
    except:
        return 0.0



def category_range(cat):
    raw = str(cat)
    c = re.sub(r'^[0-9]+-', '', raw).strip().lower()
    has_hsec = 'h.sec' in c or 'higher sec' in c or '.sec.' in c
    has_upper= 'up.' in c or 'upper' in c or 'up.pr' in c
    has_pri  = 'pr.' in c or 'primary' in c
    has_sec  = 'sec' in c
    if has_hsec and (has_pri or has_upper):  return 'Classes 1 to 12'
    if has_hsec:                              return 'Classes 9 to 12'
    if has_sec  and has_upper and has_pri:    return 'Classes 1 to 10'
    if has_sec  and has_upper:                return 'Classes 6 to 10'
    if has_sec  and has_pri:                  return 'Classes 1 to 10'
    if has_sec:                               return 'Classes 9 to 10'
    if has_upper and has_pri:                 return 'Classes 1 to 8'
    if has_upper:                             return 'Classes 6 to 8'
    if has_pri:                               return 'Classes 1 to 5'
    return 'various classes'

def cat_short(cat):
    raw = str(cat)
    c = re.sub(r'^[0-9]+-', '', raw).strip().lower()
    has_hsec = 'h.sec' in c or 'higher sec' in c or '.sec.' in c
    has_upper= 'up.' in c or 'upper' in c
    has_pri  = 'pr.' in c or 'primary' in c
    has_sec  = 'sec' in c
    if has_hsec and (has_pri or has_upper):  return 'Class 1–12'
    if has_hsec:                              return 'Higher Secondary'
    if has_sec:                               return 'Secondary'
    if has_upper:                             return 'Upper Primary'
    return 'Primary'


def mgmt_short(mgmt):
    m = str(mgmt).lower()
    if 'private unaided' in m: return 'Private Unaided'
    if 'private aided'   in m: return 'Private Aided'
    if 'department'      in m: return 'Government'
    if 'local body'      in m: return 'Local Body'
    if 'central'         in m: return 'Central Govt.'
    return mgmt[:22]

def location_label(loc):
    if 'urban' in str(loc).lower(): return 'Urban'
    return 'Rural'

def school_type_short(stype):
    s = str(stype).lower()
    if 'co-ed' in s or 'co ed' in s: return 'Co-educational'
    if 'girls' in s or 'female' in s: return 'Girls Only'
    if 'boys' in s or 'male' in s:    return 'Boys Only'
    return stype[:20]

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def read_csv(path):
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [c.strip().lstrip('\ufeff') for c in reader.fieldnames]
        for row in reader:
            rows.append({k.strip(): v for k, v in row.items()})
    return rows


# ─────────────────────────────────────────────
# BUILD VILLAGE/DISTRICT LOOKUP
# ─────────────────────────────────────────────
def build_village_index(village_rows):
    """
    Build lookup: (state_slug, district_slug) → district census data
    Also: (state_slug, district_slug, village_slug) → village row
    """
    district_index = {}   # (state_slug, district_slug) → row
    village_index  = {}   # (state_slug, district_slug, village_slug) → row

    for row in village_rows:
        ss  = slugify(row.get('state_name',''))
        ds  = slugify(row.get('district_name',''))
        vs  = slugify(row.get('village_name',''))
        key_d = (ss, ds)
        key_v = (ss, ds, vs)

        if key_d not in district_index:
            district_index[key_d] = row
        village_index[key_v] = row

    return district_index, village_index


# ─────────────────────────────────────────────
# RELIGION BARS HTML
# ─────────────────────────────────────────────
def religion_bars_html(row):
    religions = [
        ('Hindu',    row.get('dist_Hindu_pct','0')),
        ('Muslim',   row.get('dist_Muslim_pct','0')),
        ('Christian',row.get('dist_Christian_pct','0')),
        ('Sikh',     row.get('dist_Sikh_pct','0')),
        ('Buddhist', row.get('dist_Buddhist_pct','0')),
        ('Jain',     row.get('dist_Jain_pct','0')),
        ('Others',   row.get('dist_Other_Religion_pct','0')),
    ]
    html = ''
    for name, pct in religions:
        p = safe_float(pct)
        if p > 0.5:
            html += f'<div class="rel-item"><div class="rel-name">{name}</div><div class="rel-pct">{p:.1f}%</div></div>'
    return html or '<div class="rel-item"><div class="rel-name">Data not available</div></div>'


# ─────────────────────────────────────────────
# DYNAMIC CONTENT GENERATORS (Human-sounding)
# ─────────────────────────────────────────────
def literacy_context(district, literacy_pct, male_lit, female_lit):
    p = safe_float(literacy_pct)
    m = safe_float(male_lit)
    f = safe_float(female_lit)
    gap = m - f
    if p >= 80:
        level = "well above the national average, reflecting strong educational infrastructure in the district"
    elif p >= 65:
        level = "broadly in line with the national average, though there remains room for improvement"
    elif p >= 50:
        level = "below the national average, indicating that educational access and outcomes remain a challenge for many families here"
    else:
        level = "significantly below the national average, highlighting serious educational gaps that require sustained policy attention"

    gap_text = ""
    if gap > 20:
        gap_text = f" The gender literacy gap of {gap:.1f} percentage points — with male literacy at {m:.1f}% compared to female literacy at {f:.1f}% — is notably wide, suggesting that girls' education remains a priority area for {district}."
    elif gap > 10:
        gap_text = f" The {gap:.1f} percentage point gap between male ({m:.1f}%) and female ({f:.1f}%) literacy indicates that while progress has been made, girls' educational outcomes still lag behind."
    else:
        gap_text = f" The relatively narrow gap between male ({m:.1f}%) and female ({f:.1f}%) literacy suggests more equitable educational access across genders in this district."

    return f"This is {level}.{gap_text}"


def school_density_context(district, total_schools, population):
    ts = safe_float(total_schools)
    pop = safe_float(population)
    if ts > 0 and pop > 0:
        per_10k = (ts / pop) * 10000
        if per_10k >= 8:
            return f"With {fmt_num(ts)} schools serving a population of {fmt_num(population)}, {district} has a relatively good school density of approximately {per_10k:.1f} schools per 10,000 people"
        elif per_10k >= 4:
            return f"The district has approximately {per_10k:.1f} schools per 10,000 people — a moderate density that suggests most children should have access to at least one school within a reasonable distance"
        else:
            return f"With only around {per_10k:.1f} schools per 10,000 people, {district} faces real challenges in ensuring every child has a school accessible within walking distance"
    return f"{district} has {fmt_num(ts)} schools serving the district population"


def tribal_context(st_pct, district, is_tribal):
    p = safe_float(st_pct)
    if is_tribal and is_tribal.upper() == 'Y':
        return f"This particular village is classified as a tribal area, and the school serves a community that may include students from Scheduled Tribe backgrounds. Tribal area schools in India often face additional challenges around multilingual education and teacher recruitment."
    if p >= 40:
        return f"With {p:.1f}% of the district population belonging to Scheduled Tribes, {district} has a significant tribal demographic. Schools in the district play a particularly important role in ensuring quality education reaches tribal communities, many of whom may speak a language different from the medium of instruction."
    elif p >= 15:
        return f"Scheduled Tribe communities make up {p:.1f}% of {district}'s population. The district's schools serve a mix of tribal and non-tribal students, requiring sensitivity to different community backgrounds and learning contexts."
    else:
        return f"Scheduled Tribe communities account for {p:.1f}% of {district}'s population."


def rural_urban_label(inhabited_villages, towns):
    v = safe_float(inhabited_villages)
    t = safe_float(towns)
    if v > 0 and t > 0:
        if v / (v + t) > 0.8:
            return "predominantly rural"
        elif v / (v + t) > 0.5:
            return "mixed rural-urban"
        else:
            return "urban-leaning"
    return "predominantly rural"


# ─────────────────────────────────────────────
# RENDER SCHOOL PAGE
# ─────────────────────────────────────────────
def render_school_page(school, template, related_html, district_data):
    u      = str(school.get('udise_code','')).strip()
    name   = str(school.get('school_name','')).strip().title()
    state  = clean(school.get('state',''), False)
    dist   = clean(school.get('district',''), False).title()
    block  = clean(school.get('block',''), False).title()
    village= clean(school.get('village',''), False).title()
    cluster= clean(school.get('cluster',''), False).title()
    loc    = clean(str(school.get('location','Rural')))
    s_mgmt = clean(school.get('state_mgmt',''))
    n_mgmt = clean(school.get('national_mgmt',''))
    cat    = clean(school.get('school_category',''))
    stype  = clean(school.get('school_type',''))
    status = clean(str(school.get('school_status','')).strip())

    state_slug = slugify(state)
    dist_slug  = slugify(dist)

    # District/village data
    d = district_data or {}
    literacy_pct    = fmt_pct(d.get('dist_Literacy_pct','N/A'))
    male_lit        = fmt_pct(d.get('dist_Male_Literacy_pct','N/A'))
    female_lit      = fmt_pct(d.get('dist_Female_Literacy_pct','N/A'))
    worker_pct      = fmt_pct(d.get('dist_Worker_pct','N/A'))
    population      = d.get('dist_Population','N/A')
    sex_ratio       = d.get('dist_Sex_Ratio','N/A')
    child_sex_ratio = d.get('dist_Child_Sex_Ratio','N/A')
    total_schools   = d.get('dist_Total_Schools','N/A')
    govt_schools    = d.get('dist_Govt_Schools','N/A')
    private_schools = d.get('dist_Private_Schools','N/A')
    girls_schools   = d.get('dist_Girls_Schools','N/A')
    st_pct          = fmt_pct(d.get('dist_ST_pct','0'))
    sc_pct          = fmt_pct(d.get('dist_SC_pct','0'))
    post_offices    = d.get('dist_Total_PostOffices','N/A')
    pin_code        = d.get('dist_Sample_PIN','N/A')
    inhabited_v     = d.get('dist_Inhabited_Villages','N/A')
    towns           = d.get('dist_Towns','N/A')
    is_tribal       = d.get('is_tribal_area','N')

    # Formatted
    population_fmt = fmt_num(population)
    total_schools_fmt = fmt_num(total_schools)
    govt_schools_fmt  = fmt_num(govt_schools)
    priv_schools_fmt  = fmt_num(private_schools)

    # Dynamic content
    lit_ctx         = literacy_context(dist, literacy_pct, male_lit, female_lit)
    density_ctx     = school_density_context(dist, total_schools, population)
    tribal_ctx_para = tribal_context(st_pct, dist, is_tribal)
    rural_urban_lbl = rural_urban_label(inhabited_v, towns)
    tribal_village_ctx = "This village is in a designated tribal area." if str(is_tribal).upper()=='Y' else f"The village of {village} is in a {location_label(loc)} area of {block} block."
    religion_html   = religion_bars_html(d)
    pin_disp        = str(pin_code).replace('.0','') if pin_code != 'N/A' else 'N/A'
    sex_ratio_disp  = str(sex_ratio).replace('.0','') if sex_ratio != 'N/A' else 'N/A'
    child_sr_disp   = str(child_sex_ratio).replace('.0','') if child_sex_ratio != 'N/A' else 'N/A'
    inhabited_disp  = fmt_num(inhabited_v)
    towns_disp      = fmt_num(towns)
    post_disp       = fmt_num(post_offices)

    html = template
    for k, v in {
        '{{SCHOOL_NAME}}':          name,
        '{{UDISE_CODE}}':           u,
        '{{STATE}}':                state,
        '{{STATE_SLUG}}':           state_slug,
        '{{DISTRICT}}':             dist,
        '{{DISTRICT_SLUG}}':        dist_slug,
        '{{BLOCK}}':                block,
        '{{VILLAGE}}':              village,
        '{{CLUSTER}}':              cluster,
        '{{LOCATION_TYPE}}':        location_label(loc),
        '{{STATE_MGMT}}':           s_mgmt,
        '{{NATIONAL_MGMT}}':        n_mgmt,
        '{{MGMT_SHORT}}':           mgmt_short(n_mgmt),
        '{{SCHOOL_CATEGORY}}':      cat,
        '{{CAT_SHORT}}':            cat_short(cat),
        '{{CATEGORY_RANGE}}':       category_range(cat),
        '{{SCHOOL_TYPE}}':          stype,
        '{{SCHOOL_TYPE_SHORT}}':    school_type_short(stype),
        '{{SCHOOL_STATUS}}':        status,
        '{{IS_TRIBAL}}':            'Yes — Tribal Area' if str(is_tribal).upper()=='Y' else 'No',
        '{{TRIBAL_BADGE}}':         '<span class="badge badge-amber">Tribal Area</span>' if str(is_tribal).upper()=='Y' else '',
        '{{IS_TRIBAL_CONTEXT}}':    tribal_village_ctx,
        '{{PIN_CODE}}':             pin_disp,
        # District census data
        '{{DIST_LITERACY_PCT}}':    literacy_pct,
        '{{DIST_MALE_LITERACY}}':   male_lit,
        '{{DIST_FEMALE_LITERACY}}': female_lit,
        '{{DIST_WORKER_PCT}}':      worker_pct,
        '{{DIST_POPULATION_FMT}}':  population_fmt,
        '{{DIST_SEX_RATIO}}':       sex_ratio_disp,
        '{{DIST_CHILD_SEX_RATIO}}': child_sr_disp,
        '{{DIST_TOTAL_SCHOOLS}}':   total_schools_fmt,
        '{{DIST_GOVT_SCHOOLS}}':    govt_schools_fmt,
        '{{DIST_PRIVATE_SCHOOLS}}': priv_schools_fmt,
        '{{DIST_ST_PCT}}':          st_pct,
        '{{DIST_SC_PCT}}':          sc_pct,
        '{{DIST_INHABITED_VILLAGES}}': inhabited_disp,
        '{{DIST_TOWNS}}':           towns_disp,
        '{{DIST_POST_OFFICES}}':    post_disp,
        # Dynamic content
        '{{LITERACY_CONTEXT}}':     lit_ctx,
        '{{SCHOOL_DENSITY_CONTEXT}}': density_ctx,
        '{{TRIBAL_CONTEXT_PARA}}':  tribal_ctx_para,
        '{{RURAL_URBAN_LABEL}}':    rural_urban_lbl,
        '{{RELIGION_BARS}}':        religion_html,
        '{{RELATED_SCHOOLS_HTML}}': related_html,
    }.items():
        html = html.replace(k, str(v))

    return minify_html(html)


# ─────────────────────────────────────────────
# RELATED SCHOOLS HTML
# ─────────────────────────────────────────────
def make_related_html(related):
    html = ''
    for r in related[:6]:
        rn  = str(r.get('school_name','')).strip().title()
        ru  = str(r.get('udise_code','')).strip()
        rv  = clean(r.get('village',''), False).title()
        rm  = mgmt_short(clean(r.get('national_mgmt','')))
        rc  = cat_short(clean(r.get('school_category','')))
        html += f'''<a href="/school/{ru}/" class="related-card">
  <div class="rc-name">{rn}</div>
  <div class="rc-meta">📍 {rv} &nbsp;·&nbsp; {rm}</div>
  <div class="rc-udise">UDISE: {ru}</div>
</a>'''
    return html


# ─────────────────────────────────────────────
# STATE PAGE
# ─────────────────────────────────────────────
def state_page(state_name, districts_counts, total):
    ss    = slugify(state_name)
    cards = ''
    for d, cnt in sorted(districts_counts.items(), key=lambda x: -x[1]):
        ds = slugify(d)
        cards += f'<a href="/state/{ss}/{ds}/" class="state-card"><div><div class="state-name">{d.title()}</div><div class="state-count">{cnt:,} schools</div></div><div class="state-arrow">→</div></a>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Schools in {state_name} – District-wise Directory | {SITE_NAME}</title>
<meta name="description" content="Complete directory of {total:,} schools in {state_name}. Browse by district. Government and private schools with UDISE codes, addresses and census data.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{BASE_URL}/state/{ss}/">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"CollectionPage","name":"Schools in {state_name}","url":"{BASE_URL}/state/{ss}/"}}</script>
{CSS_LINK}
</head>
<body>
<nav><a href="/" class="logo"><div class="logo-icon">🏫</div><span class="logo-text">Schools<span style="color:#38BDF8">pedia</span><span style="color:rgba(255,255,255,.3);font-size:.7rem">.in</span></span></a></nav>
<div style="max-width:1100px;margin:0 auto;padding:2rem 1.5rem">
<nav class="breadcrumb"><a href="/">Home</a> › <span>{state_name}</span></nav>
<h1 style="font-size:1.75rem;font-weight:800;color:var(--navy);margin-bottom:8px">Schools in {state_name}</h1>
<p style="color:var(--muted);margin-bottom:32px;font-weight:300">{total:,} schools across {len(districts_counts)} districts</p>
<div class="state-grid">{cards}</div>
</div>
<footer><p><a href="/">{SITE_NAME}</a> | <a href="/about/">About</a> | <a href="/privacy/">Privacy</a> | <a href="/disclaimer/">Disclaimer</a></p></footer>
</body></html>'''


# ─────────────────────────────────────────────
# DISTRICT PAGE
# ─────────────────────────────────────────────
def district_page(state_name, district_name, school_list, district_data):
    ss = slugify(state_name)
    ds = slugify(district_name)
    d  = district_data or {}
    literacy = fmt_pct(d.get('dist_Literacy_pct',''))
    population = fmt_num(d.get('dist_Population',''))
    total_schools = fmt_num(d.get('dist_Total_Schools',''))

    rows = ''
    for s in school_list[:300]:
        sn = str(s.get('school_name','')).strip().title()
        su = str(s.get('udise_code','')).strip()
        sv = clean(s.get('village',''), False).title()
        sm = mgmt_short(clean(s.get('national_mgmt','')))
        sc_val = cat_short(clean(s.get('school_category','')))
        rows += f'''<a href="/school/{su}/" class="school-row">
<div><div class="school-row-name">{sn}</div><div class="school-row-meta">📍 {sv} &nbsp;·&nbsp; {sm} &nbsp;·&nbsp; {sc_val}</div></div>
<div class="school-row-udise">UDISE<br>{su}</div></a>'''

    census_strip = ''
    if literacy != 'N/A':
        census_strip = f'''<div style="display:flex;gap:20px;flex-wrap:wrap;background:var(--cream);border-radius:10px;padding:14px 18px;margin-bottom:24px;border:1px solid var(--border)">
<div><span style="font-size:1.1rem;font-weight:800;color:var(--navy);font-family:monospace">{literacy}%</span><br><span style="font-size:.72rem;color:var(--muted)">Literacy Rate</span></div>
<div><span style="font-size:1.1rem;font-weight:800;color:var(--navy);font-family:monospace">{population}</span><br><span style="font-size:.72rem;color:var(--muted)">Population</span></div>
<div><span style="font-size:1.1rem;font-weight:800;color:var(--navy);font-family:monospace">{total_schools}</span><br><span style="font-size:.72rem;color:var(--muted)">Total Schools</span></div>
</div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Schools in {district_name}, {state_name} – {len(school_list):,} Schools | {SITE_NAME}</title>
<meta name="description" content="{len(school_list):,} schools in {district_name}, {state_name}. Literacy rate: {literacy}%. Find government and private schools with UDISE codes, addresses and details.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{BASE_URL}/state/{ss}/{ds}/">
{CSS_LINK}
</head>
<body>
<nav><a href="/" class="logo"><div class="logo-icon">🏫</div><span class="logo-text">Schools<span style="color:#38BDF8">pedia</span><span style="color:rgba(255,255,255,.3);font-size:.7rem">.in</span></span></a></nav>
<div style="max-width:960px;margin:0 auto;padding:2rem 1.5rem">
<nav class="breadcrumb"><a href="/">Home</a> › <a href="/state/{ss}/">{state_name}</a> › <span>{district_name}</span></nav>
<h1 style="font-size:1.75rem;font-weight:800;color:var(--navy);margin-bottom:8px">Schools in {district_name}</h1>
<p style="color:var(--muted);margin-bottom:20px;font-weight:300">{state_name} &nbsp;·&nbsp; {len(school_list):,} schools</p>
{census_strip}
<p style="color:var(--muted);font-size:.82rem;margin-bottom:20px;font-weight:300">Showing {min(len(school_list),300)} of {len(school_list):,} schools. <a href="/" style="color:var(--saffron)">Search</a> to find a specific school.</p>
<div class="school-list">{rows}</div>
</div>
<footer><p><a href="/">{SITE_NAME}</a> | <a href="/about/">About</a> | <a href="/privacy/">Privacy</a></p></footer>
</body></html>'''


# ─────────────────────────────────────────────
# HOMEPAGE
# ─────────────────────────────────────────────
def homepage(state_index):
    total_schools = sum(sum(len(sl) for sl in dists.values()) for dists in state_index.values())
    state_cards = ''
    for state_name in sorted(state_index.keys())[:24]:
        cnt = sum(len(sl) for sl in state_index[state_name].values())
        ss  = slugify(state_name)
        state_cards += f'<a href="/state/{ss}/" class="state-card"><div><div class="state-name">{state_name}</div><div class="state-count">{cnt:,} schools</div></div><div class="state-arrow">→</div></a>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Indian Schools Directory – Find Any School in India | {SITE_NAME}</title>
<meta name="description" content="Find any of India's {total_schools:,}+ schools. Search by name, UDISE code, state, district or village. Government and private schools with complete details from official UDISE data.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{BASE_URL}/">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"{SITE_NAME}","url":"{BASE_URL}","potentialAction":{{"@type":"SearchAction","target":"{BASE_URL}/search/?q={{search_term_string}}","query-input":"required name=search_term_string"}}}}</script>
{CSS_LINK}
<style>
.hero-section{{background:linear-gradient(135deg,#1C2B3A 0%,#152B58 60%,#1a3a6b 100%);padding:70px 2rem 80px;text-align:center;position:relative;overflow:hidden}}
.hero-section::before{{content:'';position:absolute;top:-30%;left:-10%;width:120%;height:200%;background:radial-gradient(ellipse at 30% 40%,rgba(255,107,0,0.12) 0%,transparent 60%),radial-gradient(ellipse at 70% 60%,rgba(19,136,8,0.08) 0%,transparent 50%);pointer-events:none}}
.hero-badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(255,107,0,0.15);border:1px solid rgba(255,107,0,0.3);color:#ff9050;padding:5px 16px;border-radius:100px;font-size:.78rem;font-weight:700;letter-spacing:.5px;margin-bottom:22px;text-transform:uppercase}}
.hero-h1{{font-size:clamp(1.8rem,5vw,3.2rem);font-weight:800;color:white;line-height:1.15;letter-spacing:-1.5px;margin-bottom:16px}}
.hero-h1 span{{color:#FF8C38}}
.hero-sub{{color:rgba(255,255,255,0.6);font-size:1rem;font-weight:300;max-width:500px;margin:0 auto 36px}}
.search-wrap{{max-width:660px;margin:0 auto;position:relative}}
.search-wrap input{{width:100%;padding:18px 150px 18px 22px;font-size:.95rem;font-family:'Lexend',sans-serif;border:none;border-radius:14px;background:rgba(255,255,255,0.97);box-shadow:0 8px 40px rgba(0,0,0,0.25);outline:none;color:#1A1A2E}}
.search-wrap input:focus{{box-shadow:0 8px 40px rgba(0,0,0,0.3),0 0 0 3px rgba(255,107,0,0.3)}}
.search-btn{{position:absolute;right:7px;top:50%;transform:translateY(-50%);background:linear-gradient(135deg,#38BDF8,#e55d00);color:white;border:none;padding:11px 24px;border-radius:10px;font-size:.85rem;font-weight:700;font-family:'Lexend',sans-serif;cursor:pointer}}
.search-tags{{margin-top:14px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}}
.stag{{background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.7);border:1px solid rgba(255,255,255,0.15);padding:4px 12px;border-radius:100px;font-size:.75rem;cursor:pointer;text-decoration:none;transition:all .2s}}
.stag:hover{{background:rgba(255,107,0,0.2);color:#ff9050}}
.stats-strip{{background:white;padding:24px 2rem;display:flex;justify-content:center;gap:3rem;border-bottom:1px solid #E5E7EB;flex-wrap:wrap}}
.sstat{{text-align:center}}
.sstat-n{{font-size:1.8rem;font-weight:800;color:#38BDF8;letter-spacing:-1px;display:block;font-family:'JetBrains Mono',monospace}}
.sstat-l{{font-size:.72rem;color:#6B7280;font-weight:400;text-transform:uppercase;letter-spacing:.5px}}
.sec{{padding:52px 0}}
.sec-title{{font-size:1.5rem;font-weight:800;color:#1C2B3A;letter-spacing:-.3px;margin-bottom:6px}}
.sec-sub{{color:#6B7280;font-size:.9rem;font-weight:300;margin-bottom:28px}}
.features-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}}
.feat{{background:white;border:1px solid #E5E7EB;border-radius:14px;padding:24px}}
.feat-icon{{font-size:1.8rem;margin-bottom:12px}}
.feat-title{{font-weight:700;font-size:.95rem;color:#1C2B3A;margin-bottom:6px}}
.feat-text{{font-size:.85rem;color:#6B7280;font-weight:300;line-height:1.7}}
.about-strip{{background:linear-gradient(135deg,#FFF8F0,#FFF3E5);border:1px solid rgba(255,107,0,0.2);border-radius:16px;padding:28px 32px;margin:0 0 32px}}
</style>
</head>
<body>
<nav>
  <a href="/" class="logo"><div class="logo-icon">🏫</div><span class="logo-text">Schools<span style="color:#38BDF8">pedia</span><span style="color:rgba(255,255,255,.3);font-size:.7rem">.in</span></span></a>
  <div style="display:flex;gap:1.5rem;align-items:center">
    <a href="/articles/" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:.82rem">Articles</a>
    <a href="/about/" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:.82rem">About</a>
  </div>
</nav>

<section class="hero-section">
  <div class="hero-badge">🇮🇳 India's Most Complete School Directory</div>
  <h1 class="hero-h1">Find Any School<br>Across <span>India</span></h1>
  <p class="hero-sub">Search from {total_schools:,}+ verified schools — with district census data, literacy rates, and complete UDISE information.</p>
  <div class="search-wrap">
    <input type="text" id="hs" placeholder="Search school name, UDISE code, village…" autocomplete="off">
    <button class="search-btn" onclick="doSearch()">Search →</button>
  </div>
  <div class="search-tags">
    <a href="/state/delhi/" class="stag">Delhi</a>
    <a href="/state/maharashtra/" class="stag">Maharashtra</a>
    <a href="/state/uttar-pradesh/" class="stag">Uttar Pradesh</a>
    <a href="/state/rajasthan/" class="stag">Rajasthan</a>
    <a href="/state/assam/" class="stag">Assam</a>
    <a href="/state/karnataka/" class="stag">Karnataka</a>
    <a href="/state/tamil-nadu/" class="stag">Tamil Nadu</a>
    <a href="/state/west-bengal/" class="stag">West Bengal</a>
  </div>
</section>

<div class="stats-strip">
  <div class="sstat"><span class="sstat-n">{total_schools:,}</span><span class="sstat-l">Total Schools</span></div>
  <div class="sstat"><span class="sstat-n">36</span><span class="sstat-l">States & UTs</span></div>
  <div class="sstat"><span class="sstat-n">700+</span><span class="sstat-l">Districts</span></div>
  <div class="sstat"><span class="sstat-n">6L+</span><span class="sstat-l">Villages Covered</span></div>
</div>

<div style="max-width:1200px;margin:0 auto;padding:0 2rem">

  <!-- AD SLOT -->
  <div style="background:#F9FAFB;border:1px dashed #E5E7EB;border-radius:10px;padding:12px;text-align:center;margin:28px 0;min-height:90px;display:flex;align-items:center;justify-content:center;color:#9CA3AF;font-size:.75rem">Advertisement</div>

  <!-- About strip -->
  <div class="about-strip">
    <p style="font-size:.95rem;color:#374151;font-weight:300;line-height:1.8;margin:0">
      <strong style="color:#1C2B3A">About this directory:</strong> SchoolsIndia.in is built and maintained by <strong>Sahajul</strong> from Tezpur, Assam — a writer with fourteen years of experience covering education in India. Every school page on this site combines official UDISE data with Census of India demographic information to give parents, students and researchers the most complete picture of any school and its surrounding district. Data is sourced from official government databases and is provided free of charge. &nbsp;<a href="/about/" style="color:#38BDF8">Read more about this project →</a>
    </p>
  </div>

  <!-- Browse by State -->
  <section class="sec">
    <div class="sec-title">Browse Schools by State</div>
    <div class="sec-sub">Select a state to see all schools by district</div>
    <div class="state-grid">{state_cards}</div>
    <div style="margin-top:20px;text-align:center">
      <a href="/states/" style="display:inline-block;background:var(--cream);border:1px solid var(--border);border-radius:10px;padding:10px 24px;font-size:.85rem;font-weight:600;color:var(--navy);text-decoration:none">View all 36 States & UTs →</a>
    </div>
  </section>

  <!-- Why use this -->
  <section class="sec" style="padding-top:0">
    <div class="sec-title">Why SchoolsIndia.in?</div>
    <div class="sec-sub">More than just a school list — context, data, and clarity</div>
    <div class="features-grid">
      <div class="feat"><div class="feat-icon">📊</div><div class="feat-title">Census Data on Every Page</div><p class="feat-text">Each school page shows district-level literacy rates, sex ratios, population data and school density from the Census of India — context that no other school directory provides.</p></div>
      <div class="feat"><div class="feat-icon">🔍</div><div class="feat-title">Official UDISE Source</div><p class="feat-text">All school data is sourced directly from India's UDISE database — the most authoritative source of school information maintained by the Ministry of Education.</p></div>
      <div class="feat"><div class="feat-icon">📍</div><div class="feat-title">Village-Level Accuracy</div><p class="feat-text">Every school is mapped to its village, block, district and cluster — making it possible to find schools even in the most remote areas of the country.</p></div>
      <div class="feat"><div class="feat-icon">✍️</div><div class="feat-title">Human-Written Content</div><p class="feat-text">Written and maintained by Sahajul, a journalist from Tezpur, Assam with 14 years of experience writing about education in India. Real perspective, not generated text.</p></div>
    </div>
  </section>

  <!-- Articles -->
  <section class="sec" style="padding-top:0">
    <div class="sec-title">Latest Articles</div>
    <div class="sec-sub">In-depth writing on Indian education by Sahajul</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px">
      <a href="/articles/how-to-find-school-udise-code/" style="background:white;border:1px solid #E5E7EB;border-radius:12px;padding:20px;text-decoration:none;color:#1A1A2E;display:block;transition:all .2s" onmouseover="this.style.borderColor='#38BDF8'" onmouseout="this.style.borderColor='#E5E7EB'">
        <div style="font-size:.72rem;font-weight:700;color:#4F46E5;background:#EEF2FF;padding:3px 10px;border-radius:100px;display:inline-block;margin-bottom:10px">GUIDE</div>
        <div style="font-weight:700;font-size:.92rem;color:#1C2B3A;line-height:1.4;margin-bottom:6px">How to Find Any School in India Using UDISE Code</div>
        <div style="font-size:.75rem;color:#6B7280">January 2025 &nbsp;·&nbsp; 9 min read</div>
      </a>
      <a href="/articles/government-vs-private-schools-india/" style="background:white;border:1px solid #E5E7EB;border-radius:12px;padding:20px;text-decoration:none;color:#1A1A2E;display:block;transition:all .2s" onmouseover="this.style.borderColor='#38BDF8'" onmouseout="this.style.borderColor='#E5E7EB'">
        <div style="font-size:.72rem;font-weight:700;color:#138808;background:#EEF7EE;padding:3px 10px;border-radius:100px;display:inline-block;margin-bottom:10px">ANALYSIS</div>
        <div style="font-weight:700;font-size:.92rem;color:#1C2B3A;line-height:1.4;margin-bottom:6px">Government vs Private Schools: What the Data Actually Says</div>
        <div style="font-size:.75rem;color:#6B7280">January 2025 &nbsp;·&nbsp; 10 min read</div>
      </a>
      <a href="/articles/girls-education-india/" style="background:white;border:1px solid #E5E7EB;border-radius:12px;padding:20px;text-decoration:none;color:#1A1A2E;display:block;transition:all .2s" onmouseover="this.style.borderColor='#38BDF8'" onmouseout="this.style.borderColor='#E5E7EB'">
        <div style="font-size:.72rem;font-weight:700;color:#38BDF8;background:#FFF3E8;padding:3px 10px;border-radius:100px;display:inline-block;margin-bottom:10px">FEATURE</div>
        <div style="font-weight:700;font-size:.92rem;color:#1C2B3A;line-height:1.4;margin-bottom:6px">Girls' Education in India: How Far We Have Come</div>
        <div style="font-size:.75rem;color:#6B7280">January 2025 &nbsp;·&nbsp; 10 min read</div>
      </a>
    </div>
    <div style="margin-top:18px;text-align:center">
      <a href="/articles/" style="display:inline-block;background:var(--cream);border:1px solid var(--border);border-radius:10px;padding:10px 24px;font-size:.85rem;font-weight:600;color:var(--navy);text-decoration:none">View all 20 articles →</a>
    </div>
  </section>

</div>

<footer>
  <p>Data: <strong>UDISE – Ministry of Education, Govt. of India</strong> &nbsp;·&nbsp; Census of India &nbsp;|&nbsp; <a href="/">SchoolsIndia.in</a></p>
  <p style="margin-top:6px;font-size:.75rem"><a href="/about/">About</a> · <a href="/privacy/">Privacy</a> · <a href="/disclaimer/">Disclaimer</a> · <a href="/terms/">Terms</a> · <a href="/contact/">Contact</a> · <a href="/articles/">Articles</a> · <a href="/sitemap.xml">Sitemap</a></p>
</footer>

<script>
function doSearch(){{
  const q=document.getElementById('hs').value.trim();
  if(q) window.location.href='/search/?q='+encodeURIComponent(q);
}}
document.getElementById('hs').addEventListener('keydown',e=>{{if(e.key==='Enter')doSearch()}});
</script>
</body></html>'''


# ─────────────────────────────────────────────
# SITEMAPS
# ─────────────────────────────────────────────
def sitemap_batch(urls, priority='0.7'):
    today = datetime.now().strftime('%Y-%m-%d')
    entries = ''.join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>{priority}</priority></url>' for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'

def sitemap_index(n):
    today = datetime.now().strftime('%Y-%m-%d')
    entries = f'<sitemap><loc>{BASE_URL}/sitemap-states.xml</loc><lastmod>{today}</lastmod></sitemap>'
    for i in range(1, n+1):
        entries += f'<sitemap><loc>{BASE_URL}/sitemap-schools-{i}.xml</loc><lastmod>{today}</lastmod></sitemap>'
    return f'<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</sitemapindex>'


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',   default='schools.csv')
    parser.add_argument('--village', default='LocalDataHub_Village_Master_v2.csv')
    parser.add_argument('--output',  default='output')
    parser.add_argument('--limit',   type=int, default=0)
    parser.add_argument('--template',default='templates\\school-detail.html')
    args = parser.parse_args()

    out = args.output
    os.makedirs(out, exist_ok=True)

    # Load template
    tmpl_path = args.template
    if not os.path.exists(tmpl_path):
        for alt in ['templates/school-detail.html',
                    os.path.join(os.path.dirname(__file__),'..','templates','school-detail.html')]:
            if os.path.exists(alt):
                tmpl_path = alt; break
        else:
            print(f"ERROR: template not found at {tmpl_path}"); sys.exit(1)

    with open(tmpl_path, encoding='utf-8') as f:
        template = f.read()

    # Load schools
    print(f"Reading schools CSV: {args.input}")
    schools = []
    with open(args.input, encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [c.strip().lstrip('\ufeff') for c in reader.fieldnames]
        for row in reader:
            schools.append({k.strip(): v for k,v in row.items()})
            if args.limit and len(schools) >= args.limit:
                break
    print(f"  Loaded {len(schools):,} schools")

    # Load village/district data
    district_lookup = {}
    if os.path.exists(args.village):
        print(f"Reading village/district CSV: {args.village}")
        vrows = read_csv(args.village)
        district_lookup, _ = build_village_index(vrows)
        print(f"  Loaded {len(district_lookup):,} district entries")
    else:
        print(f"WARNING: village CSV not found at {args.village} — pages will lack census data")

    # Build indexes
    state_index    = defaultdict(lambda: defaultdict(list))
    district_index = defaultdict(list)

    for s in schools:
        st  = clean(s.get('state',''), False)
        dis = clean(s.get('district',''), False).title()
        state_index[st][dis].append(s)
        district_index[slugify(dis)].append(s)

    # Copy CSS
    for css_src in ['static/css/style.css',
                    os.path.join(os.path.dirname(__file__),'..','static','css','style.css')]:
        if os.path.exists(css_src):
            shutil.copy(css_src, os.path.join(out, 'style.css'))
            print("Copied style.css"); break

    # Generate school pages
    all_urls = []
    print(f"\nGenerating school pages...")
    for i, school in enumerate(schools):
        udise = str(school.get('udise_code','')).strip()
        if not udise or udise == 'nan': continue

        st  = clean(school.get('state',''), False)
        dis = clean(school.get('district',''), False).title()
        d_key = (slugify(st), slugify(dis))
        dist_data = district_lookup.get(d_key, {})

        d_slug = slugify(dis)
        related = [r for r in district_index.get(d_slug,[]) if str(r.get('udise_code','')).strip() != udise][:6]
        related_html = make_related_html(related)

        html = render_school_page(school, template, related_html, dist_data)
        write_file(os.path.join(out,'school',udise,'index.html'), html)
        all_urls.append(f"{BASE_URL}/school/{udise}/")
        if (i+1) % 10000 == 0:
            print(f"  {i+1:,} / {len(schools):,}")

    print(f"  Done! {len(all_urls):,} pages")

    # Generate state + district pages
    print("\nGenerating state/district pages...")
    state_urls = []
    for state_name, districts in state_index.items():
        ss = slugify(state_name)
        district_counts = {d: len(sl) for d,sl in districts.items()}
        total = sum(district_counts.values())
        write_file(os.path.join(out,'state',ss,'index.html'),
                   minify_html(state_page(state_name, district_counts, total)))
        state_urls.append(f"{BASE_URL}/state/{ss}/")

        for dist_name, school_list in districts.items():
            ds  = slugify(dist_name)
            d_key = (ss, ds)
            dist_data = district_lookup.get(d_key, {})
            write_file(os.path.join(out,'state',ss,ds,'index.html'),
                       district_page(state_name, dist_name, school_list, dist_data))

    print(f"  {len(state_index)} states done")

    # Homepage
    write_file(os.path.join(out,'index.html'), homepage(state_index))

    # Sitemaps
    print("\nGenerating sitemaps...")
    write_file(os.path.join(out,'sitemap-states.xml'), sitemap_batch(state_urls,'0.9'))
    n = math.ceil(len(all_urls)/BATCH_SITEMAP_SIZE)
    for i in range(n):
        batch = all_urls[i*BATCH_SITEMAP_SIZE:(i+1)*BATCH_SITEMAP_SIZE]
        write_file(os.path.join(out,f'sitemap-schools-{i+1}.xml'), sitemap_batch(batch))
    write_file(os.path.join(out,'sitemap.xml'), sitemap_index(n))
    write_file(os.path.join(out,'robots.txt'),
               f'User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n\nDisallow: /admin/\n\nUser-agent: AhrefsBot\nCrawl-delay: 10\nUser-agent: SemrushBot\nCrawl-delay: 10\n')

    print(f'''
==============================================
  ✅ DONE!
  School pages : {len(all_urls):,}
  States       : {len(state_index)}
  Output       : {out}/
==============================================
''')

if __name__ == '__main__':
    main()
