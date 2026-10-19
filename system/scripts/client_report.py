#!/usr/bin/env python3
"""Client-facing monthly SEO report: one self-contained HTML file an agency can send to any client.

Reads whatever data the system already saved for the client and skips a section when its data
is missing (it never invents numbers):
  - snapshots/gsc-week-<end>.json   weekly Search Console snapshots (weekly_report.py)
  - snapshots/index-<date>.json     indexing checks (weekly_report.py); gsc-<date>.json baselines with "index"
  - data/tech-audit-<date>.json     monthly technical check (tech_audit.py)
  - data/ai-visibility-<date>.json  AI answer sampling (ai_visibility.py)
  - log.md                          work completed in the month ("- YYYY-MM-DD · Area · text")
  - todo.md                         next steps and what we need from the client (## Owner / ## Claude / ## Waiting)
Weekly snapshots whose windows overlap are not double counted: the latest week wins and older
overlapping weeks are skipped. Changes are compared with the previous month when data exists,
otherwise the tile says "first month".

Output: clients/<domain>/reports/client-report-<YYYY-MM>.html (inline CSS, no external requests,
A4 print-friendly, phone-friendly, light theme). Accent colour from client.json "brand_color"
(default #0f766e). --lang ar renders the fixed labels in Modern Standard Arabic, right to left;
data text (queries, pages, log lines) stays as found. Adds a line to log.md unless --no-log.

Usage:
    python client_report.py example.com                    # last complete month, English
    python client_report.py example.com --month 2026-10
    python client_report.py example.com --month 2026-10 --lang ar
"""

import argparse
import calendar
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))
from common import CLIENTS_DIR, load_json, normalize_domain  # noqa: E402

DEFAULT_COLOR = "#0f766e"
INDEXED = "Submitted and indexed"

# ------------------------------------------------------------------ labels

T = {
    "en": {
        "title": "Monthly SEO report", "prepared": "Prepared by SEO Claude System", "generated": "Generated",
        "website": "Website", "period": "Reporting period",
        "kpi_clicks": "Clicks from Google", "kpi_impr": "Times shown on Google", "kpi_pos": "Average Google position",
        "kpi_indexed": "Pages in Google's index", "kpi_tech": "Technical problems", "kpi_ai": "AI answers citing you",
        "first": "first month", "first_check": "first check", "first_round": "first round","vs_prev": "vs last month", "vs_start": "since start of month",
        "vs_prev_check": "vs previous check", "vs_prev_round": "vs previous round", "better": "better", "worse": "worse",
        "no_change": "no change", "per_day": "per day",
        "s_search": "Search performance on Google", "s_index": "Indexing", "s_tech": "Technical health",
        "s_ai": "AI search visibility", "s_work": "Work completed this month", "s_next": "Next steps",
        "s_limits": "About this data",
        "covers": "Search Console weeks used: {weeks} ({days} days of data).",
        "prev_covers": "Last month: {days} days of data.",
        "no_prev": "There is no Search Console data for last month in our records, so this month is the starting point.",
        "per_day_note": "The two months cover a different number of days, so changes compare the daily average.",
        "top_queries": "Top searches (by times shown)", "top_pages": "Top pages",
        "query": "Search", "page": "Page", "clicks": "Clicks", "impr": "Shown", "pos": "Position",
        "movers": "Biggest ranking moves", "movers_basis_prev": "Compared with last month.",
        "movers_basis_in": "Compared from the first to the last week of the month.",
        "was": "Was", "now": "Now", "up": "Up", "down": "Down", "no_movers": "No search moved by more than one position.",
        "idx_start": "Start of month", "idx_end": "End of month", "idx_checked": "checked",
        "idx_of": "{n} of {total} pages", "idx_breakdown": "Status of every page in the sitemap at the last check",
        "status": "Status", "pages": "Pages", "idx_one": "Only one check this month: {n} of {total} pages indexed ({date}).",
        "st_indexed": "Indexed (can appear in Google)", "st_discovered": "Found by Google, not crawled yet",
        "st_crawled": "Crawled, not indexed yet", "st_unknown": "Not yet known to Google", "st_other": "Other",
        "tech_date": "Last technical check: {date}, {pages} pages checked.",
        "tech_open": "Problems open", "tech_fixed": "Fixed since the previous check", "tech_new": "New since the previous check",
        "tech_none": "No problems found: every page loads, has its own title, description and one main heading, and links work.",
        "tech_first": "This was the first technical check, so there is nothing to compare with yet.",
        "tech_kinds": "Problems by type", "type": "Type", "count": "Count",
        "crawl": "Can search engines and AI assistants read the site?", "crawler": "Visitor", "result": "Result",
        "ok": "Allowed", "blocked": "Blocked (HTTP {code})", "files": "Site files",
        "speed": "Mobile speed (Google PageSpeed lab test, 0-100)", "score": "Score",
        "speed_none": "No speed test was part of this check.",
        "ai_intro": "We asked AI assistants with web search {n} real customer questions on {date} and checked which websites the answers used.",
        "ai_cited": "Answers linking to your site", "ai_mentioned": "Answers naming your brand",
        "ai_sources": "Websites AI answers relied on most", "site": "Website", "answers": "Answers",
        "ai_comp": "Competitors cited", "ai_agg": "Answers that relied on booking sites such as Booking.com or Trip.com: {pct}%.",
        "ai_lang": "By language", "lang": "Language", "questions": "Questions", "cited": "Cited",
        "ai_prev": "Previous round ({date}): cited in {c} of {n} answers.",
        "work_none": "No work entries were logged for this month.", "date": "Date", "area": "Area",
        "next_us": "What we will do next", "next_you": "What we need from you", "waiting": "Still waiting on",
        "next_none": "No open tasks are recorded.",
        "limit_lag": "Google Search Console data runs about 3 days behind, so the last days of the month may be missing.",
        "limit_small": "When numbers are small, a few searches can swing the percentages a lot. Read the counts, not only the percentages.",
        "limit_pos": "Average position is the average rank when the site was shown; lower is better (1 = top of Google).",
        "limit_ai": "AI visibility is a sample of answers on one day, not a full tracker; answers change from day to day.",
        "limit_index": "Indexing is checked page by page with Google's URL Inspection tool; Google decides when to index a page.",
        "limit_missing": "Not available this month: {what}.",
        "missing_gsc": "Search Console snapshots", "missing_index": "indexing checks", "missing_tech": "technical check",
        "missing_ai": "AI visibility round", "missing_work": "work log", "missing_todo": "task list",
        "lang_en": "English", "lang_ar": "Arabic",
    },
    "ar": {
        "title": "تقرير تحسين محركات البحث الشهري", "prepared": "إعداد: SEO Claude System", "generated": "تاريخ الإعداد",
        "website": "الموقع", "period": "فترة التقرير",
        "kpi_clicks": "النقرات من Google", "kpi_impr": "مرات الظهور في Google", "kpi_pos": "متوسط الترتيب في Google",
        "kpi_indexed": "الصفحات المفهرسة في Google", "kpi_tech": "المشكلات التقنية", "kpi_ai": "إجابات الذكاء الاصطناعي التي تستشهد بموقعكم",
        "first": "الشهر الأول", "first_check": "الفحص الأول", "first_round": "الجولة الأولى","vs_prev": "مقارنة بالشهر الماضي", "vs_start": "منذ بداية الشهر",
        "vs_prev_check": "مقارنة بالفحص السابق", "vs_prev_round": "مقارنة بالجولة السابقة", "better": "أفضل", "worse": "أسوأ",
        "no_change": "دون تغيير", "per_day": "يوميًا",
        "s_search": "الأداء في بحث Google", "s_index": "الفهرسة", "s_tech": "السلامة التقنية",
        "s_ai": "الظهور في بحث الذكاء الاصطناعي", "s_work": "الأعمال المنجزة هذا الشهر", "s_next": "الخطوات التالية",
        "s_limits": "حول هذه البيانات",
        "covers": "أسابيع Search Console المستخدمة: {weeks} ({days} يومًا من البيانات).",
        "prev_covers": "الشهر الماضي: {days} يومًا من البيانات.",
        "no_prev": "لا توجد في سجلاتنا بيانات Search Console للشهر الماضي، لذا يُعد هذا الشهر نقطة البداية.",
        "per_day_note": "يغطي الشهران عددًا مختلفًا من الأيام، لذا تقارن التغيرات المتوسط اليومي.",
        "top_queries": "أهم عمليات البحث (حسب مرات الظهور)", "top_pages": "أهم الصفحات",
        "query": "عبارة البحث", "page": "الصفحة", "clicks": "النقرات", "impr": "الظهور", "pos": "الترتيب",
        "movers": "أكبر التغيرات في الترتيب", "movers_basis_prev": "مقارنة بالشهر الماضي.",
        "movers_basis_in": "مقارنة بين أول أسبوع وآخر أسبوع في الشهر.",
        "was": "كان", "now": "الآن", "up": "صعود", "down": "هبوط", "no_movers": "لم يتغير ترتيب أي عبارة بحث بأكثر من مركز واحد.",
        "idx_start": "بداية الشهر", "idx_end": "نهاية الشهر", "idx_checked": "تاريخ الفحص",
        "idx_of": "{n} من {total} صفحة", "idx_breakdown": "حالة كل صفحة في خريطة الموقع عند آخر فحص",
        "status": "الحالة", "pages": "الصفحات", "idx_one": "فحص واحد فقط هذا الشهر: {n} من {total} صفحة مفهرسة ({date}).",
        "st_indexed": "مفهرسة (يمكن أن تظهر في Google)", "st_discovered": "اكتشفها Google ولم يزحف إليها بعد",
        "st_crawled": "زحف إليها Google ولم يفهرسها بعد", "st_unknown": "لم يتعرف عليها Google بعد", "st_other": "أخرى",
        "tech_date": "آخر فحص تقني: {date}، وشمل {pages} صفحة.",
        "tech_open": "مشكلات قائمة", "tech_fixed": "تم إصلاحها منذ الفحص السابق", "tech_new": "جديدة منذ الفحص السابق",
        "tech_none": "لم نجد أي مشكلة: كل الصفحات تعمل، ولكل صفحة عنوان ووصف خاص بها وعنوان رئيسي واحد، والروابط سليمة.",
        "tech_first": "هذا أول فحص تقني، لذا لا توجد مقارنة بعد.",
        "tech_kinds": "المشكلات حسب النوع", "type": "النوع", "count": "العدد",
        "crawl": "هل تستطيع محركات البحث ومساعدات الذكاء الاصطناعي قراءة الموقع؟", "crawler": "الزائر", "result": "النتيجة",
        "ok": "مسموح", "blocked": "محجوب (HTTP {code})", "files": "ملفات الموقع",
        "speed": "السرعة على الجوال (اختبار Google PageSpeed، من 0 إلى 100)", "score": "النتيجة",
        "speed_none": "لم يتضمن هذا الفحص اختبار سرعة.",
        "ai_intro": "طرحنا {n} سؤالًا حقيقيًا من أسئلة العملاء على مساعدات الذكاء الاصطناعي المزودة بالبحث في الويب بتاريخ {date}، وتحققنا من المواقع التي اعتمدت عليها الإجابات.",
        "ai_cited": "إجابات تضمنت رابطًا لموقعكم", "ai_mentioned": "إجابات ذكرت علامتكم التجارية",
        "ai_sources": "أكثر المواقع التي اعتمدت عليها الإجابات", "site": "الموقع", "answers": "الإجابات",
        "ai_comp": "المنافسون الذين وردت مواقعهم", "ai_agg": "نسبة الإجابات التي اعتمدت على مواقع الحجز مثل Booking.com وTrip.com: {pct}%.",
        "ai_lang": "حسب اللغة", "lang": "اللغة", "questions": "الأسئلة", "cited": "مرات الاستشهاد",
        "ai_prev": "الجولة السابقة ({date}): ورد موقعكم في {c} من {n} إجابة.",
        "work_none": "لم تُسجل أعمال لهذا الشهر.", "date": "التاريخ", "area": "المجال",
        "next_us": "ما سنقوم به لاحقًا", "next_you": "ما نحتاجه منكم", "waiting": "ما زلنا ننتظر",
        "next_none": "لا توجد مهام مفتوحة مسجلة.",
        "limit_lag": "تتأخر بيانات Google Search Console نحو 3 أيام، لذا قد لا تظهر الأيام الأخيرة من الشهر.",
        "limit_small": "عندما تكون الأرقام صغيرة، قد تُحدث عمليات بحث قليلة تقلبات كبيرة في النسب المئوية. انظروا إلى الأعداد لا إلى النسب فقط.",
        "limit_pos": "متوسط الترتيب هو متوسط مركز الموقع عند ظهوره؛ الرقم الأقل أفضل (1 = أعلى نتائج Google).",
        "limit_ai": "قياس الظهور في الذكاء الاصطناعي عينة من الإجابات في يوم واحد وليس تتبعًا شاملًا، والإجابات تتغير من يوم لآخر.",
        "limit_index": "تُفحص الفهرسة صفحة بصفحة بأداة فحص عناوين URL من Google، وGoogle هو من يقرر موعد فهرسة الصفحة.",
        "limit_missing": "غير متوفر هذا الشهر: {what}.",
        "missing_gsc": "لقطات Search Console", "missing_index": "فحوصات الفهرسة", "missing_tech": "الفحص التقني",
        "missing_ai": "جولة قياس الذكاء الاصطناعي", "missing_work": "سجل الأعمال", "missing_todo": "قائمة المهام",
        "lang_en": "الإنجليزية", "lang_ar": "العربية",
    },
}
MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

# ------------------------------------------------------------------ helpers

e = html.escape


def month_bounds(ym: str) -> tuple[dt.date, dt.date]:
    y, m = map(int, ym.split("-"))
    return dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])


def prev_month(ym: str) -> str:
    first, _ = month_bounds(ym)
    return (first - dt.timedelta(days=1)).strftime("%Y-%m")


def file_date(p: Path) -> dt.date | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
    try:
        return dt.date.fromisoformat(m.group(1)) if m else None
    except ValueError:
        return None


def fmt_num(n) -> str:
    if n is None:
        return "–"
    if isinstance(n, float) and not n.is_integer():
        return f"{n:,.1f}"
    return f"{int(n):,}"


def month_label(ym: str, lang: str) -> str:
    first, _ = month_bounds(ym)
    return f"{MONTHS_AR[first.month - 1]} {first.year}" if lang == "ar" else first.strftime("%B %Y")


def hex_color(c) -> str:
    c = str(c or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", c):
        return "#" + c.lstrip("#").lower()
    if re.fullmatch(r"#?[0-9a-fA-F]{3}", c):
        return "#" + "".join(ch * 2 for ch in c.lstrip("#")).lower()
    return DEFAULT_COLOR


def tint(c: str, amount: float) -> str:
    """Mix colour c with white (amount 0..1 = share of white)."""
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(v + (255 - v) * amount):02x}" for v in (r, g, b))


# ------------------------------------------------------------------ Search Console

def parse_window(snap: dict, end: dt.date) -> tuple[dt.date, dt.date]:
    m = re.match(r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", snap.get("window", ""))
    if m:
        return dt.date.fromisoformat(m.group(1)), dt.date.fromisoformat(m.group(2))
    return end - dt.timedelta(days=6), end


def month_weeks(folder: Path, ym: str) -> list[dict]:
    """Weekly snapshots ending inside the month, latest first, overlapping older weeks dropped."""
    first, last = month_bounds(ym)
    cands = []
    for p in (folder / "snapshots").glob("gsc-week-*.json"):
        d = file_date(p)
        if d and first <= d <= last:
            snap = load_json(p)
            if snap:
                s, en = parse_window(snap, d)
                cands.append({"start": s, "end": en, "snap": snap})
    cands.sort(key=lambda w: w["end"], reverse=True)
    chosen = []
    for w in cands:
        if all(w["end"] < c["start"] or w["start"] > c["end"] for c in chosen):
            chosen.append(w)
    return sorted(chosen, key=lambda w: w["start"]), sorted(cands, key=lambda w: w["end"])


def merge_rows(weeks: list[dict], kind: str, keyfn) -> dict:
    out = {}
    for w in weeks:
        for r in w["snap"].get(kind, []):
            k = keyfn(r[{"queries": "query", "pages": "page"}[kind]])
            o = out.setdefault(k, {"clicks": 0, "impressions": 0, "_pw": 0.0})
            o["clicks"] += r.get("clicks", 0)
            o["impressions"] += r.get("impressions", 0)
            o["_pw"] += r.get("position", 0) * r.get("impressions", 0)
    for o in out.values():
        o["position"] = round(o.pop("_pw") / o["impressions"], 1) if o["impressions"] else None
    return out


def gsc_month(folder: Path, ym: str, host: str) -> dict | None:
    weeks, all_weeks = month_weeks(folder, ym)
    if not weeks:
        return None
    clicks = sum((w["snap"].get("totals") or {}).get("clicks", 0) for w in weeks)
    impr = sum((w["snap"].get("totals") or {}).get("impressions", 0) for w in weeks)
    pw = sum((w["snap"].get("totals") or {}).get("position", 0) * (w["snap"].get("totals") or {}).get("impressions", 0) for w in weeks)
    days = sum((w["end"] - w["start"]).days + 1 for w in weeks)

    def page_key(u):
        p = re.sub(r"^https?://[^/]+", "", u) or "/"
        return p

    return {"weeks": weeks, "all_weeks": all_weeks, "days": days, "clicks": clicks, "impressions": impr,
            "position": round(pw / impr, 1) if impr else None,
            "queries": merge_rows(weeks, "queries", lambda q: q.strip()),
            "pages": merge_rows(weeks, "pages", page_key)}


def movers(now_q: dict, old_q: dict, min_impr: int = 2) -> tuple[list, list]:
    rows = []
    for q in set(now_q) & set(old_q):
        a, b = old_q[q], now_q[q]
        if a["impressions"] >= min_impr and b["impressions"] >= min_impr and a["position"] and b["position"]:
            rows.append((q, a["position"], b["position"], b["impressions"]))
    up = sorted([r for r in rows if r[2] <= r[1] - 1], key=lambda r: r[2] - r[1])[:5]
    down = sorted([r for r in rows if r[2] >= r[1] + 1], key=lambda r: r[1] - r[2])[:5]
    return up, down


# ------------------------------------------------------------------ other inputs

def index_snapshots(folder: Path) -> list[tuple[dt.date, dict]]:
    out = {}
    for p in list((folder / "snapshots").glob("index-*.json")) + list((folder / "snapshots").glob("gsc-2*.json")):
        d = file_date(p)
        if not d:
            continue
        idx = load_json(p).get("index")
        if idx and (d not in out or p.name.startswith("index-")):
            out[d] = idx
    return sorted(out.items())


def dated_files(folder: Path, pattern: str) -> list[tuple[dt.date, Path]]:
    return sorted((d, p) for p in folder.glob(pattern) if (d := file_date(p)))


def parse_log(folder: Path, ym: str) -> list[tuple[str, str, str]]:
    path = folder / "log.md"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"-\s*(\d{4}-\d{2}-\d{2})\s*·\s*([^·]+?)\s*·\s*(.+)", line)
        if not m or not m.group(1).startswith(ym):
            continue
        area = m.group(2).strip()
        if area.lower() in ("system",):  # agency tooling, not client work
            continue
        raw = m.group(3).strip()
        if re.match(r"(?i)committed\b", raw):  # version-control hand-off; the work itself has its own line
            continue
        text = clean_text(raw)
        if text and not re.match(r"(?:user to|PR to be|to GitHub)\b", text):
            out.append((m.group(1), area, text))
    return out


PATH_EXT = r"(?:md|json|sql|txt|py|ts|tsx|ps1|yml|yaml|mjs|js|csv|html)"


def clean_text(text: str, limit: int = 260) -> str:
    def code(m):
        s = m.group(1)
        if re.search(r"[/\\]|\." + PATH_EXT + r"\b", s) or s.startswith(("python ", "npm ")):
            return ""
        return s
    text = re.sub(r"`([^`]*)`", code, text)
    # internal developer steps -> plain words
    text = re.sub(r"^Branch [\w./-]+ \([^)]*\)\s*:?\s*", "", text)
    text = re.sub(r"^Committed(?: [0-9a-f]{7,})?(?: (?:\+|and))? pushed(?: branch)?(?: [\w./-]+)?\s*[;:,.]?\s*", "", text)
    text = re.sub(r"(?<![/\w])(?:outreach|data|reports|content|snapshots|system|clients)/[\w./-]*", "", text)
    text = re.sub(r"^PR #\d+(?: \([^)]*\))?(?: merged)?(?:,| and)?(?: (?:and )?live)?(?: \d{1,2}:\d{2} UTC)?\s*[:.;]?\s*",
                  "Live on the site: ", text)
    text = re.sub(r"\s*\((?:committed|not committed)[^)]*\)", "", text)
    text = re.sub(r"\b(?:kept at|saved in|saved to|written to|see)\s*(?=[;:,.)]|$)", "", text)
    text = re.sub(r"(?<![/\w])[\w.-]+(?:/[\w.@<>-]+)+\." + PATH_EXT + r"\b", "", text)   # dir/file.ext
    text = re.sub(r"(?<![/\w.])[\w-]+\.(?:md|json|sql|py|ps1|yml|csv)\b", "", text)      # bare file.ext
    text = re.sub(r"\b(?:Reports?|Graph|Data|data|SQL|Output|Report)\s*:\s*(?=[,.;)]|$)", "", text)
    text = re.sub(r"\(\s*[,;·]*\s*\)", "", text)
    text = re.sub(r"\s*·\s*(?=$|·)", "", text)
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    text = re.sub(r"\(\s*[,;:]\s*", "(", text)
    text = re.sub(r"[:;,]\s*(?=[.;])", "", text)
    text = re.sub(r"\s*\+\s*(?=[:,.;)]|$)", "", text)                 # "saved to a + b" with both paths gone
    text = re.sub(r"\s*·\s*(?=[.,;:])", "", text)
    text = re.sub(r"\.\s*[:;,]", ".", text)
    text = re.sub(r"\s+\b(?:in|at|to|from|on|into)\s*$", "", text)     # dangling preposition after a removed path
    text = re.sub(r"\s+\b(?:in|at|to|from|on|into)\s*(?=[;,)])", "", text)
    text = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ·,;:-")
    text = text[:1].upper() + text[1:]
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:·(") + " …"
    return text


def parse_todo(folder: Path) -> dict | None:
    path = folder / "todo.md"
    if not path.exists():
        return None
    sections, cur = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        h = re.match(r"##\s+(.+)", line)
        if h:
            cur = h.group(1).strip().lower()
            sections.setdefault(cur, [])
            continue
        m = re.match(r"\s*-\s*\[( |x|X)\]\s*(.+)", line)
        if cur and m and m.group(1) == " ":
            t = clean_text(m.group(2), limit=220)
            if t:
                sections[cur].append(t)
    return sections


# ------------------------------------------------------------------ HTML pieces

def change_badge(new, old, t, basis, lower_better=False, per_day=None, whole=False):
    if old is None:
        first_key = {"vs_prev_check": "first_check", "vs_prev_round": "first_round"}.get(basis, "first")
        return f'<span class="chg neutral">{e(t[first_key])}</span>'
    if per_day:  # (days_now, days_prev)
        new_r, old_r = new / per_day[0], old / per_day[1]
    else:
        new_r, old_r = new, old
    diff = new_r - old_r
    if abs(diff) < 1e-9:
        return f'<span class="chg neutral">{e(t["no_change"])} · {e(t[basis])}</span>'
    good = diff < 0 if lower_better else diff > 0
    cls = "good" if good else "bad"
    if lower_better:
        txt = f'{abs(diff):.0f} {t["better"] if good else t["worse"]}' if whole else f'{abs(diff):.1f} {t["better"] if good else t["worse"]}'
    elif old_r:
        txt = f"{diff / old_r * 100:+.0f}%"
    else:
        txt = f"+{fmt_num(new)}"
    if per_day:
        txt += f' {t["per_day"]}'
    arrow = "▲" if diff > 0 else "▼"
    return f'<span class="chg {cls}"><span dir="ltr">{arrow} {e(txt)}</span> · {e(t[basis])}</span>'


def tile(label, value, badge, sub=""):
    return (f'<div class="tile"><div class="tl">{e(label)}</div><div class="tv" dir="ltr">{e(value)}</div>'
            f'{f"<div class=ts>{e(sub)}</div>" if sub else ""}<div>{badge}</div></div>')


def table(headers, rows, num_cols=()):
    h = "".join(f'<th class="{"n" if i in num_cols else ""}">{e(x)}</th>' for i, x in enumerate(headers))
    body = ""
    for r in rows:
        body += "<tr>" + "".join(
            f'<td class="n" dir="ltr">{e(str(c))}</td>' if i in num_cols else f'<td dir="auto">{c if isinstance(c, Raw) else e(str(c))}</td>'
            for i, c in enumerate(r)) + "</tr>"
    return f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>'


class Raw(str):
    """Already-escaped HTML for a table cell."""


def section(title, body):
    return f'<section><h2>{e(title)}</h2>{body}</section>'


def p(text):
    return f"<p>{e(text)}</p>"


CSS = """
:root{--a:%(a)s;--a2:%(a2)s;--a3:%(a3)s;--ink:#1f2933;--mut:#5b6670;--line:#e3e7eb;--bg:#f6f8f9;--good:#15803d;--bad:#b42318}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 %(font)s}
.page{max-width:900px;margin:0 auto;padding:16px}
header{background:var(--a);color:#fff;border-radius:14px;padding:24px 22px;margin-bottom:18px}
header h1{margin:0 0 4px;font-size:26px;line-height:1.25}header .sub{opacity:.92;font-size:16px}
header .meta{margin-top:12px;font-size:13px;opacity:.85;display:flex;flex-wrap:wrap;gap:6px 18px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px}
.tile{background:#fff;border:1px solid var(--line);border-top:4px solid var(--a);border-radius:12px;padding:14px}
.tl{font-size:13px;color:var(--mut)}.tv{font-size:28px;font-weight:700;margin:2px 0;color:var(--ink)}
[dir=rtl] .tv{text-align:right}.ts{font-size:12px;color:var(--mut)}
.chg{display:inline-block;font-size:12px;border-radius:999px;padding:2px 8px;margin-top:6px}
.chg.good{background:#e7f6ec;color:var(--good)}.chg.bad{background:#fdecea;color:var(--bad)}.chg.neutral{background:var(--a3);color:var(--a)}
section{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-bottom:16px}
h2{margin:0 0 10px;font-size:19px;color:var(--a);border-bottom:2px solid var(--a3);padding-bottom:6px}
h3{margin:16px 0 6px;font-size:15px}p{margin:6px 0}.mut{color:var(--mut);font-size:13px}
.tw{overflow-x:auto;margin:6px 0 10px}table{width:100%%;border-collapse:collapse;font-size:14px}
th{text-align:start;background:var(--a3);color:var(--ink);font-weight:600;padding:7px 9px}
td{padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}
th.n,td.n{text-align:end;white-space:nowrap}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.pill{display:inline-block;background:var(--a3);color:var(--a);border-radius:6px;padding:0 6px;font-size:12px;white-space:nowrap}
ul{margin:6px 0;padding-inline-start:20px}li{margin:4px 0}
.ok{color:var(--good);font-weight:600}.no{color:var(--bad);font-weight:600}
.stat{display:flex;gap:12px;flex-wrap:wrap;margin:8px 0}.stat div{background:var(--a2);border-radius:10px;padding:10px 14px;min-width:150px}
.stat b{display:block;font-size:22px}
bdi{unicode-bidi:isolate;white-space:nowrap}
footer{text-align:center;color:var(--mut);font-size:12px;padding:8px 0 24px}
@media (max-width:640px){.tiles{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}header h1{font-size:22px}.tv{font-size:23px}section{padding:14px}}
@media print{@page{size:A4;margin:12mm}body{background:#fff;font-size:12px}.page{max-width:none;padding:0}
header,.tile,.chg,th,.pill,.stat div{-webkit-print-color-adjust:exact;print-color-adjust:exact}
section,.tile,tr{break-inside:avoid}section{border-color:#ccc}.tiles{grid-template-columns:repeat(3,1fr)}h2{break-after:avoid}}
"""


# ------------------------------------------------------------------ build

def build(domain: str, ym: str, lang: str) -> tuple[str, list[str], list[str]]:
    t = T[lang]
    folder = CLIENTS_DIR / domain
    c = load_json(folder / "client.json")
    if not c:
        sys.exit(f"No client.json in {folder}")
    name = c.get("business_name") or domain
    host = normalize_domain(c.get("canonical_host") or domain)
    color = hex_color(c.get("brand_color"))
    first, last = month_bounds(ym)
    pm = prev_month(ym)
    rendered, missing = [], []

    # ---------- Search Console
    g, gp = gsc_month(folder, ym, host), gsc_month(folder, pm, host)
    per_day = (g["days"], gp["days"]) if g and gp and g["days"] != gp["days"] else None

    # ---------- Indexing
    idx = index_snapshots(folder)
    idx_in = [(d, i) for d, i in idx if first <= d <= last]
    idx_before = [(d, i) for d, i in idx if d < first]
    idx_end = idx_in[-1] if idx_in else None
    idx_start = idx_before[-1] if idx_before else (idx_in[0] if len(idx_in) > 1 else None)

    def n_indexed(i):
        return sum(1 for s in i.values() if str(s).startswith(INDEXED))

    # ---------- Tech
    techs = dated_files(folder / "data", "tech-audit-*.json")
    tech_in = [(d, pth) for d, pth in techs if first <= d <= last]
    tech = load_json(tech_in[-1][1]) if tech_in else None
    tech_prev = None
    if tech_in:
        earlier = [pth for d, pth in techs if d < tech_in[-1][0]]
        tech_prev = load_json(earlier[-1]) if earlier else None

    # ---------- AI
    ais = dated_files(folder / "data", "ai-visibility-*.json")
    ai_in = [(d, pth) for d, pth in ais if first <= d <= last]
    ai = load_json(ai_in[-1][1]) if ai_in else None
    ai_prev = None
    if ai_in:
        earlier = [pth for d, pth in ais if d < ai_in[-1][0]]
        ai_prev = load_json(earlier[-1]) if earlier else None

    work = parse_log(folder, ym)
    todo = parse_todo(folder)

    # ---------- KPI tiles
    tiles = []
    if g:
        tiles.append(tile(t["kpi_clicks"], fmt_num(g["clicks"]),
                          change_badge(g["clicks"], gp["clicks"] if gp else None, t, "vs_prev", per_day=per_day)))
        tiles.append(tile(t["kpi_impr"], fmt_num(g["impressions"]),
                          change_badge(g["impressions"], gp["impressions"] if gp else None, t, "vs_prev", per_day=per_day)))
        if g["position"] is not None:
            tiles.append(tile(t["kpi_pos"], f'{g["position"]:.1f}',
                              change_badge(g["position"], gp["position"] if gp and gp["position"] is not None else None,
                                           t, "vs_prev", lower_better=True)))
    if idx_end:
        n_end, tot_end = n_indexed(idx_end[1]), len(idx_end[1])
        tiles.append(tile(t["kpi_indexed"], f"{n_end}", change_badge(n_end, n_indexed(idx_start[1]) if idx_start else None, t, "vs_start"),
                          sub=t["idx_of"].format(n=n_end, total=tot_end)))
    if tech:
        badge = change_badge(len(tech.get("issues", [])), len(tech_prev.get("issues", [])) if tech_prev else None,
                             t, "vs_prev_check", lower_better=True, whole=True)
        tiles.append(tile(t["kpi_tech"], fmt_num(len(tech.get("issues", []))), badge))
    if ai and ai.get("score"):
        s = ai["score"]
        sp = (ai_prev or {}).get("score")
        tiles.append(tile(t["kpi_ai"], f'{s.get("client_cited", 0)} / {s.get("questions", 0)}',
                          change_badge(s.get("client_cited", 0), sp.get("client_cited", 0) if sp else None, t, "vs_prev_round")))

    body = []

    # ---------- Search performance
    if g:
        rendered.append("Search performance")
        weeks = ", ".join(f'<bdi dir="ltr">{w["start"]} → {w["end"]}</bdi>' for w in g["weeks"])
        parts = ["<p>" + e(t["covers"]).format(weeks=weeks, days=g["days"]) + "</p>"]
        parts.append(p(t["prev_covers"].format(days=gp["days"])) if gp else p(t["no_prev"]))
        if per_day:
            parts.append(f'<p class="mut">{e(t["per_day_note"])}</p>')
        topq = sorted(g["queries"].items(), key=lambda kv: (-kv[1]["impressions"], -kv[1]["clicks"]))[:10]
        topp = sorted(g["pages"].items(), key=lambda kv: (-kv[1]["clicks"], -kv[1]["impressions"]))[:10]
        if topq:
            parts.append(f'<h3>{e(t["top_queries"])}</h3>' + table(
                [t["query"], t["clicks"], t["impr"], t["pos"]],
                [(q, v["clicks"], v["impressions"], f'{v["position"]:.1f}' if v["position"] else "–") for q, v in topq], (1, 2, 3)))
        if topp:
            parts.append(f'<h3>{e(t["top_pages"])}</h3>' + table(
                [t["page"], t["clicks"], t["impr"], t["pos"]],
                [(pg, v["clicks"], v["impressions"], f'{v["position"]:.1f}' if v["position"] else "–") for pg, v in topp], (1, 2, 3)))
        # movers
        if gp:
            up, down = movers(g["queries"], gp["queries"])
            basis = t["movers_basis_prev"]
        elif len(g["all_weeks"]) >= 2:
            a, b = g["all_weeks"][0], g["all_weeks"][-1]
            up, down = movers(merge_rows([b], "queries", str.strip), merge_rows([a], "queries", str.strip))
            basis = t["movers_basis_in"]
        else:
            up = down = None
        if up is not None:
            parts.append(f'<h3>{e(t["movers"])}</h3><p class="mut">{e(basis)}</p>')
            if up or down:
                rows = [(Raw(f'<span class="ok">▲ {e(t["up"])}</span>'), q, f"{a:.1f}", f"{b:.1f}", im) for q, a, b, im in up]
                rows += [(Raw(f'<span class="no">▼ {e(t["down"])}</span>'), q, f"{a:.1f}", f"{b:.1f}", im) for q, a, b, im in down]
                parts.append(table(["", t["query"], t["was"], t["now"], t["impr"]], rows, (2, 3, 4)))
            else:
                parts.append(p(t["no_movers"]))
        body.append(section(t["s_search"], "".join(parts)))
    else:
        missing.append("missing_gsc")

    # ---------- Indexing
    if idx_end:
        rendered.append("Indexing")
        d_end, i_end = idx_end
        parts = []
        if idx_start:
            d0, i0 = idx_start
            parts.append('<div class="stat">'
                         f'<div>{e(t["idx_start"])}<b dir="ltr">{n_indexed(i0)} / {len(i0)}</b><span class="mut">{e(t["idx_checked"])} {d0}</span></div>'
                         f'<div>{e(t["idx_end"])}<b dir="ltr">{n_indexed(i_end)} / {len(i_end)}</b><span class="mut">{e(t["idx_checked"])} {d_end}</span></div></div>')
        else:
            parts.append(p(t["idx_one"].format(n=n_indexed(i_end), total=len(i_end), date=d_end)))
        buckets = {"st_indexed": 0, "st_discovered": 0, "st_crawled": 0, "st_unknown": 0, "st_other": 0}
        for s in i_end.values():
            s = str(s)
            k = ("st_indexed" if s.startswith(INDEXED) else "st_discovered" if s.startswith("Discovered") else
                 "st_crawled" if s.startswith("Crawled") else "st_unknown" if "unknown" in s.lower() else "st_other")
            buckets[k] += 1
        parts.append(f'<h3>{e(t["idx_breakdown"])}</h3>' + table(
            [t["status"], t["pages"]], [(t[k], v) for k, v in buckets.items() if v], (1,)))
        body.append(section(t["s_index"], "".join(parts)))
    else:
        missing.append("missing_index")

    # ---------- Technical health
    if tech:
        rendered.append("Technical health")
        issues = tech.get("issues", [])
        parts = [p(t["tech_date"].format(date=tech.get("date", tech_in[-1][0]), pages=tech.get("pages", "?")))]
        stat = f'<div class="stat"><div>{e(t["tech_open"])}<b>{len(issues)}</b></div>'
        if tech_prev is not None:
            pk = {i["key"] for i in tech_prev.get("issues", [])}
            nk = {i["key"] for i in issues}
            stat += f'<div>{e(t["tech_fixed"])}<b>{len(pk - nk)}</b></div><div>{e(t["tech_new"])}<b>{len(nk - pk)}</b></div>'
        parts.append(stat + "</div>")
        if tech_prev is None:
            parts.append(f'<p class="mut">{e(t["tech_first"])}</p>')
        if not issues:
            parts.append(p(t["tech_none"]))
        else:
            kinds = {}
            for i in issues:
                kinds[i["kind"].split("-")[0]] = kinds.get(i["kind"].split("-")[0], 0) + 1
            parts.append(f'<h3>{e(t["tech_kinds"])}</h3>' + table([t["type"], t["count"]], sorted(kinds.items(), key=lambda kv: -kv[1]), (1,)))
        access = {**(tech.get("bots") or {}), **(tech.get("site_checks") or {})}
        if access:
            def res(code):
                return Raw(f'<span class="ok">✓ {e(t["ok"])}</span>' if code == 200 else f'<span class="no">✗ {e(t["blocked"].format(code=code))}</span>')
            parts.append(f'<h3>{e(t["crawl"])}</h3>' + table([t["crawler"], t["result"]], [(k, res(v)) for k, v in access.items()]))
        speed = tech.get("speed") or {}
        if speed:
            parts.append(f'<h3>{e(t["speed"])}</h3>' + table(
                [t["page"], t["score"], "LCP", "CLS"],
                [(pg, s.get("score", "–"), s.get("lcp", "–"), s.get("cls", "–")) for pg, s in speed.items()], (1, 2, 3)))
        else:
            parts.append(f'<p class="mut">{e(t["speed_none"])}</p>')
        body.append(section(t["s_tech"], "".join(parts)))
    else:
        missing.append("missing_tech")

    # ---------- AI visibility
    if ai and ai.get("score"):
        rendered.append("AI search visibility")
        s = ai["score"]
        parts = [p(t["ai_intro"].format(n=s.get("questions", 0), date=ai.get("date", ai_in[-1][0])))]
        parts.append(f'<div class="stat"><div>{e(t["ai_cited"])}<b dir="ltr">{s.get("client_cited", 0)} / {s.get("questions", 0)}</b></div>'
                     f'<div>{e(t["ai_mentioned"])}<b dir="ltr">{s.get("client_mentioned", 0)} / {s.get("questions", 0)}</b></div></div>')
        if ai_prev and ai_prev.get("score"):
            sp = ai_prev["score"]
            parts.append(p(t["ai_prev"].format(date=ai_prev.get("date", "?"), c=sp.get("client_cited", 0), n=sp.get("questions", 0))))
        if s.get("aggregator_share_pct") is not None:
            parts.append(p(t["ai_agg"].format(pct=s["aggregator_share_pct"])))
        bl = s.get("by_lang") or {}
        if bl:
            parts.append(f'<h3>{e(t["ai_lang"])}</h3>' + table(
                [t["lang"], t["questions"], t["cited"]],
                [(t.get(f"lang_{k}", k), v.get("questions", 0), v.get("cited", 0)) for k, v in bl.items()], (1, 2)))
        top = s.get("top_domains") or []
        if top:
            parts.append(f'<h3>{e(t["ai_sources"])}</h3>' + table([t["site"], t["answers"]], [(d, n) for d, n in top[:10]], (1,)))
        comp = s.get("competitors") or {}
        if comp:
            parts.append(p(t["ai_comp"] + ": " + ", ".join(f"{k} ({v})" for k, v in comp.items())))
        body.append(section(t["s_ai"], "".join(parts)))
    else:
        missing.append("missing_ai")

    # ---------- Work completed
    if (folder / "log.md").exists():
        rendered.append("Work completed")
        if work:
            rows = [(d, Raw(f'<span class="pill">{e(a)}</span>'), txt) for d, a, txt in work]
            body.append(section(t["s_work"], table([t["date"], t["area"], ""], rows)))
        else:
            body.append(section(t["s_work"], p(t["work_none"])))
    else:
        missing.append("missing_work")

    # ---------- Next steps
    if todo is not None:
        rendered.append("Next steps")
        us = todo.get("claude", []) + todo.get("agency", []) + todo.get("us", [])
        you = todo.get("owner", []) + todo.get("client", [])
        wait = todo.get("waiting", [])

        def ul(items):
            return "<ul>" + "".join(f'<li dir="auto">{e(i)}</li>' for i in items) + "</ul>"
        cols = []
        if us:
            cols.append(f'<div><h3>{e(t["next_us"])}</h3>{ul(us)}</div>')
        if you or wait:
            cols.append(f'<div><h3>{e(t["next_you"])}</h3>{ul(you) if you else ""}'
                        + (f'<p class="mut">{e(t["waiting"])}:</p>' + ul(wait) if wait else "") + '</div>')
        body.append(section(t["s_next"], f'<div class="two">{"".join(cols)}</div>' if cols else p(t["next_none"])))
    else:
        missing.append("missing_todo")

    # ---------- Data limits
    limits = [t["limit_lag"], t["limit_small"]]
    if g:
        limits.append(t["limit_pos"])
    if idx_end:
        limits.append(t["limit_index"])
    if ai:
        limits.append(t["limit_ai"])
    if missing:
        limits.append(t["limit_missing"].format(what=", ".join(t[m] for m in missing)))
    body.append(section(t["s_limits"], "<ul>" + "".join(f"<li>{e(x)}</li>" for x in limits) + "</ul>"))

    font = ("Tahoma, 'Segoe UI', 'Noto Naskh Arabic', Arial, sans-serif" if lang == "ar"
            else "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif")
    css = CSS % {"a": color, "a2": tint(color, 0.9), "a3": tint(color, 0.85), "font": font}
    mlabel = month_label(ym, lang)
    today = dt.date.today().isoformat()
    doc = f"""<!doctype html>
<html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(name)} · {e(t['title'])} · {e(mlabel)}</title>
<style>{css}</style>
</head>
<body>
<div class="page">
<header>
<h1>{e(name)}</h1>
<div class="sub">{e(t['title'])} · {e(mlabel)}</div>
<div class="meta"><span>{e(t['website'])}: <bdi dir="ltr">{e(host)}</bdi></span><span>{e(t['period'])}: <bdi dir="ltr">{first} → {last}</bdi></span>
<span>{e(t['prepared'])}</span><span>{e(t['generated'])}: <bdi dir="ltr">{today}</bdi></span></div>
</header>
{f'<div class="tiles">{"".join(tiles)}</div>' if tiles else ''}
{''.join(body)}
<footer>{e(t['prepared'])} · <bdi dir="ltr">{e(host)}</bdi> · <bdi dir="ltr">{today}</bdi></footer>
</div>
</body>
</html>
"""
    return doc, rendered, [T["en"][m] for m in missing]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client")
    ap.add_argument("--month", help="YYYY-MM (default: last complete month)")
    ap.add_argument("--lang", choices=["en", "ar"], default="en")
    ap.add_argument("--no-log", action="store_true", help="do not add a line to log.md")
    a = ap.parse_args()

    domain = normalize_domain(a.client)
    folder = CLIENTS_DIR / domain
    if not folder.exists():
        sys.exit(f"No client folder: {folder}")
    ym = a.month or (dt.date.today().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", ym):
        sys.exit("--month must look like 2026-10")

    doc, rendered, missing = build(domain, ym, a.lang)
    (folder / "reports").mkdir(exist_ok=True)
    suffix = "" if a.lang == "en" else f"-{a.lang}"
    out = folder / "reports" / f"client-report-{ym}{suffix}.html"
    out.write_text(doc, encoding="utf-8")

    if not a.no_log and (folder / "log.md").exists():
        lines = (folder / "log.md").read_text(encoding="utf-8").splitlines()
        i = next((n for n, l in enumerate(lines) if l.startswith("- ")), len(lines))
        lines.insert(i, f"- {dt.date.today()} · Reporting · Client monthly report {ym} ({a.lang}): "
                        f"{len(rendered)} sections · `reports/{out.name}`")
        (folder / "log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"report": str(out), "month": ym, "lang": a.lang, "sections": rendered, "missing": missing},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
