# Roadmap

### Done

- [x] Custom user model with email login
- [x] Deck and card models with UUID keys
- [x] REST API with ownership enforcement and JWT auth
- [x] OpenAPI / Swagger documentation
- [x] Frontend — auth, deck list/create, card list/create ([#6](https://github.com/jakefred/WayOom-Bot/issues/6))
- [x] Test suite — 166 tests ([#9](https://github.com/jakefred/WayOom-Bot/issues/9))
- [x] CI pipeline — GitHub Actions ([#14](https://github.com/jakefred/WayOom-Bot/issues/14))
- [x] PostgreSQL support ([#5](https://github.com/jakefred/WayOom-Bot/issues/5))

### Done — Anki Parity

Card model expanded for lossless Anki import. See `docs/adding-model-fields.md` for the field-change checklist.

- [x] **Card types** — `basic`, `basic_reversed`, `cloze`
- [x] **Extra notes** — `extra_notes` JSON list for Anki's additional fields
- [x] **Spaced repetition** — `status`, `due_date`, `interval`, `ease_factor`, `review_count`, `lapse_count`
- [x] **Organization** — `flag` (0-7 color flags) and `position` (manual ordering)
- [x] **HTML rendering** — sanitized HTML via DOMPurify for `front`, `back`, and `extra_notes`
- [x] **`.apkg` import** — `POST /api/import/apkg/` + frontend upload UI. Supports `.anki2`, `.anki21`, and `.anki21b` (zstd-compressed) formats. Deterministic UUID v5 dedup, partial failure handling, 50 MB limit. 26 dedicated tests.
- [x] **Media attachments** — `DeckMedia` model stores images and audio from `.apkg` imports. Served via `GET /api/decks/<id>/media/<filename>` with ownership enforcement. Card HTML rewritten at API time to resolve bare filenames to served URLs; `[sound:]` tags converted to `<audio>` elements. 13 dedicated tests.

### Done — Study Mode

- [x] **Flashcard study mode** — progressive reveal: front always visible, tap to show back, then each extra note one at a time. Dot indicators show reveal progress. Keyboard navigation (Space/Enter/arrows). ([#26](https://github.com/jakefred/WayOom-Bot/issues/26))

### Up Next
- [ ] Edit and delete decks and cards from the UI
- [ ] Frontend design review ([#7](https://github.com/jakefred/WayOom-Bot/issues/7))
- [ ] Sidebar navigation ([#17](https://github.com/jakefred/WayOom-Bot/issues/17))
- [ ] Theme support ([#18](https://github.com/jakefred/WayOom-Bot/issues/18))
- [ ] WayOom icon ([#11](https://github.com/jakefred/WayOom-Bot/issues/11))
- [ ] Fix: anonymous users cannot read cards in public decks ([#1](https://github.com/jakefred/WayOom-Bot/issues/1))
- [ ] Documentation pass ([#8](https://github.com/jakefred/WayOom-Bot/issues/8))

### Before Production

- [ ] Rate limiting on auth endpoints ([#3](https://github.com/jakefred/WayOom-Bot/issues/3))
- [ ] Move refresh token to `httpOnly` cookie
- [ ] Password strength indicators ([#16](https://github.com/jakefred/WayOom-Bot/issues/16))
- [ ] Security review ([#10](https://github.com/jakefred/WayOom-Bot/issues/10))
- [ ] CD pipeline ([#19](https://github.com/jakefred/WayOom-Bot/issues/19))
- [ ] Account recovery and deletion ([#13](https://github.com/jakefred/WayOom-Bot/issues/13))

### Long Term

- Two-factor authentication ([#15](https://github.com/jakefred/WayOom-Bot/issues/15))
- Spaced repetition scheduling
- Rich card content (images, markdown, audio)
- Mobile-friendly experience
- Public deck sharing and discovery
