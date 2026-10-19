# Playbook: Google Business Profile and a reviews programme

Use for service businesses (travel agency, clinic, agency, trades) that want local trust, map visibility and better AI answers.
Read `client.json` and `profile.md` first. Use the `seo-local` skill for the audit side.

> **Who does what.** The owner does every account action (sign-in, verification, edits, posting, replying) and sends every message to customers. Claude drafts text, checks consistency, and tracks numbers. Claude never logs into the client's accounts and never sends messages.

## 1. NAP consistency (do this first)
NAP = business **N**ame, **A**ddress, **P**hone, identical everywhere.

| Rule | Detail |
|---|---|
| One master version | Write it in `profile.md` exactly: legal/brand name, full address (or service area), main phone in international format, website URL, hours. Arabic version of name/address if the market uses it. |
| Same everywhere | Website footer + contact page + `Organization`/`LocalBusiness` schema, GBP, Bing Places, Apple Business Connect, Facebook/Instagram, directories. |
| Name | The real business name only. No keywords or city names added ("ReserVella Best Hotels Cairo" breaks Google's guidelines). |
| Address | Hide the address and set a service area if customers are not served at the premises. |
| Check | `seo-local` NAP check; list every mismatch with where to fix it. |

## 2. Google Business Profile setup / optimisation
| Item | What to do (owner clicks; Claude drafts text) |
|---|---|
| Eligibility | Needs a real address or service area and in-person contact with customers. Online-only businesses may not qualify; check Google's guidelines first. |
| Verification | Owner verifies via the method Google offers (video, phone, postcard). |
| Primary category | The most specific match (e.g. "Travel agency"). Check what the top local competitors use. |
| Secondary categories | Only ones that truly apply (e.g. "Tour operator" only if the business runs tours). |
| Services | Each real service with a short description (from `profile.md`; no invented services or prices). |
| Description | Up to 750 characters, facts only: what, for whom, where, since when, how to book. No links, no promo phrases. Claude drafts in English (and Arabic if the market uses it). |
| Hours, phone, website | Match NAP. Website link may carry UTM tags (`utm_source=google&utm_medium=organic&utm_campaign=gbp`) so GA4 shows GBP visits. |
| Photos | Real photos: logo, cover, team, office/storefront, real work (e.g. trips with permission). Owned or licensed only; no stock pretending to be the business. Add new ones monthly. |
| Posts | 1–2 per month: offers, new guides, seasonal updates, with a link to the matching page. Claude drafts; owner posts. |
| Q&A | Where Google still shows Q&A for the profile: seed real common questions from `questions.md` with factual answers; check monthly for new public questions. |
| Messaging / booking links | Only if someone answers them quickly. |

## 3. Bing Places and Apple Business Connect
| Platform | Notes |
|---|---|
| Bing Places for Business | Can import from GBP (fastest). Feeds Bing Maps and Copilot answers. Owner signs in and verifies. |
| Apple Business Connect | businessconnect.apple.com. Feeds Apple Maps, Siri, Spotlight. Same NAP, categories, photos, hours. Owner signs in and verifies. |
| Others | Facebook page, relevant local/industry directories. Same NAP everywhere. |

## 4. Reviews programme
### Policy (never break)
- **No incentives:** no discounts, gifts, refunds, prize draws or cash for reviews.
- **No gating:** ask every customer, not only happy ones. No "rate us first, then we send happy people to Google" flows.
- **No fake reviews:** no reviews from the owner, staff, family or paid services; no writing reviews for customers.
- Breaking these can get reviews removed or the profile restricted. Claude will not draft anything that breaks them.

### Timing and channel
| When | Channel | Who sends |
|---|---|---|
| 1–3 days after the service ends (travel: after the guest is home) | The channel the customer already used (WhatsApp or email) | Owner/staff |
| One reminder, 5–7 days later, only if no reply | Same channel | Owner/staff |
| Never more than one reminder | — | — |

Use the GBP "Ask for reviews" short link as `{review_link}`. Personalise with the customer's name and what they bought.

### Request templates
**WhatsApp, English**
> Hi {name}, welcome back! We hope you enjoyed {service/hotel}. If you have a minute, an honest review on Google helps other travellers choose: {review_link}
> Thank you, {staff_name} from {business}

**WhatsApp, Modern Standard Arabic**
> مرحبًا {name}، نتمنى أن تكون قد استمتعت بـ{service/hotel}. إذا كان لديك دقيقة، فإن تقييمك الصادق على Google يساعد المسافرين الآخرين على الاختيار: {review_link}
> شكرًا لك، {staff_name} من {business}

**Email, English**
> Subject: How was {service/hotel}?
>
> Hi {name},
> Thank you for booking {service/hotel} with {business}. We would value your honest opinion: good or bad, it helps us improve and helps other travellers decide.
> Leave a review on Google: {review_link}
> It takes about a minute. Thank you,
> {staff_name}, {business}

**Email, Modern Standard Arabic**
> الموضوع: كيف كانت تجربتك في {service/hotel}؟
>
> مرحبًا {name}،
> شكرًا لحجزك {service/hotel} مع {business}. يهمنا رأيك الصادق، سواء كان إيجابيًا أو سلبيًا، فهو يساعدنا على التحسين ويساعد المسافرين الآخرين على الاختيار.
> اترك تقييمك على Google: {review_link}
> لن يستغرق الأمر أكثر من دقيقة. شكرًا لك،
> {staff_name}، {business}

### Reply templates
Reply to every review within a few days, in the reviewer's language. Use their name, mention something specific, never share booking details or personal data, never argue.

**Positive, English**
> Thank you, {name}! We are glad {specific detail they mentioned} went well. We look forward to planning your next trip.
> {staff_name}, {business}

**Positive, Arabic**
> شكرًا جزيلًا {name}! يسعدنا أن {specific detail} كانت تجربة جيدة. نتطلع إلى تنظيم رحلتك القادمة.
> {staff_name}، {business}

**Negative, English**
> {name}, thank you for telling us, and we are sorry about {issue they raised}. This is not the experience we want for our guests. Please contact {staff_name} on {phone/email} so we can look into it and make it right.
> {staff_name}, {business}

**Negative, Arabic**
> {name}، شكرًا لإخبارنا، ونعتذر عن {issue}. هذه ليست التجربة التي نريدها لعملائنا. نرجو التواصل مع {staff_name} على {phone/email} حتى نراجع الأمر ونجد حلًا مناسبًا.
> {staff_name}، {business}

Fake or policy-breaking review: owner reports it in GBP ("Report review"); reply calmly and briefly if it stays.

## 5. Tracking (monthly)
Add a table to `clients/<domain>/data/reviews-tracking.md`, numbers read by the owner or from the public profile, with the date:

| Month | Platform | Total reviews | New this month | Average rating | Replied % | Requests sent | Notes |
|---|---|---|---|---|---|---|---|
| YYYY-MM | Google | | | | | | |
| YYYY-MM | Facebook / other | | | | | | |

Also check GBP Performance (calls, website clicks, direction requests) and GA4 visits with the GBP UTM tag. Log a line in `log.md` each month.

## 6. Why this matters for AI answers and trust
- AI assistants and Google's AI features answer "is X legit / reliable / good" questions from public signals: review counts, ratings, review text, and consistent business details across sources. A business with no reviews and mismatched NAP gives them nothing to cite.
- Review text that mentions specific services, places and outcomes matches the questions customers ask (`questions.md`).
- Consistent NAP + `Organization` schema + an About/trust page lets search engines and AI connect the website, GBP and social profiles as one entity.
- Track the effect in the AI-visibility round (`ai_visibility.py`): trust questions ("Is {business} legit?") should start mentioning the business.

## Checklist
- [ ] Master NAP in `profile.md`; mismatches listed and fixed by the owner
- [ ] GBP verified; primary + secondary categories; services; description; hours; UTM link
- [ ] Real photos added; posting plan (1–2/month) drafted
- [ ] Q&A seeded where available
- [ ] Bing Places and Apple Business Connect claimed with the same NAP
- [ ] Review request and reply templates approved by the owner (EN + AR)
- [ ] Every customer asked; no incentives, no gating; max one reminder
- [ ] Monthly tracking table filled; `log.md` updated

## Worked example: reservella.net
Not run yet for this client (no GBP/reviews entry in `log.md` as of 2026-10-19). Related trust work already done: an About page with company facts, a "Is ReserVella legit?" section with FAQ schema, and `legalName` in Organization schema (log, 2026-10-17), targeting the AI trust questions. A reviews programme would add the public signals those answers draw on.
