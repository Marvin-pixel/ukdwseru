"""
search.py - Fitur Pencarian Anime untuk Anies (Anime List)

Isi modul:
1. Data        : ambil data dari MyAnimeList API v2 -> list of dictionary
2. Algoritma   : linear search berbobot (relevansi), binary search (prefix),
                 filter, dan merge sort (semuanya ditulis manual)
3. UI Streamlit: halaman Explore (pencarian + filter + sorting + detail)

Cara pakai di login.py:
    from search import page_search
    ...
    elif page == "Explore":
        page_search()

Client ID MyAnimeList disimpan di .streamlit/secrets.toml:
    MAL_CLIENT_ID = "isi_client_id_kamu"
Jika kosong / API gagal, aplikasi memakai data contoh (mode demo).
"""

import requests
import streamlit as st

MAL_API = "https://api.myanimelist.net/v2"
FIELDS = (
    "id,title,main_picture,alternative_titles,start_date,synopsis,mean,rank,"
    "popularity,genres,num_episodes,status,studios,media_type,start_season"
)
STATUS_ID = {
    "finished_airing": "Selesai tayang",
    "currently_airing": "Sedang tayang",
    "not_yet_aired": "Belum tayang",
}
PER_PAGE = 12
MIN_QUERY_API = 3  # MyAnimeList mensyaratkan kata kunci minimal 3 karakter


# =====================================================================
# 1. DATA
# =====================================================================
def _secret(name: str) -> str:
    try:
        return st.secrets[name]
    except Exception:
        return ""


def get_client_id() -> str:
    return str(_secret("MAL_CLIENT_ID")).strip()


def normalize_mal(node: dict) -> dict:
    """Ubah JSON MyAnimeList menjadi dictionary sederhana (1 dict = 1 anime)."""
    start = node.get("start_date") or ""
    season = node.get("start_season") or {}
    pic = node.get("main_picture") or {}
    alt = node.get("alternative_titles") or {}
    return {
        "id": node.get("id"),
        "title": node.get("title") or "-",
        "title_en": alt.get("en") or "",
        "title_jp": alt.get("ja") or "",
        "image": pic.get("large") or pic.get("medium"),
        "synopsis": node.get("synopsis") or "",
        "score": node.get("mean") or 0.0,
        "rank": node.get("rank"),
        "popularity": node.get("popularity"),
        "genres": [g["name"] for g in node.get("genres", [])],
        "episodes": node.get("num_episodes") or 0,
        "status": STATUS_ID.get(node.get("status"), node.get("status") or "-"),
        "studio": ", ".join(s["name"] for s in node.get("studios", [])) or "-",
        "type": (node.get("media_type") or "-").upper(),
        "year": int(start[:4]) if start[:4].isdigit() else season.get("year"),
    }


def _mal_get(client_id: str, path: str, params: dict) -> dict:
    r = requests.get(
        f"{MAL_API}{path}",
        params=params,
        headers={"X-MAL-CLIENT-ID": client_id},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=3600, show_spinner="Mengambil data dari MyAnimeList...")
def load_catalog(client_id: str) -> list[dict]:
    """Katalog lokal: 300 teratas ranking 'all' + 300 teratas 'bypopularity'."""
    merged: dict[int, dict] = {}
    for ranking_type in ("all", "bypopularity"):
        for offset in (0, 100, 200):
            data = _mal_get(
                client_id,
                "/anime/ranking",
                {"ranking_type": ranking_type, "limit": 100,
                 "offset": offset, "fields": FIELDS},
            )
            for item in data.get("data", []):
                a = normalize_mal(item["node"])
                merged.setdefault(a["id"], a)
    return list(merged.values())


@st.cache_data(ttl=1800, show_spinner=False)
def api_search(client_id: str, query: str) -> list[dict]:
    """Pencarian judul langsung ke MyAnimeList API (endpoint /anime?q=)."""
    data = _mal_get(client_id, "/anime", {"q": query, "limit": 50, "fields": FIELDS})
    return [normalize_mal(i["node"]) for i in data.get("data", [])]


# Data contoh agar aplikasi tetap jalan tanpa Client ID
_SAMPLE = [
    ("Sousou no Frieren", "Frieren: Beyond Journey's End", 9.3, 1, 30, ["Adventure", "Drama", "Fantasy"], 28, 2023, "Madhouse"),
    ("Fullmetal Alchemist: Brotherhood", "", 9.1, 2, 3, ["Action", "Adventure", "Drama", "Fantasy"], 64, 2009, "Bones"),
    ("Steins;Gate", "", 9.07, 3, 13, ["Drama", "Sci-Fi", "Suspense"], 24, 2011, "White Fox"),
    ("Gintama", "", 8.9, 8, 31, ["Action", "Comedy", "Sci-Fi"], 367, 2006, "Sunrise"),
    ("Kusuriya no Hitorigoto", "The Apothecary Diaries", 8.87, 12, 40, ["Drama", "Mystery"], 24, 2023, "OLM"),
    ("Shingeki no Kyojin", "Attack on Titan", 8.57, 100, 1, ["Action", "Drama", "Suspense"], 25, 2013, "Wit Studio"),
    ("Kimetsu no Yaiba", "Demon Slayer", 8.4, 180, 5, ["Action", "Fantasy"], 26, 2019, "ufotable"),
    ("One Piece", "", 8.73, 40, 17, ["Action", "Adventure", "Fantasy"], 1100, 1999, "Toei Animation"),
    ("Jujutsu Kaisen", "", 8.5, 120, 4, ["Action", "Fantasy"], 24, 2020, "MAPPA"),
    ("Death Note", "", 8.62, 70, 2, ["Mystery", "Supernatural", "Suspense"], 37, 2006, "Madhouse"),
    ("Spy x Family", "", 8.6, 90, 8, ["Action", "Comedy"], 12, 2022, "Wit Studio"),
    ("Kaguya-sama wa Kokurasetai", "Kaguya-sama: Love is War", 8.4, 190, 38, ["Comedy", "Romance"], 12, 2019, "A-1 Pictures"),
    ("Violet Evergarden", "", 8.5, 130, 27, ["Drama", "Fantasy"], 13, 2018, "Kyoto Animation"),
    ("Clannad: After Story", "", 8.9, 9, 42, ["Drama", "Romance", "Slice of Life"], 24, 2008, "Kyoto Animation"),
]


def sample_catalog() -> list[dict]:
    return [
        {"id": -i, "title": t, "title_en": en, "title_jp": "", "image": None,
         "synopsis": "Data contoh (mode demo). Isi MAL_CLIENT_ID untuk data asli.",
         "score": s, "rank": r, "popularity": p, "genres": g, "episodes": e,
         "status": "Selesai tayang", "studio": studio, "type": "TV", "year": y}
        for i, (t, en, s, r, p, g, e, y, studio) in enumerate(_SAMPLE, start=1)
    ]


def get_catalog() -> tuple[list[dict], str]:
    """Mengembalikan (katalog, nama_sumber). Gagal/kosong -> data contoh."""
    client_id = get_client_id()
    if not client_id:
        st.warning("MAL_CLIENT_ID belum diatur - mode demo dengan data contoh.")
        return sample_catalog(), "Data contoh"
    try:
        return load_catalog(client_id), "MyAnimeList API v2"
    except requests.RequestException as e:
        st.warning(f"MyAnimeList API gagal ({e}). Periksa Client ID. Memakai data contoh.")
        return sample_catalog(), "Data contoh"


# =====================================================================
# 2. ALGORITMA (ditulis manual, tanpa sorted()/filter() bawaan)
# =====================================================================
def merge_sort(items: list, key, reverse: bool = False) -> list:
    """Merge sort (stabil). Kompleksitas O(n log n)."""
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    left = merge_sort(items[:mid], key, reverse)
    right = merge_sort(items[mid:], key, reverse)

    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if reverse:
            take_left = key(left[i]) >= key(right[j])
        else:
            take_left = key(left[i]) <= key(right[j])
        if take_left:
            out.append(left[i])
            i += 1
        else:
            out.append(right[j])
            j += 1
    return out + left[i:] + right[j:]


def _token_score(a: dict, t: str) -> int:
    """Skor kecocokan satu kata kunci terhadap satu anime (0 = tidak cocok)."""
    best = 0
    for field in ("title", "title_en", "title_jp"):
        text = a.get(field, "").lower()
        if not text:
            continue
        if text == t:
            best = max(best, 100)                              # judul persis
        elif text.startswith(t):
            best = max(best, 80)                               # awal judul
        elif any(w.startswith(t) for w in text.replace(":", " ").split()):
            best = max(best, 60)                               # awal salah satu kata
        elif t in text:
            best = max(best, 40)                               # ada di dalam judul
    if best == 0:
        if any(t in g.lower() for g in a["genres"]):
            best = 20                                          # cocok genre
        elif t in a["studio"].lower():
            best = 15                                          # cocok studio
    return best


def relevance(a: dict, tokens: list[str]) -> int:
    """Semua kata harus cocok (AND). Skor akhir = jumlah skor tiap kata."""
    total = 0
    for t in tokens:
        s = _token_score(a, t)
        if s == 0:
            return 0
        total += s
    return total


def linear_search(items: list[dict], keyword: str, always_include=frozenset()) -> list[dict]:
    """
    Linear search O(n): periksa anime satu per satu, beri skor relevansi,
    lalu urutkan dari yang paling relevan.

    always_include: id anime hasil API yang tetap ditampilkan walau judulnya
    tidak mengandung kata kunci (MAL juga mencari lewat sinonim).
    """
    tokens = keyword.lower().split()
    if not tokens:
        return list(items)

    scored = []
    for a in items:
        s = relevance(a, tokens)
        if s == 0 and a["id"] in always_include:
            s = 5
        if s > 0:
            scored.append({"score": s, "anime": a})

    scored = merge_sort(scored, lambda r: r["score"], reverse=True)
    return [r["anime"] for r in scored]


def build_title_index(items: list[dict]) -> list[dict]:
    """Index judul terurut A-Z (prasyarat binary search)."""
    rows = [{"key": a["title"].lower(), "anime": a} for a in items]
    return merge_sort(rows, lambda r: r["key"])


def binary_search_prefix(index: list[dict], prefix: str) -> list[dict]:
    """
    Binary search O(log n) untuk menemukan posisi pertama judul yang
    berawalan `prefix`, lalu kumpulkan semua judul berawalan sama.
    Dipakai untuk saran judul ("Mungkin maksud kamu").
    """
    p = prefix.strip().lower()
    if not p:
        return []
    lo, hi = 0, len(index)
    while lo < hi:
        mid = (lo + hi) // 2
        if index[mid]["key"] < p:
            lo = mid + 1
        else:
            hi = mid
    out = []
    while lo < len(index) and index[lo]["key"].startswith(p):
        out.append(index[lo]["anime"])
        lo += 1
    return out


def filter_anime(items, genres=(), year_range=None, min_score=0.0) -> list[dict]:
    """Saring berdasarkan genre (harus memuat semua genre pilihan), tahun, skor."""
    out = []
    for a in items:
        if genres and not all(g in a["genres"] for g in genres):
            continue
        if year_range and a["year"] and not (year_range[0] <= a["year"] <= year_range[1]):
            continue
        if a["score"] < min_score:
            continue
        out.append(a)
    return out


def genre_counts(items: list[dict]) -> dict:
    """Jumlah anime per genre (dictionary)."""
    c = {}
    for a in items:
        for g in a["genres"]:
            c[g] = c.get(g, 0) + 1
    return c


RELEVANCE = "Paling relevan"
SORTS = {
    RELEVANCE: None,
    "Skor tertinggi": (lambda a: a["score"], True),
    "Paling populer": (lambda a: a["popularity"] or 10**9, False),
    "Peringkat terbaik": (lambda a: a["rank"] or 10**9, False),
    "Terbaru": (lambda a: a["year"] or 0, True),
    "Judul A-Z": (lambda a: a["title"].lower(), False),
}


# =====================================================================
# 3. UI STREAMLIT
# =====================================================================
@st.dialog("Detail anime", width="large")
def show_detail(a: dict):
    c1, c2 = st.columns([1, 2])
    with c1:
        if a["image"]:
            st.image(a["image"], width=220)
        else:
            st.markdown("## 🎬")
    with c2:
        st.subheader(a["title"])
        if a["title_en"] or a["title_jp"]:
            st.caption(" · ".join(x for x in (a["title_en"], a["title_jp"]) if x))
        st.markdown(" ".join(f"`{g}`" for g in a["genres"]) or "-")
        m = st.columns(3)
        m[0].metric("Skor", a["score"] or "-")
        m[1].metric("Peringkat", f"#{a['rank']}" if a["rank"] else "-")
        m[2].metric("Popularitas", f"#{a['popularity']}" if a["popularity"] else "-")
        st.markdown(f"**Tipe:** {a['type']} · **Episode:** {a['episodes'] or '?'} · "
                    f"**Tahun:** {a['year'] or '-'}")
        st.markdown(f"**Studio:** {a['studio']} · **Status:** {a['status']}")
    st.markdown("**Sinopsis**")
    st.write(a["synopsis"] or "Tidak ada sinopsis.")


def render_cards(items: list[dict], prefix: str, cols: int = 3):
    for i in range(0, len(items), cols):
        row = st.columns(cols)
        for col, a in zip(row, items[i:i + cols]):
            with col, st.container(border=True):
                if a["image"]:
                    st.image(a["image"], width=180)
                else:
                    st.markdown("### 🎬")
                st.markdown(f"**{a['title']}**")
                st.caption(f"⭐ {a['score'] or '-'} · {a['type']} · {a['year'] or '-'}")
                st.caption(" · ".join(a["genres"][:3]) or "-")
                if st.button("Lihat detail", key=f"{prefix}-{a['id']}"):
                    show_detail(a)


def page_search():
    """Halaman Explore: pencarian + filter + sorting + detail."""
    catalog, source = get_catalog()
    st.sidebar.caption(f"Sumber data: {source}")

    st.title("Jelajahi cerita tanpa batas.")
    q = st.text_input("Cari judul, genre, atau studio", placeholder="Contoh: Frieren").strip()

    # --- Gabungkan katalog lokal + hasil pencarian API (tanpa duplikat, kunci = id)
    pool = {a["id"]: a for a in catalog}
    remote_ids = set()
    if len(q) >= MIN_QUERY_API and source.startswith("MyAnimeList"):
        try:
            for a in api_search(get_client_id(), q):
                remote_ids.add(a["id"])
                pool.setdefault(a["id"], a)
        except requests.RequestException as e:
            st.warning(f"Pencarian API gagal, memakai data lokal. ({e})")
    pool = list(pool.values())

    # --- Panel filter
    left, right = st.columns([1, 3])
    years = [a["year"] for a in pool if a["year"]] or [1990, 2026]
    y_min, y_max = min(years), max(years)
    with left, st.container(border=True):
        st.markdown("**Filter anime**")
        genres = st.multiselect("Genre", sorted(genre_counts(pool)))
        yr = st.slider("Tahun rilis", y_min, y_max, (y_min, y_max)) if y_min < y_max else (y_min, y_max)
        min_score = st.slider("Skor minimum", 0.0, 10.0, 0.0, 0.1)
        sort_by = st.selectbox("Urutkan", list(SORTS))

    # --- Searching -> Filtering -> Sorting
    result = linear_search(pool, q, remote_ids)
    result = filter_anime(result, genres, yr, min_score)
    if SORTS[sort_by] is not None:
        keyfn, rev = SORTS[sort_by]
        result = merge_sort(result, keyfn, rev)

    # --- Tampilkan hasil
    with right:
        st.markdown(f"**{len(result):,} anime ditemukan**")

        if not result:
            st.info("Tidak ada hasil. Coba kata kunci lain atau longgarkan filter.")
            if q:
                saran = binary_search_prefix(build_title_index(pool), q[:3])[:5]
                if saran:
                    st.markdown("**Mungkin maksud kamu:** " + ", ".join(a["title"] for a in saran))
            return

        pages = -(-len(result) // PER_PAGE)  # pembulatan ke atas
        page = st.number_input("Halaman", 1, pages, 1) if pages > 1 else 1
        start = (page - 1) * PER_PAGE
        render_cards(result[start:start + PER_PAGE], "exp")
        st.caption(f"Menampilkan {start + 1}-{min(start + PER_PAGE, len(result))} "
                   f"dari {len(result):,} anime · halaman {page}/{pages}")