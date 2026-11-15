import pandas as pd

# 1. Load annotation template
df_tmpl = pd.read_csv('data/annotations/lmp_annotation_template.csv', encoding='utf-8-sig')

# 2. Pilot accepted simplifications and context notes
pilot_updates = {
    "LMP_EN_001": {
        "simplified_text": "Any other subject that must be set by rules, or that may be set by rules.",
        "context_note": "Section 30(2)(m) of Act 18 of 1969: dependent sub-clause under State Government rule-making powers; 'prescribed' defined under Sec 2(1)(e) as rules made under this Act.",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_EN_031": {
        "simplified_text": "A Magistrate may conduct a summary trial for any offence under this Act.",
        "context_note": "Section 21(2) of Act 19 of 1976: summary trial powers of a Magistrate for offences under the Act.",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_EN_061": {
        "simplified_text": "The salaries, allowances, and other conditions of service for the Chairperson and Members must be set by the State Government through rules.",
        "context_note": "Section 20 of Act 4 of 2006: State Government rule-making power for salaries, allowances, and other conditions of service of Chairperson and Members of the State Commission.",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_EN_091": {
        "simplified_text": "(c) the highest maintenance payment that the Tribunal may order under this Act;",
        "context_note": "Section 32(2)(c) of Act 56 of 2007: State Government rule-making authority regarding the maximum maintenance allowance ordered under Section 9(2).",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_EN_121": {
        "simplified_text": "A Special Court may, if it considers it appropriate, hold its proceedings at any place other than its usual location.",
        "context_note": "Section 12 of Act 34 of 2008: discretion of the Special Court to hold proceedings at a place other than its ordinary place of sitting.",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_HI_001": {
        "simplified_text": "परंतु धारा 8 की उपधारा (1) के खंड (क) से (च) तक में बताए गए व्यक्ति उस बागान के अधीक्षक को ज़रूरी जानकारी देंगे ।",
        "context_note": "1969 के अधिनियम 18 की धारा 9 का परंतुक: बागान में जन्म या मृत्यु की दशा में धारा 8(1)(क) से (च) में निर्दिष्ट व्यक्तियों द्वारा बागान अधीक्षक को आवश्यक विशिष्टियां देने का कर्तव्य।",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_HI_031": {
        "simplified_text": "(iii) किसी ऐसी बाध्यता के तहत, जो उत्तराधिकार में उस पर आई है; या",
        "context_note": "1976 के अधिनियम 19 की धारा 2(छ)(iii): बंधित श्रम पद्धति की वैधानिक परिभाषा का उप-खंड जो उत्तराधिकार द्वारा न्यागत पुश्तैनी दायित्व के अनुसरण में श्रम से संबंधित है।",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_HI_061": {
        "simplified_text": "आयोग का कोई भी काम या कार्यवाही सिर्फ़ इस वजह से अमान्य नहीं होगी कि-- (क) आयोग में कोई पद खाली है या उसके गठन में कोई कमी है; या (ख) अध्यक्ष या सदस्य के रूप में किसी व्यक्ति की नियुक्ति में कोई ख़ामी है; या (ग) आयोग की प्रक्रिया में ऐसी कोई गड़बड़ी है, जिससे मामले के गुण-दोष पर कोई असर नहीं पड़ता है।",
        "context_note": "2005 के अधिनियम 4 की धारा 9: आयोग के कार्यों या कार्यवाहियों की विधिमान्यता का संरक्षण ताकि रिक्तियों या प्रक्रियागत अनियमितताओं के आधार पर कार्यवाही अमान्य न हो।",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_HI_091": {
        "simplified_text": "(5) जहां बालक या नातेदार भारत से बाहर रह रहा है, वहां अधिकरण द्वारा समन ऐसे प्राधिकारी के माध्यम से तामील कराए जाएंगे, जिसे केंद्र सरकार राजपत्र में अधिसूचना द्वारा इस काम के लिए तय करे ।",
        "context_note": "2007 के अधिनियम 56 की धारा 6(5): भारत से बाहर रहने वाले बालक या नातेदार को अधिकरण द्वारा केंद्र सरकार के अधिसूचित प्राधिकारी के माध्यम से समन तामील कराने की प्रक्रिया।",
        "simplification_status": "SIMPLIFIED"
    },
    "LMP_HI_121": {
        "simplified_text": "(2) इस अधिनियम में किसी कानून या उसके किसी प्रावधान के संदर्भ का, ऐसे किसी क्षेत्र के मामले में जहां वह कानून या प्रावधान लागू नहीं है, यह अर्थ निकाला जाएगा मानो वह उस क्षेत्र में लागू समकक्ष कानून या उसके संबंधित प्रावधान (यदि कोई हो) का संदर्भ है ।",
        "context_note": "2008 के अधिनियम 34 की धारा 2(2): जिन क्षेत्रों में कोई अधिनियमिति लागू नहीं है, वहां उसके निर्देश को प्रवृत्त तत्स्थानी विधि के निर्देश के रूप में अर्थान्वित करने का नियम।",
        "simplification_status": "SIMPLIFIED"
    }
}

# 3. Load all 15 batch CSVs
batches = []
for b in range(1, 16):
    b_path = f'data/annotations/simplification_batches/batch_{b:02d}.csv'
    b_df = pd.read_csv(b_path, encoding='utf-8-sig', keep_default_na=False)
    batches.append(b_df)
df_batches = pd.concat(batches, ignore_index=True)
batch_dict = df_batches.set_index('pair_id').to_dict('index')

# Build master 300
rows = []
for _, tmpl_row in df_tmpl.iterrows():
    pid = tmpl_row['pair_id']
    lang = tmpl_row['language']
    act = tmpl_row['act_id']
    orig = tmpl_row['original_text']

    if pid in pilot_updates:
        simp = pilot_updates[pid]['simplified_text']
        note = pilot_updates[pid]['context_note']
        status = pilot_updates[pid]['simplification_status']
    elif pid in batch_dict:
        b_info = batch_dict[pid]
        if pid == 'LMP_EN_114':
            simp = "Provided that those children or the relative may join (implead) any other person liable to maintain the parent as a party to the maintenance application."
            note = "Proviso to Section 5(5) of Act 56 of 2007: right of respondents to implead other persons liable to maintain the parent in the maintenance proceeding."
            status = "SIMPLIFIED"
        else:
            simp = b_info['simplified_text']
            note = b_info['context_note']
            status = b_info['simplification_status']
    else:
        raise ValueError(f"Unknown ID: {pid}")

    rows.append({
        'pair_id': pid,
        'language': lang,
        'act_id': act,
        'original_text': orig,
        'simplified_text': simp,
        'context_note': note,
        'simplification_status': status
    })

df_master = pd.DataFrame(rows)
cols = ['pair_id', 'language', 'act_id', 'original_text', 'simplified_text', 'context_note', 'simplification_status']
df_master = df_master[cols]

out_path = 'data/annotations/lmp_master_300.csv'
df_master.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"Successfully consolidated {out_path} with {len(df_master)} rows.")
