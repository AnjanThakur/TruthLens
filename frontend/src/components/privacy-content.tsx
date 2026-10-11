'use client';
import Link from 'next/link';
import { usePreferences } from './preferences';
const copy = {
  en: {
    title: 'Privacy at TruthLens',
    intro: 'You control whether a report is saved. Verification is available without an account.',
    sections: [
      [
        'Content sent for verification',
        'Text, selected files and article URLs go to Person 1’s verification backend and its configured extraction, search and AI providers. Confirm its provider list and processing/retention policy before public launch. Submit only information you are permitted to share.',
      ],
      [
        'Explicit, private saving',
        'Nothing is automatically saved in this website’s database or browser storage. Sign in and explicitly choose to store a report. The snapshot includes submitted text, claims, verdicts, evidence and explanations. Media files are not stored by this website. Owner-only database rules protect history. Reports are not published or reused for aggregation; synthetic reports cannot be saved.',
      ],
      [
        'Retention and deletion',
        'Choose 7, 30 or 90 days when saving. Expired reports are hidden immediately and an hourly database task permanently deletes them. You can delete them sooner in private history. Infrastructure backups and provider logs may have separate retention policies; confirm with the deployment owner.',
      ],
      [
        'Cookies and logs',
        'Email sign-in uses authentication and PKCE cookies. Unsaved results and reading preferences stay in transient memory. This application adds no analytics trackers and does not log complete messages or media. Hosting and backend operators must also avoid sensitive payload logging.',
      ],
      [
        'Sharing and WhatsApp',
        'Copying a result does not automatically publish it. WhatsApp processes only content you choose to send to the bot. Processing data is temporary and is not automatically added to website history. TruthLens cannot read private chats or discover forwarding recipients.',
      ],
    ],
  },
  hi: {
    title: 'ट्रुथलेंस में गोपनीयता',
    intro: 'रिपोर्ट रखना आपकी पसंद है। बिना खाते के जाँच कर सकते हैं।',
    sections: [
      [
        'जाँच के लिए भेजी गई जानकारी',
        'पाठ, चुनी हुई फ़ाइलें और लेख लिंक Person 1 की जाँच सेवा और उसके पाठ निकालने, खोज तथा AI प्रदाताओं को भेजे जाते हैं। सार्वजनिक शुरुआत से पहले प्रदाताओं और जानकारी रखने की नीति की पुष्टि करें। केवल साझा करने की अनुमति वाली जानकारी दें।',
      ],
      [
        'आपकी सहमति से निजी रूप में सहेजना',
        'वेबसाइट के डेटाबेस या ब्राउज़र में कुछ भी अपने आप नहीं रखा जाता। साइन इन करके स्पष्ट रूप से रिपोर्ट सहेजें। इसमें मूल पाठ, दावे, निर्णय, प्रमाण और व्याख्या शामिल हैं। मीडिया फ़ाइलें वेबसाइट नहीं रखती। डेटाबेस नियम केवल मालिक को पहुँच देते हैं। रिपोर्ट प्रकाशित नहीं होती या सामूहिक विश्लेषण में उपयोग नहीं होती। काल्पनिक रिपोर्ट सहेजी नहीं जा सकती।',
      ],
      [
        'अवधि और हटाना',
        'सहेजते समय 7, 30 या 90 दिन चुनें। अवधि समाप्त होते ही रिपोर्ट छिप जाती है और हर घंटे का कार्य उसे स्थायी रूप से हटाता है। निजी इतिहास से पहले भी हटा सकते हैं। बैकअप और प्रदाता लॉग की अवधि अलग हो सकती है; तैनाती के मालिक से पुष्टि करें।',
      ],
      [
        'कुकी और लॉग',
        'ईमेल साइन-इन में प्रमाणीकरण और PKCE कुकी उपयोग होती हैं। बिना सहेजी रिपोर्ट और पठन विकल्प अस्थायी मेमोरी में रहते हैं। ऐप में एनालिटिक्स ट्रैकर नहीं हैं और पूरे संदेश या मीडिया लॉग नहीं होते। होस्ट और बैकएंड को भी संवेदनशील जानकारी लॉग करने से बचना चाहिए।',
      ],
      [
        'साझा करना और व्हाट्सऐप',
        'सार कॉपी करने से रिपोर्ट अपने आप प्रकाशित नहीं होती। व्हाट्सऐप केवल बॉट को भेजी गई सामग्री की जाँच करता है। अस्थायी सामग्री वेबसाइट के इतिहास में अपने आप नहीं जुड़ती। ट्रुथलेंस निजी चैट नहीं पढ़ सकता।',
      ],
    ],
  },
  mr: {
    title: 'ट्रुथलेन्समधील गोपनीयता',
    intro: 'अहवाल जतन करायचा का ते तुम्ही ठरवता. खात्याशिवाय तपासणी करता येते.',
    sections: [
      [
        'तपासणीसाठी पाठवलेली माहिती',
        'मजकूर, निवडलेल्या फाइल आणि लेखांच्या लिंक Person 1 च्या तपासणी सेवेकडे व तिच्या मजकूर काढणे, शोध आणि AI प्रदात्यांकडे पाठवल्या जातात. सार्वजनिक सुरुवातीपूर्वी प्रदाते आणि माहिती ठेवण्याचे धोरण निश्चित करा. शेअर करण्याची परवानगी असलेलीच माहिती द्या.',
      ],
      [
        'स्पष्ट संमतीने खाजगी जतन',
        'वेबसाइटच्या डेटाबेस किंवा ब्राउझरमध्ये काहीही आपोआप ठेवले जात नाही. साइन इन करून अहवाल जतन करण्याची स्पष्ट निवड करा. त्यात मूळ मजकूर, दावे, निष्कर्ष, पुरावे आणि स्पष्टीकरण असते. मीडिया फाइल वेबसाइट साठवत नाही. डेटाबेसचे नियम फक्त मालकाला प्रवेश देतात. अहवाल प्रकाशित होत नाहीत किंवा एकत्रित विश्लेषणासाठी वापरले जात नाहीत. काल्पनिक अहवाल जतन करता येत नाहीत.',
      ],
      [
        'कालावधी आणि हटवणे',
        'जतन करताना 7, 30 किंवा 90 दिवस निवडा. मुदत संपल्यावर अहवाल लगेच लपवला जातो आणि दर तासाचा कार्यक्रम तो कायमचा हटवतो. खाजगी इतिहासातून आधीही हटवता येतो. बॅकअप आणि प्रदाता लॉगचा कालावधी वेगळा असू शकतो; तैनातीच्या मालकाशी खात्री करा.',
      ],
      [
        'कुकी आणि लॉग',
        'ईमेल साइन-इनमध्ये प्रमाणीकरण आणि PKCE कुकी वापरल्या जातात. जतन न केलेले अहवाल आणि वाचन पर्याय तात्पुरत्या मेमरीत राहतात. अॅपमध्ये विश्लेषण ट्रॅकर नाहीत आणि पूर्ण संदेश किंवा मीडिया लॉग होत नाहीत. होस्ट आणि बॅकएंडनेही संवेदनशील माहिती लॉग करू नये.',
      ],
      [
        'शेअर करणे आणि व्हॉट्सअॅप',
        'सारांश कॉपी केल्याने अहवाल आपोआप प्रकाशित होत नाही. व्हॉट्सअॅप फक्त बॉटला पाठवलेली माहिती तपासते. तात्पुरती माहिती वेबसाइटच्या इतिहासात आपोआप जतन होत नाही. ट्रुथलेन्स खाजगी चॅट वाचू शकत नाही.',
      ],
    ],
  },
};
export function PrivacyContent() {
  const { language, t } = usePreferences();
  const content = copy[language];
  return (
    <main id="main" className="page-container prose">
      <div className="eyebrow">{t.privacy}</div>
      <h1>{content.title}</h1>
      <p>{content.intro}</p>
      {content.sections.map(([heading, body]) => (
        <section key={heading}>
          <h2>{heading}</h2>
          <p>{body}</p>
        </section>
      ))}
      <p>
        <Link href="/history">{t.history}</Link>
      </p>
      <p>
        <Link href="/">{t.verify}</Link>
      </p>
    </main>
  );
}
