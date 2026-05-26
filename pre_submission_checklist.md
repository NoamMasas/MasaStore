# Pre-submission checklist

רשימה אחרונה לפני ההגשה (8 ביוני). לסמן `[x]` כשמסיימים.

---

## 🧹 1. Comment audit — להוריד את ה-AI נויז

**הכי חשוב.** במהלך הפרויקט עלו הרבה comments גם מסקריפטים שעבדנו עליהם ביחד וגם מקוד שיצרנו. צריך לעבור על *כל* הקבצים ולהוריד הכל שאינו הכרחי. הסיבה: מבחינה ויזואלית זה נראה כמו קוד AI מגונרט, ובהקראת קוד "בני אדם" comments מיותרים הם רעש.

**כלל אצבע (לעבור על כל קובץ עם הכלל הזה):**

| תופעה | להשאיר? |
|---|---|
| Module docstring (`"""..."""` בראש הקובץ) | ✅ כן, אבל קצר ולעניין — מטרת הקובץ ב-2-3 שורות |
| Function docstring | ✅ כן אם הפונקציה לא טריוויאלית, גם אז קצר |
| הערה שמסבירה **למה** משהו חריג / החלטה לא ברורה | ✅ כן |
| הערה שמסבירה **מה** הקוד עושה (= חוזרת עליו במילים) | ❌ למחוק |
| `# --- Section X ---` headers שמחלקים את הקובץ | ❌ למחוק אלא אם הקובץ ארוך מאוד |
| הערות "TODO" / "FIXME" / "XXX" / "HACK" | ❌ למחוק — אם זה TODO ראוי, לפתוח issue |
| הערות שמתחילות ב-"v2:" / "NEW:" / "Note that..." | ❌ למחוק (זמני, או מציע מובן מאליו) |
| Type hints במקום הערות | ✅ להעדיף — `def f(x: int) -> str` עדיף על `# x is int, returns str` |

**קבצים שצריכים אודיט פרטני:**
- [ ] `main.py`
- [ ] `config/config.py`
- [ ] כל הקבצים ב-`controller/`
- [ ] כל הקבצים ב-`service/` (במיוחד `recommendation_service.py` ו-`order_service.py` שיש בהם הרבה הסברים שנוצרו תוך כדי הפיתוח)
- [ ] כל הקבצים ב-`repository/`
- [ ] כל הקבצים ב-`model/`
- [ ] `exceptions/exception.py`
- [ ] `redisClient/redis_client.py`
- [ ] `ml/notebooks/recommender.ipynb` — בעיקר תאי markdown
- [ ] `resources/db-migrations/init.sql` — להשאיר רק comments שמסבירים החלטות סכמה
- [ ] `resources/prompts/chat_system.txt` — להשאיר כמו שהוא (זה prompt לעוזר, לא קוד)
- [ ] כל הקבצים ב-`ui/`

---

## 🧠 2. Model training (v2) + החלפת joblib

- [ ] להריץ את `ml/notebooks/recommender.ipynb` ב-Colab עד הסוף (Run all)
- [ ] לוודא ש-Top-3 accuracy עלתה משמעותית לעומת v1 (היה 24.5%, צפי 55-70%)
- [ ] להוריד את `recommender.joblib` החדש
- [ ] להחליף את `ml/recommender.joblib` בקובץ החדש
- [ ] לעדכן את המטריקות ב-README (סקציית "Reported metrics") עם הערכים האמיתיים שהמודל החדש החזיר
- [ ] לאשר ש-`bundle["version"] == "2.0"` בעת ה-load

---

## 🗄 3. Database migration

`init.sql` עודכן בכמה מקומות (30 פריטים, ISO codes, DROP TABLE הוסר). חייבים volume-wipe כדי שהשינויים ייכנסו:

- [ ] `docker-compose down -v`
- [ ] `docker-compose up -d`
- [ ] לוודא ב-`mysql` ש-`SELECT COUNT(*) FROM item` מחזיר **30**
- [ ] לוודא ש-`SELECT country FROM user WHERE id=1` מחזיר **'IL'** (ולא 'Israel')

---

## 🐛 4. Debug code cleanup

- [ ] לחפש `print(` בקוד שלנו (לא ב-.venv) — להסיר כל מה שאינו ב-cells של ה-notebook או logging מכוון
- [ ] לחפש `breakpoint()` — צריך להיות 0
- [ ] לחפש `import pdb` — צריך להיות 0
- [ ] לוודא שלא נשארו קבצי `_smoke_test.py` או `_validate.py` בתוך `ml/`

---

## 🧪 5. Final test pass

### Backend (Swagger UI — http://localhost:8000/docs)
- [ ] Register משתמש חדש עם country=IL, password=123456 → 201
- [ ] Register עם country=Israel (שם מלא) → 422
- [ ] Register עם password של 5 תווים → 422
- [ ] Login עם yossi_active → token
- [ ] Login עם `deleted_user` (David, is_active=False) → 401
- [ ] `GET /item/` → 30 פריטים
- [ ] `GET /recommendation/` עם Yossi → 30 פריטים מסודרים, top items הם Tech
- [ ] קריאה שנייה ל-`/recommendation/` → cache hit (מהיר)
- [ ] `POST /favorite/` עם פריט חדש → invalidate cache, קריאה שלישית מחשבת מחדש
- [ ] `POST /order/item/` פעמיים עם אותו פריט → quantity מצטבר
- [ ] `POST /chat/` 6 פעמים → 6th נכשל עם 429
- [ ] `POST /chat/reset/` → אחר כך chat עובד שוב

### UI (Streamlit — http://localhost:8501)
- [ ] Login → סקציית auth מוסתרת
- [ ] sort dropdown מציג 6 אופציות (For You ראשון אם logged in)
- [ ] "For You" sort מציג קטגוריה דומיננטית בראש
- [ ] לחיצה על "Add to cart" → toast מציג "X added, Y now in cart"
- [ ] פריט out of stock → "Out of stock" badge, כפתור disabled
- [ ] עמוד Favorites, Orders, Chat נטענים בלי שגיאה

---

## 📄 6. Documentation sanity check

- [ ] `README.md` — לקרוא מתחילתו עד סופו, לוודא שכל פרק תקף
- [ ] לוודא שאין הזכרות ל-"Keras" / "scikeras" בקוד או ב-docs (רק בהיסטוריה ב-README — שם זה בסדר כי זה ה-rationale)
- [ ] לוודא שכל commands ב-README עובדים (`docker-compose up -d`, `uvicorn main:app --reload`, `streamlit run ui/Main.py`)

---

## 📦 7. Git / repo hygiene

- [ ] `.gitignore` מכסה `.venv/`, `__pycache__/`, `.idea/`, `.claude/`, `.env`
- [ ] `git status` לפני commit — לא להעלות `__pycache__`, `.env`, או קבצי IDE
- [ ] `requirements.txt` — לוודא שכל package שמופיע באמת בשימוש בקוד (לא לבזבז גודל install)
- [ ] `git log --oneline` — לוודא שאין commits עם הודעות מטומטמות / WIP
- [ ] לעשות commit אחרון: `chore: final pre-submission cleanup`
- [ ] לעשות push למאסטר

---

## ⏰ 8. ביום ההגשה (8 ביוני)

- [ ] Pull request פתוח / קישור ל-repo מוכן
- [ ] לוודא שה-repo ציבורי
- [ ] בדיקה אחרונה ש-`docker-compose up` + `uvicorn` + `streamlit` עובדים מ-clean clone
