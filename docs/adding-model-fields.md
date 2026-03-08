# Adding or removing model fields

A checklist for changing fields on `Deck` or `Card`. Every layer needs to be updated — miss one and you get a runtime error, a test failure, or a silent data loss.

---

## Checklist

### 1. Model — `backend/wayoom_bot/models.py`

- Add or remove the field on the model class.
- For new fields that need validation, add a validator function (see `validate_tag_list` for the pattern) and pass it in `validators=[...]`.
- Update `__str__` and `__repr__` if they reference the field.
- If the field needs a DB index, add it to `class Meta: indexes`.

### 2. Migration — `backend/wayoom_bot/migrations/`

Generate the migration after every model change:

```bash
cd backend
SECRET_KEY="dev" DB_NAME="" python manage.py makemigrations wayoom_bot --name <description>
# e.g. --name add_card_extra_field
#      --name remove_card_name
```

`DB_NAME=""` forces SQLite so you don't need PostgreSQL running locally. The generated file goes to version control — don't edit it by hand.

### 3. Admin — `backend/wayoom_bot/admin.py`

- `CardInline.fields` — list of fields shown when editing cards inline on the Deck page.
- `CardAdmin.list_display` — columns in the Card list view.
- `CardAdmin.search_fields` — fields that the admin search box queries.
- Same pattern applies to `DeckAdmin` for Deck fields.

### 4. Serializer — `backend/wayoom_bot/serializers.py`

- Add or remove the field name from `Meta.fields`.
- If the field is server-controlled (set by the view, not the client), add it to `Meta.read_only_fields`.
- If the field needs custom validation or representation, add a `validate_<field>` method or override the field declaration (see `tags` for the pattern).

### 5. Tests — `backend/wayoom_bot/tests.py`

- **Model tests** (`CardModelTests` / `DeckModelTests`): add tests for default value, max length, and any validators.
- **QuerySet tests**: no changes usually needed unless the field affects filtering.
- **View tests**: update every `Card.objects.create(...)` / `Deck.objects.create(...)` call — Django will raise a `TypeError` or `IntegrityError` if a required field is missing.
- Run the suite before committing:

```bash
cd backend
SECRET_KEY="dev" DB_NAME="" python manage.py test
```

### 6. Frontend API types — `frontend/src/api/decks.ts`

- Add or remove the field from the `Card` or `Deck` interface.
- If the field is writable by the client, add it to the `data` parameter type of the relevant `apiCreate*` or `apiUpdate*` function.

### 7. Frontend UI — `frontend/src/pages/`

Update any page that creates, displays, or edits the model:

- **`DeckDetailPage.tsx`** — card create form and card list display.
- **`DeckListPage.tsx`** — deck create form and deck list display.
- Add state (`useState`), a form field, and update the `apiCreate*` call for new writable fields.
- Remove state and JSX for removed fields.

---

## Order of operations

Do the steps in this order to avoid cascading errors:

1. Model
2. Migration (generate immediately after model change)
3. Admin
4. Serializer
5. Tests (fix existing, add new)
6. Frontend types
7. Frontend UI

Run `python manage.py test` after step 5. Run `npm run build` in `frontend/` after step 7 to catch TypeScript errors before pushing.

---

## Common mistakes

| Symptom | Cause |
|---------|-------|
| `TypeError: Card() got unexpected keyword argument 'name'` | Field removed from model but still in a test `create()` call |
| `admin.E108: list_display refers to 'name'` | Field removed from model but still in `CardAdmin.list_display` |
| `IntegrityError: NOT NULL constraint` | Added a non-nullable field without a `default` and existing rows have no value |
| TypeScript build error on `card.name` | Field removed from `Card` interface but still referenced in a page component |

## Non-nullable fields on existing data

If adding a field without `null=True` and the table already has rows, Django will prompt for a one-time default during `makemigrations`. Provide a sensible value (e.g. `""` for text, `0` for integers). If the field should genuinely be nullable, add `null=True, blank=True` to the field definition.
