"""Anies (Anime List) - katalog & rekomendasi anime.
Python + Streamlit + MyAnimeList API v2 + Plotly + OpenPyXL + Gemini.
"""

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from login import LOGO_URL, login_page

st.set_page_config(page_title="Anies - Anime List", page_icon="🎌", layout="wide")

MAL_API = "https://api.myanimelist.net/v2"
FIELDS = ("id,title,main_picture,alternative_titles,start_date,synopsis,mean,rank,"
          "popularity,genres,num_episodes,status,studios,media_type,start_season")
STATUS_ID = {"finished_airing": "Selesai tayang", "currently_airing": "Sedang tayang",
             "not_yet_aired": "Belum tayang"}
PER_PAGE = 12

st.markdown("""
<style>
.hero{padding:2rem 2.2rem;border-radius:18px;margin-bottom:1rem;
background:linear-gradient(120deg,#1b1530 0%,#3b2a73 100%);}
.hero h1{margin:0 0 .3rem 0;font-size:2.4rem}
.hero p{margin:0;opacity:.8}
.rank{color:#a78bfa;font-weight:700}
</style>""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Konfigurasi API key
# --------------------------------------------------------------------------
def get_secret(name: str) -> str:
    try:
        return st.secrets[name]
    except Exception:
        return ""


# # >>> ISI CLIENT ID MYANIMELIST KAMU DI SINI (di antara tanda kutip) <<<
# MAL_CLIENT_ID_MANUAL = ""
# # >>> (opsional) ISI API KEY GEMINI DI SINI <<<
# GEMINI_API_KEY_MANUAL = ""

# Jika kosong, dicoba dari secrets.toml. Semua kosong -> mode demo.
CLIENT_ID = MAL_CLIENT_ID_MANUAL.strip() or get_secret("MAL_CLIENT_ID")
GEMINI_KEY = GEMINI_API_KEY_MANUAL.strip() or get_secret("GEMINI_API_KEY")
GEMINI_MODEL = get_secret("GEMINI_MODEL") or "gemini-2.5-flash"
# --------------------------------------------------------------------------
# Data: MyAnimeList API -> list of dictionary
# --------------------------------------------------------------------------
def normalize_mal(node: dict) -> dict:
    """Ubah JSON MyAnimeList API v2 menjadi dictionary sederhana."""
    start = node.get("start_date") or ""
    season = node.get("start_season") or {}
    pic = node.get("main_picture") or {}
    return {
        "id": node.get("id"),
        "title": node.get("title") or "-",
        "title_jp": (node.get("alternative_titles") or {}).get("ja", ""),
        "image": pic.get("large") or pic.get("medium"),
        "synopsis": node.get("synopsis") or "",
        "score": node.get("mean") or 0.0,
        "rank": node.get("rank"),
        "popularity": node.get("popularity"),
        "genres": [g["name"] for g in node.get("genres", [])],
        "episodes": node.get("num_episodes") or 0,
        "status": STATUS_ID.get(node.get("status"), node.get("status") or "-"),
        "studio": ", ".join(x["name"] for x in node.get("studios", [])) or "-",
        "type": (node.get("media_type") or "-").upper(),
        "year": int(start[:4]) if start[:4].isdigit() else season.get("year"),
    }


def mal_get(path: str, params: dict) -> dict:
    r = requests.get(f"{MAL_API}{path}", params=params,
                     headers={"X-MAL-CLIENT-ID": CLIENT_ID}, timeout=15)
    r.raise_for_status()
    return r.json()


SAMPLE = [  # data contoh agar aplikasi tetap jalan tanpa Client ID
    ("Sousou no Frieren", 9.3, 1, 30, ["Adventure", "Drama", "Fantasy"], 28, 2023, "Madhouse"),
    ("Fullmetal Alchemist: Brotherhood", 9.1, 2, 3, ["Action", "Adventure", "Drama", "Fantasy"], 64, 2009, "Bones"),
    ("Steins;Gate", 9.07, 3, 13, ["Drama", "Sci-Fi", "Suspense"], 24, 2011, "White Fox"),
    ("Gintama", 8.9, 8, 31, ["Action", "Comedy", "Sci-Fi"], 367, 2006, "Sunrise"),
    ("Kusuriya no Hitorigoto", 8.87, 12, 40, ["Drama", "Mystery"], 24, 2023, "OLM"),
    ("Shingeki no Kyojin", 8.57, 100, 1, ["Action", "Drama", "Suspense"], 25, 2013, "Wit Studio"),
    ("Kimetsu no Yaiba", 8.4, 180, 5, ["Action", "Fantasy"], 26, 2019, "ufotable"),
    ("One Piece", 8.73, 40, 17, ["Action", "Adventure", "Fantasy"], 1100, 1999, "Toei Animation"),
    ("Jujutsu Kaisen", 8.5, 120, 4, ["Action", "Fantasy"], 24, 2020, "MAPPA"),
    ("Death Note", 8.62, 70, 2, ["Mystery", "Supernatural", "Suspense"], 37, 2006, "Madhouse"),
    ("Spy x Family", 8.6, 90, 8, ["Action", "Comedy"], 12, 2022, "Wit Studio"),
    ("Kaguya-sama wa Kokurasetai", 8.4, 190, 38, ["Comedy", "Romance"], 12, 2019, "A-1 Pictures"),
    ("Violet Evergarden", 8.5, 130, 27, ["Drama", "Fantasy"], 13, 2018, "Kyoto Animation"),
    ("Clannad: After Story", 8.9, 9, 42, ["Drama", "Romance", "Slice of Life"], 24, 2008, "Kyoto Animation"),
]


def sample_catalog() -> list[dict]:
    return [{"id": -i, "title": t, "title_jp": "", "image": None,
             "synopsis": "Data contoh (mode demo). Isi MAL_CLIENT_ID untuk data asli.",
             "score": s, "rank": r, "popularity": p, "genres": g, "episodes": e,
             "status": "Selesai tayang", "studio": st_, "type": "TV", "year": y}
            for i, (t, s, r, p, g, e, y, st_) in enumerate(SAMPLE, start=1)]


@st.cache_data(ttl=3600, show_spinner="Mengambil data dari MyAnimeList...")
def load_catalog_mal(client_id: str) -> list[dict]:
    """Ranking 'all' + 'bypopularity' (masing-masing 300 teratas), digabung per id."""
    merged: dict[int, dict] = {}
    for ranking_type in ("all", "bypopularity"):
        for offset in (0, 100, 200):
            data = mal_get("/anime/ranking", {"ranking_type": ranking_type, "limit": 100,
                                              "offset": offset, "fields": FIELDS})
            for item in data.get("data", []):
                a = normalize_mal(item["node"])
                merged.setdefault(a["id"], a)
    return list(merged.values())


@st.cache_data(ttl=1800, show_spinner=False)
def api_search_mal(client_id: str, q: str) -> list[dict]:
    data = mal_get("/anime", {"q": q, "limit": 50, "fields": FIELDS})
    return [normalize_mal(i["node"]) for i in data.get("data", [])]


def get_catalog() -> tuple[list[dict], str]:
    """MAL v2 jika MAL_CLIENT_ID ada; kosong/gagal -> data contoh (mode demo)."""
    if not CLIENT_ID:
        st.warning("MAL_CLIENT_ID belum diatur - mode demo dengan data contoh.")
        return sample_catalog(), "Data contoh"
    try:
        return load_catalog_mal(CLIENT_ID), "MyAnimeList API v2"
    except requests.RequestException as e:
        st.warning(f"MyAnimeList API gagal ({e}). Periksa Client ID. Memakai data contoh.")
        return sample_catalog(), "Data contoh"


def search_remote(q: str) -> list[dict]:
    if st.session_state.get("source", "").startswith("MyAnimeList"):
        return api_search_mal(CLIENT_ID, q)
    return []


# --------------------------------------------------------------------------
# Algoritma: searching, filtering, sorting (ditulis manual)
# --------------------------------------------------------------------------
def linear_search(items: list[dict], keyword: str) -> list[dict]:
    kw = keyword.strip().lower()
    if not kw:
        return list(items)
    return [a for a in items
            if kw in a["title"].lower() or kw in a["title_jp"].lower()
            or any(kw in g.lower() for g in a["genres"])]


def filter_anime(items, genres=(), year_range=None, min_score=0.0):
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


def merge_sort(items: list[dict], key, reverse=False) -> list[dict]:
    if len(items) <= 1:
        return items
    mid = len(items) // 2
    left, right = merge_sort(items[:mid], key, reverse), merge_sort(items[mid:], key, reverse)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        take_left = key(left[i]) >= key(right[j]) if reverse else key(left[i]) <= key(right[j])
        if take_left:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    return out + left[i:] + right[j:]


SORTS = {
    "Skor tertinggi": (lambda a: a["score"], True),
    "Paling populer": (lambda a: a["popularity"] or 10**9, False),
    "Peringkat terbaik": (lambda a: a["rank"] or 10**9, False),
    "Terbaru": (lambda a: a["year"] or 0, True),
    "Judul A-Z": (lambda a: a["title"].lower(), False),
}


def genre_counts(items: list[dict]) -> dict:
    """Hitung jumlah anime per genre (dictionary)."""
    c = {}
    for a in items:
        for g in a["genres"]:
            c[g] = c.get(g, 0) + 1
    return c


def top_genres(counts: dict, n: int) -> list[tuple]:
    """n genre terbanyak, diurutkan dengan merge sort buatan sendiri."""
    rows = [{"genre": g, "n": v} for g, v in counts.items()]
    rows = merge_sort(rows, lambda r: r["n"], True)
    return [(r["genre"], r["n"]) for r in rows[:n]]


# --------------------------------------------------------------------------
# Ekspor Excel
# --------------------------------------------------------------------------
def to_excel(items: list[dict], note: str = "") -> bytes:
    df = pd.DataFrame([{
        "Judul": a["title"], "Genre": ", ".join(a["genres"]), "Skor": a["score"],
        "Peringkat": a["rank"], "Popularitas": a["popularity"], "Episode": a["episodes"],
        "Status": a["status"], "Studio": a["studio"], "Tahun": a["year"]} for a in items])
    scores = [a["score"] for a in items if a["score"]]
    summary = pd.DataFrame({"Ringkasan": ["Filter/pencarian", "Jumlah anime", "Rata-rata skor", "Skor tertinggi"],
                            "Nilai": [note or "-", len(items),
                                      round(sum(scores) / len(scores), 2) if scores else 0,
                                      max(scores) if scores else 0]})
    path = "anies_export.xlsx"  # file sementara, ditimpa setiap ekspor
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Anime", index=False)
        summary.to_excel(w, sheet_name="Ringkasan", index=False)
    with open(path, "rb") as f:
        return f.read()


# --------------------------------------------------------------------------
# Komponen UI
# --------------------------------------------------------------------------
@st.dialog("Detail anime", width="large")
def show_detail(a: dict):
    c1, c2 = st.columns([1, 2])
    with c1:
        if a["image"]:
            st.image(a["image"], use_container_width=True)
        else:
            st.markdown("## 🎬")
    with c2:
        st.subheader(a["title"])
        if a["title_jp"]:
            st.caption(a["title_jp"])
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


def render_cards(items: list[dict], prefix: str, cols: int = 4):
    for i in range(0, len(items), cols):
        row = st.columns(cols)
        for col, a in zip(row, items[i:i + cols]):
            with col, st.container(border=True):
                if a["image"]:
                    st.image(a["image"], use_container_width=True)
                else:
                    st.markdown("### 🎬")
                st.markdown(f"**{a['title']}**")
                st.caption(f"⭐ {a['score']} · {a['type']} · {a['year'] or '-'}")
                st.caption(" · ".join(a["genres"][:3]))
                if st.button("Lihat detail", key=f"{prefix}-{a['id']}-{i}", use_container_width=True):
                    show_detail(a)


# --------------------------------------------------------------------------
# Halaman
# --------------------------------------------------------------------------
def page_home(catalog):
    st.markdown("""<div class="hero"><h1>Temukan Anime Favoritmu.</h1>
    <p>Jelajahi ribuan cerita. Temukan yang paling kamu suka.</p></div>""", unsafe_allow_html=True)

    gc = genre_counts(catalog)
    scores = [a["score"] for a in catalog if a["score"]]
    m = st.columns(4)
    m[0].metric("Anime dalam katalog", f"{len(catalog):,}")
    m[1].metric("Genre untuk dijelajahi", len(gc))
    m[2].metric("Skor tertinggi", max(scores) if scores else 0)
    m[3].metric("Rata-rata skor", round(sum(scores) / len(scores), 2) if scores else 0)

    st.subheader("Anime populer")
    st.caption("Cerita yang sedang jadi perbincangan.")
    render_cards(merge_sort(catalog, SORTS["Paling populer"][0])[:8], "pop")

    st.subheader("Rating tinggi, cerita tak terlupakan")
    for n, a in enumerate(merge_sort(catalog, lambda x: x["score"], True)[:5], start=1):
        with st.container(border=True):
            c = st.columns([1, 8, 2])
            c[0].markdown(f"<span class='rank'>#{n:02d}</span>", unsafe_allow_html=True)
            c[1].markdown(f"**{a['title']}**  \n{' · '.join(a['genres'][:3])}")
            c[2].markdown(f"⭐ **{a['score']}** / 10")


def page_explore(catalog):
    st.title("Jelajahi cerita tanpa batas.")
    q = st.text_input("Cari judul, genre, atau studio", placeholder="Contoh: Frieren")
    left, right = st.columns([1, 3])

    pool = catalog
    if q and len(q) >= 3 and st.session_state.get('source') != 'Data contoh':  # tambahkan hasil pencarian API
        try:
            extra = {a["id"]: a for a in search_remote(q)}
            extra.update({a["id"]: a for a in catalog})
            pool = list(extra.values())
        except requests.RequestException as e:
            st.warning(f"Pencarian API gagal, memakai data lokal. ({e})")

    all_genres = sorted(genre_counts(pool))
    years = [a["year"] for a in pool if a["year"]] or [1990, 2026]
    with left, st.container(border=True):
        st.markdown("**Filter anime**")
        genres = st.multiselect("Genre", all_genres)
        yr = st.slider("Tahun rilis", min(years), max(years), (min(years), max(years)))
        min_score = st.slider("Skor minimum", 0.0, 10.0, 0.0, 0.1)
        sort_by = st.selectbox("Urutkan", list(SORTS))

    result = filter_anime(linear_search(pool, q), genres, yr, min_score)
    keyfn, rev = SORTS[sort_by]
    result = merge_sort(result, keyfn, rev)

    with right:
        top = st.columns([3, 1])
        top[0].markdown(f"**{len(result):,} anime ditemukan**")
        note = f"kata kunci='{q}', genre={genres or 'semua'}, tahun={yr}, skor>={min_score}"
        top[1].download_button("⬇️ Excel", to_excel(result, note), "anies_hasil.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               disabled=not result, use_container_width=True)
        pages = max(1, -(-len(result) // PER_PAGE))
        page = st.number_input("Halaman", 1, pages, 1) if pages > 1 else 1
        start = (page - 1) * PER_PAGE
        render_cards(result[start:start + PER_PAGE], "exp", cols=3)
        st.caption(f"Menampilkan {start + 1 if result else 0}-{min(start + PER_PAGE, len(result))} "
                   f"dari {len(result):,} anime · halaman {page}/{pages}")


def page_stats(catalog):
    st.title("Dunia anime dalam angka.")
    gc = genre_counts(catalog)
    scores = [a["score"] for a in catalog if a["score"]]
    m = st.columns(4)
    m[0].metric("Total anime", f"{len(catalog):,}")
    m[1].metric("Ragam genre", len(gc))
    m[2].metric("Skor tertinggi", max(scores) if scores else 0)
    m[3].metric("Rata-rata skor", round(sum(scores) / len(scores), 2) if scores else 0)

    c1, c2 = st.columns(2)
    with c1:
        top_n = top_genres(gc, 10)
        df = pd.DataFrame(top_n, columns=["Genre", "Jumlah"]).iloc[::-1]
        fig = px.bar(df, x="Jumlah", y="Genre", orientation="h", title="Genre paling banyak dijelajahi",
                     color_discrete_sequence=["#a78bfa"])
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        df = pd.DataFrame([{"Judul": a["title"], "Skor": a["score"], "Popularitas": a["popularity"],
                            "Genre": a["genres"][0] if a["genres"] else "-"}
                           for a in catalog if a["score"] and a["popularity"]])
        fig = px.scatter(df, x="Popularitas", y="Skor", color="Genre", hover_name="Judul",
                         title="Skor vs popularitas (peringkat kecil = lebih populer)")
        fig.update_xaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

    if gc:
        name, n = top_genres(gc, 1)[0]
        st.info(f"**{name}** memimpin dengan {n:,} judul di katalog saat ini.")
    st.download_button("⬇️ Ekspor katalog ke Excel", to_excel(catalog, "seluruh katalog"),
                       "anies_katalog.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def ask_gemini(prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=GEMINI_KEY)
    return client.models.generate_content(model=GEMINI_MODEL, contents=prompt).text


def page_ai(catalog):
    st.title("Cerita berikutnya, lebih personal.")
    st.caption("Beri tahu apa yang kamu suka. Biarkan AI membantu menemukan anime untukmu.")
    left, right = st.columns([1, 2])
    with left, st.container(border=True):
        genres = st.multiselect("Genre favorit", sorted(genre_counts(catalog)))
        yr = st.slider("Preferensi tahun", 1990, 2026, (2015, 2026))
        min_score = st.slider("Skor minimum", 0.0, 10.0, 7.5, 0.1)
        extra = st.text_area("Catatan tambahan (opsional)", placeholder="Misal: santai, tidak terlalu panjang")
        go = st.button("✨ Dapatkan rekomendasi", type="primary", use_container_width=True)

    with right:
        if not go:
            st.info("Pilih preferensi lalu klik tombol untuk mendapatkan rekomendasi.")
            return
        cands = filter_anime(catalog, genres, yr, min_score)
        cands = merge_sort(cands, lambda a: a["score"], True)[:15]
        if not cands:
            st.warning("Tidak ada anime yang cocok. Longgarkan filter.")
            return
        if not GEMINI_KEY:
            st.warning("GEMINI_API_KEY belum diisi. Menampilkan kandidat teratas tanpa AI.")
            render_cards(cands[:6], "ai", cols=3)
            return
        daftar = "\n".join(f"- {a['title']} | {', '.join(a['genres'])} | skor {a['score']} | "
                           f"{a['year']} | {a['synopsis'][:200]}" for a in cands)
        prompt = (f"Kamu adalah asisten rekomendasi anime. Preferensi pengguna: genre {genres or 'bebas'}, "
                  f"tahun {yr[0]}-{yr[1]}, skor minimal {min_score}. Catatan: {extra or '-'}.\n"
                  f"Pilih 3 judul TERBAIK hanya dari daftar kandidat berikut, dan beri alasan singkat "
                  f"(1-2 kalimat, bahasa Indonesia) untuk masing-masing:\n{daftar}")
        with st.spinner("AI sedang memilih..."):
            try:
                st.markdown(ask_gemini(prompt))
            except Exception as e:
                st.error(f"Gagal memanggil Gemini: {e}")
        with st.expander("Kandidat yang dikirim ke AI"):
            render_cards(cands[:6], "aic", cols=3)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    if not st.session_state.get("user"):
        login_page()
        return

    with st.sidebar:
        st.image(LOGO_URL, width=110)
        st.markdown("## anies")
        st.caption(f"Halo, **{st.session_state['user']}** 👋")
        page = st.radio("Menu", ["Home", "Explore", "Statistics", "AI Recommendation"],
                        label_visibility="collapsed")
        st.caption("Temukan cerita berikutnya.")
        if st.button("Keluar", use_container_width=True):
            st.session_state["user"] = None
            st.rerun()

    catalog, source = get_catalog()
    st.session_state["source"] = source
    st.sidebar.caption(f"Sumber data: {source}")

    {"Home": page_home, "Explore": page_explore,
     "Statistics": page_stats, "AI Recommendation": page_ai}[page](catalog)


main()
