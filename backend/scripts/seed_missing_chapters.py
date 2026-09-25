"""Seed MISSING GSEB Std 10 chapter rows so every subject has its full topic list.

Idempotent — safe to rerun. Only INSERTS chapters that don't exist yet
(matched by subject + number). Never modifies or deletes existing rows,
so all ingested knowledge documents stay attached.

Sources: official GSEB Std 10 Gujarati-medium textbooks (via shalamitra.in
chapter indexes, cross-checked with studentbro.in for ICT).

Usage:  python -m scripts.seed_missing_chapters
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models.chapter import Chapter  # noqa: E402
from app.models.subject import Subject  # noqa: E402

# ---- Gujarati (first language): 26 Sem-1 lessons + 5 Sem-2 lessons + grammar units
GUJARATI = [
    (1, "વૈષ્ણવજન"), (2, "રેસનો ઘોડો"), (3, "શીલવંત સાધુને"), (4, "ભૂલી ગયા પછી"),
    (5, "દીકરી"), (6, "વાઈરલ ઇન્ફેક્શન"), (7, "હું એવો ગુજરાતી"), (8, "છત્રી"),
    (9, "માધવને દીઠો છે ક્યાંય?"), (10, "ડાંગવનો અને..."), (11, "શિકારીને"),
    (12, "ચોપડાની ઈન્દ્રજાળ"), (13, "વતનથી વિદાય થતાં"), (14, "જન્મોત્સવ"),
    (15, "બોલીએ ના કાંઈ"), (16, "ગતિભંગ"), (17, "દિવસો જુદાઈના જાય છે"),
    (18, "ભૂખથી ભૂંડી ભીખ"), (19, "એક બપોરે"), (20, "વિરલ વિભૂતિ"),
    (21, "ચાંદલિયો"), (22, "હિમાલયમાં એક સાહસ"), (23, "લઘુકાવ્યો"),
    (24, "ઘોડીની સ્વામીભક્તિ"), (25, "સમર્પણ"), (26, "રાષ્ટ્રભક્તિની સંજીવની"),
    (27, "બહાદુર બાળકો"), (28, "નદીવિયોગ"), (29, "તારા પગલે"), (30, "મારી બા"),
    (31, "વીરભૂમિ"),
    (32, "વ્યાકરણ: ધ્વનિશ્રેણી, જોડણી, સંધિ, સમાસ"),
    (33, "વ્યાકરણ: સંજ્ઞા, વિશેષણ, ક્રિયા વિશેષણ"),
    (34, "વ્યાકરણ: વાક્યપ્રકાર — કર્તરિ, કર્મણિ, ભાવે, પ્રેરક"),
    (35, "વ્યાકરણ: અલંકાર"), (36, "વ્યાકરણ: છંદ"),
    (37, "લેખનકૌશલ: નિબંધ, અહેવાલ, સંક્ષેપીકરણ"),
]

# ---- Hindi (23 lessons)
HINDI = [
    (1, "प्रभुजी तुम चन्दन हम पानी"), (2, "बूढ़ी काकी"), (3, "सवैये"),
    (4, "एक प्रश्न : चार उत्तर"), (5, "मीरा के पद"), (6, "कालिदास का प्राणीप्रेम"),
    (7, "जन्मभूमि"), (8, "सुधामूर्ति"), (9, "कुत्ते की सिख"), (10, "जीने की कला"),
    (11, "भारतवर्ष हमारा है"), (12, "एक नई शरुआत"), (13, "साधुप्रदेश"),
    (14, "मेरी माँ"), (15, "हे जनशक्ति महान!"), (16, "चोरी"), (17, "कश्मीर"),
    (18, "रचना"), (19, "तोता और इन्द्र"), (20, "अलबम"), (21, "पहेलियाँ-मुकरियाँ"),
    (22, "भीतरी समृद्धि"), (23, "भूख"),
]

# ---- English (14 units)
ENGLISH = [
    (1, "Against the Odds"), (2, "The Human Robot"),
    (3, "An Interview with Arun Krishnamurthy"), (4, "A Wonderful Creation"),
    (5, "Playing with Fire"), (6, "I Love You, Teacher"), (7, "Kach & Devyani"),
    (8, "Our Feathered Friends"), (9, "Tune up O Teens"), (10, "Test of True Love"),
    (11, "My Song"), (12, "Pencil"), (13, "Growing"), (14, "Vanila Twilight"),
]

# ---- Sanskrit (20 lessons + 6 abhyas)
SANSKRIT = [
    (1, "सं वदध्वम्"), (2, "यद्धविष्यो विनश्यति"), (3, "स्वस्थवृत्तं समाचर"),
    (4, "जनार्दनस्य पश्चिमः सन्देशः"), (5, "गुणवन्ती कन्या"), (6, "काष्ठखण्डः"),
    (7, "सुभाषितकुसुमानि"), (8, "साक्षिभूतः मनुष्यः"), (9, "चक्षुष्मान् अन्ध एव"),
    (10, "त्वमेका भवानी"), (11, "यस्य जननं तस्य मरणम्"),
    (12, "कलिकालसर्वज्ञो हेमचन्द्रः"), (13, "गीतामृतम्"), (14, "क इदं दुष्करं कुर्यात्"),
    (15, "जयः पराजयो वा"), (16, "अद्भुतं युद्धम्"), (17, "स्वभाविकं सादृश्यम्"),
    (18, "मुक्तानि मुक्तकानि"), (19, "सत्यं मयूरः"), (20, "तथैव तिष्ठति"),
    (21, "अभ्यास 1: पुनरावर्तन अनે ક્રિયાપદ-પરિચય"),
    (22, "अभ्यास 2: વિશેષણ-પ્રયોગ-પરિચય"),
    (23, "अभ्यास 3: ઉપપદ-વિભક્તિ-પરિચય"),
    (24, "अभ्यास 4: કૃદંત-પરિચય"), (25, "अभ्यास 5: સમાસ-પરિચય"),
    (26, "अभ्यास 6: વિસર્ગસંધિ-પરિચય"),
]

# ---- ICT / Computer Studies (16 chapters)
ICT = [
    (1, "HTML નો પરિચય"), (2, "HTMLમાં Head અને Body વિભાગ"),
    (3, "HTMLમાં છબીઓનું વ્યવસ્થાપન"), (4, "HTMLમાં યાદી અને કોષ્ટકનો ઉપયોગ"),
    (5, "કેલ્સીનો પરિચય"), (6, "કેલ્સીમાં ડેટાનું ઓડિટિંગ અને ફોર્મેટિંગ"),
    (7, "કેલ્સીમાં વિધેય"), (8, "કેલ્સીમાં આલેખની રચના"),
    (9, "સમસ્યા અને સમસ્યાનું નિરાકરણ"), (10, "સી ભાષાનો પરિચય"),
    (11, "સી ભાષામાં ડેટા પ્રકાર, પ્રક્રિયકો અને પદાવલિઓ"),
    (12, "નિવેશ/નિર્ગમ પ્રક્રિયાઓનો ઉપયોગ"), (13, "નિર્ણય માળખાં"),
    (14, "લૂપ નિયંત્રણ માળખાં"), (15, "એરે"), (16, "વિધેય"),
]

# ---- Social Science: keep existing geography 1-9 + 17; add heritage & remaining topics.
# (Existing rows are never touched; these numbers fill the gaps without collision.)
SOCIAL_SCIENCE_MISSING = [
    (10, "ભારતનો વારસો"),
    (11, "સાંસ્કૃતિક વારસો: પરંપરાઓ, હસ્ત અને લલિતકલા"),
    (12, "સાંસ્કૃતિક વારસો: શિલ્પ અને સ્થાપત્ય"),
    (13, "ભારતનો સાહિત્યિક વારસો"),
    (14, "ભારતનો વિજ્ઞાન અને ટેક્નોલૉજીનો વારસો"),
    (15, "ભારતનો સાંસ્કૃતિક વારસાનાં સ્થળો"),
    (16, "આપણા વારસાનું જતન"),
    (18, "આર્થિક ઉદારીકરણ અને વૈશ્વિકીકરણ"),
    (19, "આર્થિક સમસ્યાઓ: ગરીબી અને બેરોજગારી"),
    (20, "ભાવવધારો અને ગ્રાહક જાગૃતિ"),
    (21, "માનવ વિકાસ"),
    (22, "ભારતની સામાજિક સમસ્યાઓ અને પડકારો"),
    (23, "સામાજિક પરિવર્તન"),
    (24, "પ્રકૃતિમાં પોષણ-વ્યવસ્થા"),
    (25, "માર્ગ-સલામતી અને વાહનચાલક"),
]

SUBJECT_CHAPTERS = {
    "Gujarati": GUJARATI,
    "Hindi": HINDI,
    "English": ENGLISH,
    "Sanskrit": SANSKRIT,
    "ICT": ICT,
    "Social Science": SOCIAL_SCIENCE_MISSING,
}


def main() -> None:
    db = SessionLocal()
    try:
        total_added = 0
        for subject_name, chapters in SUBJECT_CHAPTERS.items():
            subject = (
                db.query(Subject)
                .filter(Subject.name_en == subject_name, Subject.standard == 10)
                .first()
            )
            if not subject:
                print(f"!! subject not found: {subject_name} (std 10) — skipped")
                continue
            added = 0
            for number, name_gu in chapters:
                exists = (
                    db.query(Chapter)
                    .filter(Chapter.subject_id == subject.id, Chapter.number == number)
                    .first()
                )
                if exists:
                    continue
                db.add(Chapter(
                    subject_id=subject.id, number=number, name_gu=name_gu,
                    name_en="", description="", is_active=True,
                ))
                added += 1
            db.commit()
            total_added += added
            print(f"{subject_name}: +{added} chapters")
        print(f"done — {total_added} chapters added")
    finally:
        db.close()


if __name__ == "__main__":
    main()
