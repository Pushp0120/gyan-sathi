"""Seed database: plans, subjects, chapters, sample knowledge, admin user.

Run:  python -m scripts.seed_database
"""
import io
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
import app.models  # noqa: F401 — register all tables
from app.core.security import hash_password
from app.models.chapter import Chapter
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.subject import Subject
from app.models.subscription import Plan, Subscription
from app.models.user import User
from app.utils.time import utcnow

settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

SUBJECTS = {
    9: [
        ("Mathematics", "ગણિત", "📐", "navy"),
        ("Science", "વિજ્ઞાન", "🔬", "green"),
        ("Social Science", "સામાજિક વિજ્ઞાન", "🌍", "orange"),
        ("Gujarati", "ગુજરાતી", "📖", "navy"),
        ("English", "અંગ્રેજી", "🔤", "blue"),
        ("Hindi", "હિન્દી", "📕", "orange"),
        ("Sanskrit", "સંસ્કૃત", "🙏", "navy"),
        ("ICT", "કમ્પ્યુટર (ICT)", "💻", "blue"),
    ],
    10: [
        ("Mathematics", "ગણિત", "📐", "navy"),
        ("Science", "વિજ્ઞાન", "🔬", "green"),
        ("Social Science", "સામાજિક વિજ્ઞાન", "🌍", "orange"),
        ("Gujarati", "ગુજરાતી", "📖", "navy"),
        ("English", "અંગ્રેજી", "🔤", "blue"),
        ("Hindi", "હિન્દી", "📕", "orange"),
        ("Sanskrit", "સંસ્કૃત", "🙏", "navy"),
        ("ICT", "કમ્પ્યુટર (ICT)", "💻", "blue"),
    ],
}

# Sample chapters (GSEB-aligned, clearly editable demo structure)
CHAPTERS = {
    ("Science", 10): [
        (1, "રાસાયણિક પ્રક્રિયાઓ અને સમીકરણો", "Chemical Reactions and Equations"),
        (2, "એસિડ, બેઝ અને ક્ષાર", "Acids, Bases and Salts"),
        (3, "ધાતુ અને અધાતુ", "Metals and Non-metals"),
        (4, "કાર્બન અને તેનાં સંયોજનો", "Carbon and its Compounds"),
        (10, "પ્રકાશ – પરાવર્તન અને વક્રીભવન", "Light – Reflection and Refraction"),
        (11, "માનવ નેત્ર તથા વર્ણવિક્ષેપણ", "Human Eye and Colourful World"),
        (12, "વિદ્યુત પ્રવાહનાં મૂળભૂત ખ્યાલો", "Electricity"),
        (13, "ચુંબકીય અસરો અને વિદ્યુત પ્રવાહ", "Magnetic Effects of Electric Current"),
    ],
    ("Mathematics", 10): [
        (1, "વાસ્તવિક સંખ્યાઓ", "Real Numbers"),
        (2, "બહુપદી", "Polynomials"),
        (3, "યુગ્મ રેખીય સમીકરણ", "Pair of Linear Equations"),
        (4, "દ્વિઘાત સમીકરણ", "Quadratic Equations"),
        (5, "સમાંતર શ્રેણી", "Arithmetic Progressions"),
        (8, "ત્રિકોણમિતિ", "Introduction to Trigonometry"),
        (9, "ત્રિકોણમિતિનાં ઉપયોગો", "Applications of Trigonometry"),
        (13, "પ્રિષ્ઠક્ષેત્ર અને ઘનફળ", "Surface Areas and Volumes"),
        (14, "સંખ્યાશાસ્ત્ર", "Statistics"),
        (15, "સંભાવના", "Probability"),
    ],
    ("Science", 9): [
        (1, "આપણી આસપાસનો પદાર્થ", "Matter in Our Surroundings"),
        (2, "ક્ષાર છે પદાર્થ શું છે?", "Is Matter Around Us Pure"),
        (8, "ગતિ", "Motion"),
        (9, "બળ અને ગતિના નિયમો", "Force and Laws of Motion"),
        (11, "કાર્ય અને ઊર્જા", "Work and Energy"),
    ],
    ("Mathematics", 9): [
        (1, "સંખ્યા પદ્ધતિ", "Number Systems"),
        (2, "બહુપદી", "Polynomials"),
        (6, "રેખાઓ અને ખૂણા", "Lines and Angles"),
        (8, "ચતુર્ભુજ", "Quadrilaterals"),
        (12, "હેરોનનું સૂત્ર", "Heron's Formula"),
    ],
    ("Social Science", 10): [
        (1, "ભારતના સંસાધનો", "Resources of India"),
        (7, "પર્યટન વ્યવસાય", "Tourism"),
        (8, "ઉદ્યોગો", "Industries"),
        (17, "આર્થિક વિકાસ", "Economic Development"),
    ],
}

# Clearly-marked SAMPLE knowledge content (demo purposes, not copyrighted textbook text)
SAMPLE_KB = {
    ("Science", 10, "પ્રકાશ – પરાવર્તન અને વક્રીભવન"): [
        ("પરાવર્તન (Reflection)", """
પ્રકાશનું પરાવર્તન: જ્યારે પ્રકાશનો કિરણ કોઈ સપાટી પર પડે છે અને તે જ માધ્યમમાં પાછો વળે છે, તેને પ્રકાશનું પરાવર્તન કહેવાય.

પરાવર્તનના નિયમો:
1. આપાત કિરણ, પરાવર્તિત કિરણ અને અભલંબ એક જ સમતલમાં હોય છે.
2. આપાત કોણ = પરાવર્તન કોણ (angle of incidence = angle of reflection).

સમતલ દર્પણ: પ્રતિબિંબ આભાસી (virtual), સીધો (erect) અને વસ્તુ જેટલો જ કદનો બને છે.

ગોળીય દર્પણ: અંતર્મુખ (concave) દર્પણ પ્રકાશને એકત્રિત કરે છે (converge), બહિર્મુખ (convex) દર્પણ પ્રકાશને ફેલાવે છે (diverge).
દર્પણ સૂત્ર: 1/f = 1/v + 1/u, જ્યાં f = ફોકસ અંતર, v = પ્રતિબિંબ અંતર, u = વસ્તુ અંતર.
મોટાપણો m = -v/u = f/(f-u) = (f-v)/f.
"""),
        ("વક્રીભવન (Refraction)", """
વક્રીભવન: પ્રકાશ એક પારદર્શક માધ્યમમાંથી બીજા માધ્યમમાં જાય ત્યારે દિશા બદલે છે, આને પ્રકાશનું વક્રીભવન કહેવાય.

વક્રીભવનના નિયમો:
1. આપાત કિરણ, વક્રીભવિત કિરણ અને અભલંબ એક જ સમતલમાં હોય છે.
2. Snell નો નિયમ: sin i / sin r = અચળ સંખ્યા = n₂₁ (બીજા માધ્યમનો પ્રથમ સાપેક્ષે અપવર્તનાંક).

અપવર્તનાંક (Refractive index): પ્રકાશની ઝડપ કેટલી ઘટે છે તે દર્શાવે છે. પાણીનો અપવર્તનાંક આશરે 1.33 અને કાચનો આશરે 1.5 છે.

લેન્સ સૂત્ર: 1/f = 1/v - 1/u
લેન્સની ક્ષમતા: P = 1/f (મીટરમાં f), એકમ: ડાયોપ્ટર (D).
"""),
        ("પ્રકાશના સંખ્યાત્મક ઉદાહરણો", """
ઉદાહરણ 1: અંતર્મુખ દર્પણની ફોકસ લંબાઈ 10 cm છે. વસ્તુ 30 cm દૂર મૂકી હોય તો પ્રતિબિંબ ક્યાં બને?
આપેલ: f = -10 cm (અંતર્મુખ માટે ઋણ), u = -30 cm
સૂત્ર: 1/f = 1/v + 1/u
મૂલ્યોની સ્થાપના: 1/(-10) = 1/v + 1/(-30)
ગણતરી: 1/v = -1/10 + 1/30 = (-3+1)/30 = -2/30 = -1/15
અંતિમ જવાબ: v = -15 cm, એટલે કે પ્રતિબિંબ દર્પણની સામે 15 cm દૂર એક જ બાજુએ બને છે.

ઉદાહરણ 2: લેન્સની ક્ષમતા +2.0 D છે. ફોકસ લંબાઈ શોધો.
P = 1/f → f = 1/P = 1/2.0 = 0.5 m = +50 cm (ઉત્તલ લેન્સ).
"""),
    ],
    ("Science", 9, "બળ અને ગતિના નિયમો"): [
        ("ન્યુટનના ગતિના નિયમો", """
ન્યુટનનો પ્રથમ નિયમ (જડત્વનો નિયમ): કોઈ પદાર્થ પર સંતુલિત બાહ્ય બળ ન લાગે ત્યાં સુધી તે સ્થિર સ્થિતિમાં હોય તો સ્થિર જ રહેશે, અને ગતિમાં હોય તો સમાન વેગથી સીધી રેખામાં ચાલુ રહેશે.

ન્યુટનનો બીજો નિયમ: પદાર્થના વેગમાન (momentum) નો ફેરફાર લાગુ બળના પ્રમાણમાં થાય છે. F = ma, જ્યાં m = દળ (kg), a = પ્રવેગ (m/s²), F = બળ (ન્યૂટન N).

ન્યુટનનો ત્રીજો નિયમ: દરેક ક્રિયાને સમાન અને વિરુદ્ધ પ્રતિક્રિયા મળે છે.

જડત્વ (Inertia): પદાર્થ પોતાની સ્થિતિ બદલવાનો વિરોધ કરે છે. દળ જેટલું વધુ, જડત્વ એટલું વધુ.
"""),
        ("વેગમાન અને બળના સંખ્યાત્મક ઉદાહરણો", """
ઉદાહરણ 1: 5 kg દળના પદાર્થ પર 20 N બળ લાગે તો પ્રવેગ શોધો.
આપેલ: m = 5 kg, F = 20 N
સૂત્ર: F = ma → a = F/m
ગણતરી: a = 20/5
અંતિમ જવાબ: a = 4 m/s²

ઉદાહરણ 2: 2 kg દળનો પદાર્થ 10 m/s વેગથી ગતિ કરે છે. વેગમાન શોધો.
આપેલ: m = 2 kg, v = 10 m/s
સૂત્ર: p = mv
ગણતરી: p = 2 × 10
અંતિમ જવાબ: p = 20 kg·m/s
"""),
    ],
    ("Mathematics", 10, "ત્રિકોણમિતિ"): [
        ("ત્રિકોણમિતિના મૂળ ગુણોત્તારો", """
ત્રિકોણમિતિ (Trigonometry): સામાન્ય ખૂણાના ત્રિકોણની બાજુઓ અને ખૂણા વચ્ચેનો સંબંધ.

મૂળ ગુણોત્તારો (ખૂણા A માટે):
- sin A = લંબ / કર્ણ
- cos A = પાયો / કર્ણ
- tan A = લંબ / પાયો = sin A / cos A
- cosec A = 1/sin A, sec A = 1/cos A, cot A = 1/tan A

મહત્વની કિંમતો:
sin 0°=0, sin 30°=1/2, sin 45°=1/√2, sin 60°=√3/2, sin 90°=1
cos 0°=1, cos 30°=√3/2, cos 45°=1/√2, cos 60°=1/2, cos 90°=0

મૂળભૂત સરવાળો: sin²A + cos²A = 1; 1 + tan²A = sec²A; 1 + cot²A = cosec²A
"""),
        ("ત્રિકોણમિતિનાં ઉપયોગો – ઊંચાઈ અને અંતર", """
ઊંચાઈ અને અંતરના પ્રશ્નોમાં ત્રિકોણમિતિ વપરાય છે.

મહત્વના ખ્યાલો:
- ઉન્નતિ કોણ (Angle of elevation): નીચેથી ઉપર જોતાં દૃષ્ટિ રેખા અને આડી રેખા વચ્ચેનો ખૂણો.
- અધોગમન કોણ (Angle of depression): ઉપરથી નીચે જોતાં બનતો ખૂણો.

ઉદાહરણ: મિનારાથી 30 m દૂર આવેલા બિંદુએ મિનારાની ટોચનો ઉન્નતિ કોણ 60° હોય, તો મિનારાની ઊંચાઈ શોધો.
આપેલ: પાયો = 30 m, ખૂણો = 60°
સૂત્ર: tan 60° = લંબ/પાયો
ગણતરી: √3 = લંબ/30 → લંબ = 30√3
અંતિમ જવાબ: ઊંચાઈ = 30√3 ≈ 51.96 m
"""),
    ],
    ("Social Science", 10, "આર્થિક વિકાસ"): [
        ("ભારતનો આર્થિક વિકાસ – મૂળ ખ્યાલો", """
આર્થિક વિકાસ (Economic Development): દેશના લોકોની આવક, રોજગારી અને જીવન ધોરણમાં થતો સતત સુધારો.

મુખ્ય ખ્યાલો:
- GDP (સકલ ઘરેલુ ઉત્પાદન): એક વર્ષમાં દેશમાં ઉત્પાદિત બધી અંતિમ વસ્તુઓ અને સેવાઓનું મૂલ્ય.
- પ્રાથમિક ક્ષેત્ર: ખેતી, પશુપાલન, માછીમારી, ખનન.
- ગૌણ ક્ષેત્ર: ઉદ્યોગો, ઉત્પાદન.
- તૃતીય ક્ષેત્ર: સેવાઓ – બેંક, પરિવહન, શિક્ષણ, આરોગ્ય.

માનવ વિકાસ આંક (HDI): આયુષ્ય, શિક્ષણ અને આવકને આધારે દેશોની ગણતરી.
"""),
    ],
}


def seed():
    logger.info("Seeding Gyan Sathi database …")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ---- plans
        free = db.query(Plan).filter(Plan.code == "free").first()
        if not free:
            free = Plan(code="free", name_en="Free", name_gu="મફત",
                        price_inr=0, duration_days=0,
                        upload_limit=settings.free_upload_limit, chat_daily_limit=-1,
                        features=["10 મફત uploads", "અસીમિત પ્રશ્નો*", "AI ક્વિઝ", "અભ્યાસ પ્રગતિ"])
            db.add(free)
        premium = db.query(Plan).filter(Plan.code == "premium").first()
        if not premium:
            premium = Plan(code="premium", name_en="Premium", name_gu="પ્રીમિયમ",
                           price_inr=settings.premium_price_inr,
                           duration_days=settings.premium_duration_days,
                           upload_limit=settings.premium_upload_limit, chat_daily_limit=-1,
                           features=["500 uploads", "પ્રાધાન્યતા AI એક્સેસ", "અદ્યતન ક્વિઝ સુવિધાઓ",
                                     "વિસ્તૃત ચેટ ઇતિહાસ", "Premium બેજ", "ભાવિ સુવિધાઓ"])
            db.add(premium)
        db.commit()

        # ---- subjects & chapters
        subj_cache: dict = {}
        for std, subs in SUBJECTS.items():
            for order, (en, gu, icon, color) in enumerate(subs):
                key = (std, en)
                subj = db.query(Subject).filter(Subject.standard == std,
                                                Subject.name_en == en).first()
                if not subj:
                    subj = Subject(standard=std, name_en=en, name_gu=gu, code=en.lower(),
                                   icon=icon, color=color, sort_order=order)
                    db.add(subj)
                    db.flush()
                subj_cache[key] = subj
        db.commit()

        chap_cache: dict = {}
        for (subj_en, std), chs in CHAPTERS.items():
            subj = subj_cache.get((std, subj_en))
            if not subj:
                continue
            for num, gu, en in chs:
                ch = db.query(Chapter).filter(Chapter.subject_id == subj.id,
                                              Chapter.number == num).first()
                if not ch:
                    ch = Chapter(subject_id=subj.id, number=num, name_en=en, name_gu=gu)
                    db.add(ch)
                    db.flush()
                chap_cache[(std, subj_en, gu)] = ch
        db.commit()

        # ---- sample knowledge documents (clearly marked as demo content)
        for (subj_en, std, chap_gu), sections in SAMPLE_KB.items():
            subj = subj_cache.get((std, subj_en))
            chap = chap_cache.get((std, subj_en, chap_gu))
            if not subj:
                continue
            title = f"[DEMO] ધોરણ {std} {subj_en} – {chap_gu}"
            doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.title == title).first()
            if not doc:
                doc = KnowledgeDocument(title=title, source_type="demo", standard=std,
                                        subject_id=subj.id, chapter_id=chap.id if chap else None,
                                        academic_year="2026-27", language="gu",
                                        file_name="", status="pending",
                                        uploaded_by=None)
                db.add(doc)
                db.flush()

            existing = db.query(KnowledgeChunk).filter(
                KnowledgeChunk.document_id == doc.id).count()
            if existing:
                continue

            rows = []
            idx = 0
            for sec_title, content in sections:
                rows.append(KnowledgeChunk(
                    document_id=doc.id, chapter_id=chap.id if chap else None,
                    chunk_index=idx, content=content.strip(),
                    standard=std, subject_id=subj.id,
                    chapter_number=chap.number if chap else None,
                    chapter_name_gu=chap_gu, subject_name_gu=subj.name_gu,
                    language="gu", page_number=None, section=sec_title.strip()[:200],
                    source="Gyan Sathi demo content (not textbook copy)",
                    academic_year="2026-27", source_type="demo",
                ))
                idx += 1
            db.add_all(rows)
            doc.chunk_count = len(rows)
            doc.status = "completed"
            db.commit()
            logger.info("Seeded KB doc: %s (%d chunks)", title, len(rows))

        # ---- admin + demo users
        for email in settings.admin_email_list:
            admin = db.query(User).filter(User.email == email).first()
            if not admin:
                admin = User(email=email, full_name="Gyan Sathi Admin", role="admin",
                             password_hash=hash_password("Admin@123"),
                             onboarded=True, standard=10)
                db.add(admin)
                logger.info("Admin created: %s / Admin@123 (change immediately)", email)

        demo = db.query(User).filter(User.email == "student@demo.in").first()
        if not demo:
            demo = User(email="student@demo.in", full_name="ડેમો વિદ્યાર્થી",
                        role="student", password_hash=hash_password("Student@123"),
                        onboarded=True, standard=10, medium="gujarati")
            db.add(demo)
            db.flush()
            db.add(Subscription(student_id=demo.id, plan_id=free.id, status="active",
                                started_at=utcnow(), expires_at=None))
            logger.info("Demo student: student@demo.in / Student@123")

        db.commit()
        logger.info("Seed complete ✔")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
