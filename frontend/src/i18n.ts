import { useCallback } from 'react'
import { useMaybeAuth } from './context/AuthContext'
import type { Language } from './types'

/**
 * Interface text in the four languages FixSaathi supports. The AI's replies follow the same setting on the server.
 * Strings not listed for a language fall back to English. Error messages that come from the server stay in English.
 */
const en = {
  'nav.newChat': 'New chat', 'nav.home': 'Home', 'nav.search': 'Search chats', 'nav.settings': 'Settings', 'nav.signOut': 'Sign out',
  'nav.manager': 'Manager dashboard', 'nav.senior': 'Senior support', 'nav.reports': 'Service reports', 'nav.menu': 'Open menu', 'nav.close': 'Close menu',
  'nav.collapse': 'Collapse sidebar', 'nav.expand': 'Expand sidebar', 'nav.chats': 'Chats', 'nav.account': 'Account menu',
  'group.today': 'Today', 'group.yesterday': 'Yesterday', 'group.week': 'Previous 7 days', 'group.older': 'Older',
  'chat.options': 'Chat options', 'chat.rename': 'Rename', 'chat.delete': 'Delete', 'chat.deleteTitle': 'Delete chat?',
  'chat.deleteBody': '“{title}” will be removed from your chat history. Service reports and safety records already saved are kept.',
  'chat.cancel': 'Cancel', 'chat.save': 'Save', 'chat.noChats': 'No chats yet', 'chat.noMatches': 'No chats match “{q}”',
  'chat.searchPlaceholder': 'Search your chats', 'chat.loadError': 'Could not load your chats.', 'chat.retry': 'Retry',
  'chat.workspace': 'Repair workspace', 'chat.downloadPdf': 'Download PDF', 'chat.preparing': 'Preparing…',
  'chat.disclaimer': 'FixSaathi can make mistakes. Verify isolation with your own tester before opening anything.',
  'chat.copy': 'Copy', 'chat.copied': 'Copied', 'chat.readAloud': 'Read aloud', 'chat.aiGenerated': 'AI-generated, check before acting',
  'chat.helpful': 'Helpful', 'chat.notHelpful': 'Not helpful', 'chat.whatWrong': 'What was wrong? (optional)', 'chat.send': 'Send', 'chat.thanks': 'Thanks, noted', 'chat.rateFailed': 'Could not save. Try again.',
  'chat.emptyTitle': 'How can I help with your repair?', 'chat.emptySub': 'Describe the fault, add a photo, or tap the microphone and speak.',
  'chat.notFound': 'This chat could not be opened. It may have been deleted.', 'chat.backHome': 'Back to Home',
  'chat.pdfTitle': 'Repair report ready', 'chat.pdfSub': 'Built from the data recorded in this conversation',
  'think.read': 'Reading your message', 'think.check': 'Checking repair records', 'think.write': 'Writing the answer', 'think.slow': 'The AI service is busy, still working on it',
  'home.morning': 'Good morning', 'home.afternoon': 'Good afternoon', 'home.evening': 'Good evening', 'home.hello': 'Hello, {name}',
  'home.sub': 'What are we fixing today?', 'home.appliance': 'Appliance',
  'composer.placeholder': 'Describe the fault, e.g. “LG split AC showing CH38, not cooling”', 'composer.followup': 'Ask a follow-up or report what you checked',
  'voice.speak': 'Speak', 'voice.start': 'Start speaking', 'voice.listening': 'Listening', 'voice.listenHint': 'Speak now. Press Done when you finish.',
  'voice.starting': 'Starting microphone…', 'voice.finishing': 'Finishing…', 'voice.done': 'Done', 'voice.cancel': 'Cancel',
  'voice.speakerOn': 'Speaker on: answers to voice messages are spoken', 'voice.speakerOff': 'Speaker off: answers to voice messages are text only',
  'voice.speaking': 'FixSaathi is speaking', 'voice.stop': 'Stop', 'voice.stopSpeaking': 'Stop speaking',
  'voice.err.unsupported': 'Voice input needs Chrome, Edge or Safari.', 'voice.err.mic-denied': 'Microphone permission was denied. Allow it in your browser settings and try again.',
  'voice.err.no-mic': 'No microphone was found, or another app is using it.', 'voice.err.network': 'Speech recognition needs an internet connection.',
  'voice.err.empty': 'I did not catch that. Tap the microphone and try again.',
  'settings.title': 'Settings', 'settings.language': 'Language', 'settings.languageHint': 'Menus and FixSaathi’s replies use this language. Typing in Hinglish always works.',
  'settings.appearance': 'Appearance', 'settings.dark': 'Dark', 'settings.light': 'Light', 'settings.system': 'System',
  'settings.voice': 'Voice', 'settings.voiceHint': 'Typed messages are answered in text only. Replies to voice messages are spoken while the speaker is on; any reply can be read aloud.',
  'voice.preparing': 'Preparing voice', 'voice.naturalVoice': 'natural voice', 'voice.personalVoice': 'your voice', 'voice.deviceVoice': 'device voice', 'settings.aiVoice': 'FixSaathi voice', 'settings.aiVoiceHint': 'Your own voice by default, then natural Gemini voices. If none is available, the device voice below is used.', 'settings.deviceOnly': 'Device voice only', 'settings.deviceVoice': 'Device voice (fallback)', 'settings.testDevice': 'Test device voice', 'voice.v.personal': 'Personal voice (ElevenLabs)', 'settings.testPersonal': 'Test my cloned voice', 'settings.testPersonalOk': 'Playing your ElevenLabs voice', 'settings.testPersonalFail': 'Your cloned voice did not play. No other voice was used.', 'voice.v.Charon': 'Charon · deep, informative', 'voice.v.Leda': 'Leda · youthful, bright', 'voice.v.Achird': 'Achird · friendly', 'voice.v.Sulafat': 'Sulafat · warm', 'voice.v.Puck': 'Puck · upbeat', 'voice.v.Kore': 'Kore · firm, clear', 'voice.v.Iapetus': 'Iapetus · clear, crisp', 'voice.v.Orus': 'Orus · firm, steady', 'voice.v.Alnilam': 'Alnilam · firm, even', 'voice.v.Sadaltager': 'Sadaltager · knowledgeable, expressive',
  'settings.voiceAuto': 'Automatic (best available)', 'settings.test': 'Test voice', 'settings.speed': 'Speaking speed',
  'settings.relaxed': 'Relaxed', 'settings.natural': 'Natural', 'settings.brisk': 'Brisk', 'settings.speakReplies': 'Speaker: speak answers to voice messages',
  'settings.noVoices': 'This browser has no voices for this language, so replies are shown as text.', 'settings.account': 'Account', 'settings.saved': 'Saved',
  'settings.voiceSample': 'Switch off the MCB first, then check with your tester that there is no live line.',
  'role.technician': 'Technician', 'role.manager': 'Manager', 'role.admin': 'Admin',
  'app.split_ac': 'Split AC', 'app.washing_machine': 'Washing machine', 'app.refrigerator': 'Refrigerator', 'app.ceiling_fan': 'Ceiling fan',
  'app.microwave_oven': 'Microwave', 'app.water_purifier': 'Water purifier', 'app.mcb_electrical': 'MCB / wiring', 'app.rooftop_solar': 'Rooftop solar',
  'sug.ac': 'Diagnose an AC problem', 'sug.fan': 'Inspect a ceiling fan', 'sug.wm': 'Troubleshoot a washing machine', 'sug.part': 'Identify an electrical component',
}
export type Key = keyof typeof en

const hi: Partial<Record<Key, string>> = {
  'nav.newChat': 'नई चैट', 'nav.home': 'होम', 'nav.search': 'चैट खोजें', 'nav.settings': 'सेटिंग्स', 'nav.signOut': 'साइन आउट',
  'nav.manager': 'मैनेजर डैशबोर्ड', 'nav.senior': 'सीनियर सहायता', 'nav.reports': 'सर्विस रिपोर्ट', 'nav.menu': 'मेन्यू खोलें', 'nav.close': 'मेन्यू बंद करें', 'nav.chats': 'चैट',
  'group.today': 'आज', 'group.yesterday': 'कल', 'group.week': 'पिछले 7 दिन', 'group.older': 'पुरानी',
  'chat.options': 'चैट विकल्प', 'chat.rename': 'नाम बदलें', 'chat.delete': 'हटाएँ', 'chat.deleteTitle': 'चैट हटाएँ?',
  'chat.deleteBody': '“{title}” आपकी चैट हिस्ट्री से हट जाएगी। पहले से सेव की गई सर्विस रिपोर्ट और सुरक्षा रिकॉर्ड बने रहेंगे।',
  'chat.cancel': 'रद्द करें', 'chat.save': 'सेव करें', 'chat.noChats': 'अभी कोई चैट नहीं', 'chat.noMatches': '“{q}” से कोई चैट नहीं मिली',
  'chat.searchPlaceholder': 'अपनी चैट खोजें', 'chat.loadError': 'आपकी चैट लोड नहीं हो सकीं।', 'chat.retry': 'फिर कोशिश करें',
  'chat.workspace': 'रिपेयर वर्कस्पेस', 'chat.downloadPdf': 'PDF डाउनलोड करें', 'chat.preparing': 'तैयार हो रहा है…',
  'chat.disclaimer': 'FixSaathi से गलती हो सकती है। कुछ भी खोलने से पहले अपने टेस्टर से जाँचें कि बिजली बंद है।',
  'chat.copy': 'कॉपी', 'chat.copied': 'कॉपी हुआ', 'chat.readAloud': 'सुनें', 'chat.aiGenerated': 'AI से बना, काम से पहले जाँचें',
  'chat.helpful': 'काम का', 'chat.notHelpful': 'काम का नहीं', 'chat.whatWrong': 'क्या गलत था? (वैकल्पिक)', 'chat.send': 'भेजें', 'chat.thanks': 'धन्यवाद, दर्ज हो गया', 'chat.rateFailed': 'सेव नहीं हुआ। फिर कोशिश करें।',
  'chat.emptyTitle': 'रिपेयर में कैसे मदद करूँ?', 'chat.emptySub': 'खराबी बताएँ, फ़ोटो जोड़ें, या माइक दबाकर बोलें।',
  'chat.notFound': 'यह चैट नहीं खुल सकी। शायद इसे हटा दिया गया है।', 'chat.backHome': 'होम पर जाएँ',
  'chat.pdfTitle': 'रिपेयर रिपोर्ट तैयार है', 'chat.pdfSub': 'इस चैट के रिकॉर्ड किए गए डेटा से बनी',
  'think.read': 'आपका संदेश पढ़ रहा है', 'think.check': 'रिपेयर रिकॉर्ड देख रहा है', 'think.write': 'जवाब लिख रहा है', 'think.slow': 'AI सेवा व्यस्त है, अभी भी काम चल रहा है',
  'home.morning': 'सुप्रभात', 'home.afternoon': 'नमस्कार', 'home.evening': 'शुभ संध्या', 'home.hello': 'नमस्ते, {name}',
  'home.sub': 'आज क्या ठीक करना है?', 'home.appliance': 'उपकरण',
  'composer.placeholder': 'खराबी बताएँ, जैसे “LG स्प्लिट AC में CH38 दिख रहा है, ठंडा नहीं कर रहा”', 'composer.followup': 'आगे पूछें या बताएँ कि आपने क्या जाँचा',
  'voice.speak': 'बोलें', 'voice.start': 'बोलना शुरू करें', 'voice.listening': 'सुन रहा है', 'voice.listenHint': 'अब बोलें। पूरा होने पर “हो गया” दबाएँ।',
  'voice.starting': 'माइक शुरू हो रहा है…', 'voice.finishing': 'पूरा कर रहा है…', 'voice.done': 'हो गया', 'voice.cancel': 'रद्द करें',
  'voice.speakerOn': 'स्पीकर चालू: आवाज़ वाले संदेशों के जवाब बोले जाएँगे', 'voice.speakerOff': 'स्पीकर बंद: आवाज़ वाले संदेशों के जवाब सिर्फ़ टेक्स्ट में',
  'voice.speaking': 'FixSaathi बोल रहा है', 'voice.stop': 'रोकें', 'voice.stopSpeaking': 'बोलना रोकें',
  'voice.err.unsupported': 'वॉइस इनपुट के लिए Chrome, Edge या Safari चाहिए।', 'voice.err.mic-denied': 'माइक की अनुमति नहीं मिली। ब्राउज़र सेटिंग्स में अनुमति दें और फिर कोशिश करें।',
  'voice.err.no-mic': 'माइक नहीं मिला, या कोई दूसरा ऐप उसे इस्तेमाल कर रहा है।', 'voice.err.network': 'आवाज़ पहचानने के लिए इंटरनेट चाहिए।',
  'voice.err.empty': 'मैं सुन नहीं पाया। माइक दबाकर फिर बोलें।',
  'settings.title': 'सेटिंग्स', 'settings.language': 'भाषा', 'settings.languageHint': 'मेन्यू और FixSaathi के जवाब इसी भाषा में होंगे। हिंग्लिश में लिखना हमेशा चलेगा।',
  'settings.appearance': 'रूप', 'settings.dark': 'डार्क', 'settings.light': 'लाइट', 'settings.system': 'सिस्टम',
  'settings.voice': 'आवाज़', 'settings.voiceHint': 'टाइप किए गए संदेशों का जवाब सिर्फ़ टेक्स्ट में मिलता है। स्पीकर चालू हो तो आवाज़ वाले संदेशों के जवाब बोले जाते हैं; किसी भी जवाब को सुन सकते हैं।',
  'voice.preparing': 'आवाज़ तैयार हो रही है', 'voice.naturalVoice': 'प्राकृतिक आवाज़', 'voice.personalVoice': 'आपकी आवाज़', 'voice.deviceVoice': 'डिवाइस की आवाज़', 'settings.aiVoice': 'FixSaathi की आवाज़', 'settings.aiVoiceHint': 'प्राकृतिक Gemini आवाज़। उपलब्ध न हो तो नीचे वाली डिवाइस की आवाज़ इस्तेमाल होती है।', 'settings.deviceOnly': 'सिर्फ़ डिवाइस की आवाज़', 'settings.deviceVoice': 'डिवाइस की आवाज़ (बैकअप)', 'settings.testDevice': 'डिवाइस की आवाज़ सुनें',
  'settings.voiceAuto': 'अपने-आप (सबसे अच्छी उपलब्ध)', 'settings.test': 'आवाज़ सुनें', 'settings.speed': 'बोलने की गति',
  'settings.relaxed': 'धीमी', 'settings.natural': 'सामान्य', 'settings.brisk': 'तेज़', 'settings.speakReplies': 'स्पीकर: आवाज़ वाले संदेशों के जवाब बोलें',
  'settings.noVoices': 'इस ब्राउज़र में इस भाषा की कोई आवाज़ नहीं है, इसलिए जवाब टेक्स्ट में दिखेंगे।', 'settings.account': 'खाता', 'settings.saved': 'सेव हो गया',
  'settings.voiceSample': 'पहले MCB बंद करें, फिर टेस्टर से जाँचें कि कोई लाइव लाइन नहीं है।',
  'role.technician': 'तकनीशियन', 'role.manager': 'मैनेजर', 'role.admin': 'एडमिन',
  'app.split_ac': 'स्प्लिट AC', 'app.washing_machine': 'वॉशिंग मशीन', 'app.refrigerator': 'फ्रिज', 'app.ceiling_fan': 'सीलिंग फैन',
  'app.microwave_oven': 'माइक्रोवेव', 'app.water_purifier': 'वॉटर प्यूरीफायर', 'app.mcb_electrical': 'MCB / वायरिंग', 'app.rooftop_solar': 'रूफटॉप सोलर',
  'sug.ac': 'AC की समस्या जाँचें', 'sug.fan': 'सीलिंग फैन जाँचें', 'sug.wm': 'वॉशिंग मशीन की खराबी ढूँढें', 'sug.part': 'बिजली का पुर्ज़ा पहचानें',
}

const kn: Partial<Record<Key, string>> = {
  'nav.newChat': 'ಹೊಸ ಚಾಟ್', 'nav.home': 'ಮುಖಪುಟ', 'nav.search': 'ಚಾಟ್‌ಗಳನ್ನು ಹುಡುಕಿ', 'nav.settings': 'ಸೆಟ್ಟಿಂಗ್‌ಗಳು', 'nav.signOut': 'ಸೈನ್ ಔಟ್',
  'nav.manager': 'ವ್ಯವಸ್ಥಾಪಕ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್', 'nav.senior': 'ಹಿರಿಯ ತಂತ್ರಜ್ಞರ ಸಹಾಯ', 'nav.reports': 'ಸೇವಾ ವರದಿಗಳು', 'nav.menu': 'ಮೆನು ತೆರೆಯಿರಿ', 'nav.close': 'ಮೆನು ಮುಚ್ಚಿ', 'nav.chats': 'ಚಾಟ್‌ಗಳು',
  'group.today': 'ಇಂದು', 'group.yesterday': 'ನಿನ್ನೆ', 'group.week': 'ಹಿಂದಿನ 7 ದಿನಗಳು', 'group.older': 'ಹಳೆಯವು',
  'chat.options': 'ಚಾಟ್ ಆಯ್ಕೆಗಳು', 'chat.rename': 'ಹೆಸರು ಬದಲಿಸಿ', 'chat.delete': 'ಅಳಿಸಿ', 'chat.deleteTitle': 'ಚಾಟ್ ಅಳಿಸಬೇಕೆ?',
  'chat.deleteBody': '“{title}” ನಿಮ್ಮ ಚಾಟ್ ಇತಿಹಾಸದಿಂದ ತೆಗೆದುಹಾಕಲಾಗುತ್ತದೆ. ಈಗಾಗಲೇ ಉಳಿಸಿದ ಸೇವಾ ವರದಿಗಳು ಮತ್ತು ಸುರಕ್ಷತಾ ದಾಖಲೆಗಳು ಉಳಿಯುತ್ತವೆ.',
  'chat.cancel': 'ರದ್ದುಮಾಡಿ', 'chat.save': 'ಉಳಿಸಿ', 'chat.noChats': 'ಇನ್ನೂ ಯಾವುದೇ ಚಾಟ್ ಇಲ್ಲ', 'chat.noMatches': '“{q}” ಗೆ ಹೊಂದುವ ಚಾಟ್ ಇಲ್ಲ',
  'chat.searchPlaceholder': 'ನಿಮ್ಮ ಚಾಟ್‌ಗಳನ್ನು ಹುಡುಕಿ', 'chat.loadError': 'ನಿಮ್ಮ ಚಾಟ್‌ಗಳನ್ನು ಲೋಡ್ ಮಾಡಲಾಗಲಿಲ್ಲ.', 'chat.retry': 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ',
  'chat.workspace': 'ದುರಸ್ತಿ ಕಾರ್ಯಕ್ಷೇತ್ರ', 'chat.downloadPdf': 'PDF ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ', 'chat.preparing': 'ಸಿದ್ಧಪಡಿಸುತ್ತಿದೆ…',
  'chat.disclaimer': 'FixSaathi ತಪ್ಪು ಮಾಡಬಹುದು. ಏನನ್ನಾದರೂ ತೆರೆಯುವ ಮೊದಲು ನಿಮ್ಮ ಟೆಸ್ಟರ್‌ನಿಂದ ವಿದ್ಯುತ್ ಕಡಿತವನ್ನು ಖಚಿತಪಡಿಸಿಕೊಳ್ಳಿ.',
  'chat.copy': 'ನಕಲಿಸಿ', 'chat.copied': 'ನಕಲಿಸಲಾಗಿದೆ', 'chat.readAloud': 'ಓದಿ ಹೇಳಿ', 'chat.aiGenerated': 'AI ರಚಿಸಿದ್ದು, ಬಳಸುವ ಮೊದಲು ಪರಿಶೀಲಿಸಿ',
  'chat.helpful': 'ಉಪಯುಕ್ತ', 'chat.notHelpful': 'ಉಪಯುಕ್ತವಲ್ಲ', 'chat.whatWrong': 'ಏನು ತಪ್ಪಾಗಿತ್ತು? (ಐಚ್ಛಿಕ)', 'chat.send': 'ಕಳುಹಿಸಿ', 'chat.thanks': 'ಧನ್ಯವಾದ, ದಾಖಲಿಸಲಾಗಿದೆ', 'chat.rateFailed': 'ಉಳಿಸಲಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
  'chat.emptyTitle': 'ನಿಮ್ಮ ದುರಸ್ತಿಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?', 'chat.emptySub': 'ದೋಷವನ್ನು ವಿವರಿಸಿ, ಫೋಟೋ ಸೇರಿಸಿ ಅಥವಾ ಮೈಕ್ ಒತ್ತಿ ಮಾತನಾಡಿ.',
  'chat.notFound': 'ಈ ಚಾಟ್ ತೆರೆಯಲಾಗಲಿಲ್ಲ. ಅದನ್ನು ಅಳಿಸಿರಬಹುದು.', 'chat.backHome': 'ಮುಖಪುಟಕ್ಕೆ ಹಿಂತಿರುಗಿ',
  'chat.pdfTitle': 'ದುರಸ್ತಿ ವರದಿ ಸಿದ್ಧವಾಗಿದೆ', 'chat.pdfSub': 'ಈ ಚಾಟ್‌ನ ದಾಖಲಿತ ಮಾಹಿತಿಯಿಂದ ರಚಿಸಲಾಗಿದೆ',
  'think.read': 'ನಿಮ್ಮ ಸಂದೇಶ ಓದುತ್ತಿದೆ', 'think.check': 'ದುರಸ್ತಿ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿದೆ', 'think.write': 'ಉತ್ತರ ಬರೆಯುತ್ತಿದೆ', 'think.slow': 'AI ಸೇವೆ ಕಾರ್ಯನಿರತವಾಗಿದೆ, ಇನ್ನೂ ಪ್ರಯತ್ನಿಸುತ್ತಿದೆ',
  'home.morning': 'ಶುಭೋದಯ', 'home.afternoon': 'ಶುಭ ಮಧ್ಯಾಹ್ನ', 'home.evening': 'ಶುಭ ಸಂಜೆ', 'home.hello': 'ನಮಸ್ಕಾರ, {name}',
  'home.sub': 'ಇಂದು ಏನನ್ನು ಸರಿಪಡಿಸೋಣ?', 'home.appliance': 'ಉಪಕರಣ',
  'composer.placeholder': 'ದೋಷವನ್ನು ವಿವರಿಸಿ, ಉದಾ. “LG ಸ್ಪ್ಲಿಟ್ AC ಯಲ್ಲಿ CH38 ತೋರಿಸುತ್ತಿದೆ, ತಂಪಾಗುತ್ತಿಲ್ಲ”', 'composer.followup': 'ಮುಂದಿನ ಪ್ರಶ್ನೆ ಕೇಳಿ ಅಥವಾ ನೀವು ಪರಿಶೀಲಿಸಿದ್ದನ್ನು ತಿಳಿಸಿ',
  'voice.speak': 'ಮಾತನಾಡಿ', 'voice.start': 'ಮಾತನಾಡಲು ಪ್ರಾರಂಭಿಸಿ', 'voice.listening': 'ಆಲಿಸುತ್ತಿದೆ', 'voice.listenHint': 'ಈಗ ಮಾತನಾಡಿ. ಮುಗಿದ ನಂತರ “ಮುಗಿದಿದೆ” ಒತ್ತಿ.',
  'voice.starting': 'ಮೈಕ್ ಪ್ರಾರಂಭವಾಗುತ್ತಿದೆ…', 'voice.finishing': 'ಮುಗಿಸುತ್ತಿದೆ…', 'voice.done': 'ಮುಗಿದಿದೆ', 'voice.cancel': 'ರದ್ದುಮಾಡಿ',
  'voice.speakerOn': 'ಸ್ಪೀಕರ್ ಆನ್: ಧ್ವನಿ ಸಂದೇಶಗಳ ಉತ್ತರಗಳನ್ನು ಮಾತನಾಡಲಾಗುತ್ತದೆ', 'voice.speakerOff': 'ಸ್ಪೀಕರ್ ಆಫ್: ಧ್ವನಿ ಸಂದೇಶಗಳ ಉತ್ತರಗಳು ಪಠ್ಯ ಮಾತ್ರ',
  'voice.speaking': 'FixSaathi ಮಾತನಾಡುತ್ತಿದೆ', 'voice.stop': 'ನಿಲ್ಲಿಸಿ', 'voice.stopSpeaking': 'ಮಾತು ನಿಲ್ಲಿಸಿ',
  'voice.err.unsupported': 'ಧ್ವನಿ ಇನ್‌ಪುಟ್‌ಗೆ Chrome, Edge ಅಥವಾ Safari ಬೇಕು.', 'voice.err.mic-denied': 'ಮೈಕ್ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ. ಬ್ರೌಸರ್ ಸೆಟ್ಟಿಂಗ್‌ಗಳಲ್ಲಿ ಅನುಮತಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.',
  'voice.err.no-mic': 'ಮೈಕ್ ಸಿಗಲಿಲ್ಲ, ಅಥವಾ ಬೇರೆ ಆ್ಯಪ್ ಅದನ್ನು ಬಳಸುತ್ತಿದೆ.', 'voice.err.network': 'ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆಗೆ ಇಂಟರ್ನೆಟ್ ಬೇಕು.',
  'voice.err.empty': 'ನನಗೆ ಕೇಳಿಸಲಿಲ್ಲ. ಮೈಕ್ ಒತ್ತಿ ಮತ್ತೆ ಹೇಳಿ.',
  'settings.title': 'ಸೆಟ್ಟಿಂಗ್‌ಗಳು', 'settings.language': 'ಭಾಷೆ', 'settings.languageHint': 'ಮೆನುಗಳು ಮತ್ತು FixSaathi ಉತ್ತರಗಳು ಈ ಭಾಷೆಯಲ್ಲಿರುತ್ತವೆ. ಹಿಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಬರೆಯುವುದು ಯಾವಾಗಲೂ ಕೆಲಸ ಮಾಡುತ್ತದೆ.',
  'settings.appearance': 'ಗೋಚರತೆ', 'settings.dark': 'ಡಾರ್ಕ್', 'settings.light': 'ಲೈಟ್', 'settings.system': 'ಸಿಸ್ಟಮ್',
  'settings.voice': 'ಧ್ವನಿ', 'settings.voiceHint': 'ಟೈಪ್ ಮಾಡಿದ ಸಂದೇಶಗಳಿಗೆ ಪಠ್ಯದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರ. ಸ್ಪೀಕರ್ ಆನ್ ಇದ್ದರೆ ಧ್ವನಿ ಸಂದೇಶಗಳ ಉತ್ತರಗಳನ್ನು ಮಾತನಾಡಲಾಗುತ್ತದೆ; ಯಾವುದೇ ಉತ್ತರವನ್ನು ಕೇಳಬಹುದು.',
  'voice.preparing': 'ಧ್ವನಿ ಸಿದ್ಧವಾಗುತ್ತಿದೆ', 'voice.naturalVoice': 'ಸಹಜ ಧ್ವನಿ', 'voice.personalVoice': 'ನಿಮ್ಮ ಧ್ವನಿ', 'voice.deviceVoice': 'ಸಾಧನದ ಧ್ವನಿ', 'settings.aiVoice': 'FixSaathi ಧ್ವನಿ', 'settings.aiVoiceHint': 'ಸಹಜ Gemini ಧ್ವನಿ. ಲಭ್ಯವಿಲ್ಲದಿದ್ದರೆ ಕೆಳಗಿನ ಸಾಧನದ ಧ್ವನಿ ಬಳಸಲಾಗುತ್ತದೆ.', 'settings.deviceOnly': 'ಸಾಧನದ ಧ್ವನಿ ಮಾತ್ರ', 'settings.deviceVoice': 'ಸಾಧನದ ಧ್ವನಿ (ಬ್ಯಾಕಪ್)', 'settings.testDevice': 'ಸಾಧನದ ಧ್ವನಿ ಕೇಳಿ',
  'settings.voiceAuto': 'ಸ್ವಯಂಚಾಲಿತ (ಅತ್ಯುತ್ತಮ ಲಭ್ಯ)', 'settings.test': 'ಧ್ವನಿ ಪರೀಕ್ಷಿಸಿ', 'settings.speed': 'ಮಾತಿನ ವೇಗ',
  'settings.relaxed': 'ನಿಧಾನ', 'settings.natural': 'ಸಾಮಾನ್ಯ', 'settings.brisk': 'ವೇಗ', 'settings.speakReplies': 'ಸ್ಪೀಕರ್: ಧ್ವನಿ ಸಂದೇಶಗಳ ಉತ್ತರಗಳನ್ನು ಮಾತನಾಡಿ',
  'settings.noVoices': 'ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಈ ಭಾಷೆಯ ಧ್ವನಿ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಉತ್ತರಗಳು ಪಠ್ಯವಾಗಿ ತೋರುತ್ತವೆ.', 'settings.account': 'ಖಾತೆ', 'settings.saved': 'ಉಳಿಸಲಾಗಿದೆ',
  'settings.voiceSample': 'ಮೊದಲು MCB ಆಫ್ ಮಾಡಿ, ನಂತರ ಟೆಸ್ಟರ್‌ನಿಂದ ಲೈವ್ ಲೈನ್ ಇಲ್ಲ ಎಂದು ಪರಿಶೀಲಿಸಿ.',
  'role.technician': 'ತಂತ್ರಜ್ಞ', 'role.manager': 'ವ್ಯವಸ್ಥಾಪಕ', 'role.admin': 'ನಿರ್ವಾಹಕ',
  'app.split_ac': 'ಸ್ಪ್ಲಿಟ್ AC', 'app.washing_machine': 'ವಾಷಿಂಗ್ ಮೆಷಿನ್', 'app.refrigerator': 'ಫ್ರಿಜ್', 'app.ceiling_fan': 'ಸೀಲಿಂಗ್ ಫ್ಯಾನ್',
  'app.microwave_oven': 'ಮೈಕ್ರೋವೇವ್', 'app.water_purifier': 'ನೀರು ಶುದ್ಧೀಕರಣ ಯಂತ್ರ', 'app.mcb_electrical': 'MCB / ವೈರಿಂಗ್', 'app.rooftop_solar': 'ಮೇಲ್ಛಾವಣಿ ಸೌರ',
  'sug.ac': 'AC ಸಮಸ್ಯೆ ಪತ್ತೆಹಚ್ಚಿ', 'sug.fan': 'ಸೀಲಿಂಗ್ ಫ್ಯಾನ್ ಪರಿಶೀಲಿಸಿ', 'sug.wm': 'ವಾಷಿಂಗ್ ಮೆಷಿನ್ ದೋಷ ಹುಡುಕಿ', 'sug.part': 'ವಿದ್ಯುತ್ ಭಾಗವನ್ನು ಗುರುತಿಸಿ',
}

const ta: Partial<Record<Key, string>> = {
  'nav.newChat': 'புதிய உரையாடல்', 'nav.home': 'முகப்பு', 'nav.search': 'உரையாடல்களைத் தேடு', 'nav.settings': 'அமைப்புகள்', 'nav.signOut': 'வெளியேறு',
  'nav.manager': 'மேலாளர் டாஷ்போர்டு', 'nav.senior': 'மூத்த தொழில்நுட்ப உதவி', 'nav.reports': 'சேவை அறிக்கைகள்', 'nav.menu': 'மெனுவைத் திற', 'nav.close': 'மெனுவை மூடு', 'nav.chats': 'உரையாடல்கள்',
  'group.today': 'இன்று', 'group.yesterday': 'நேற்று', 'group.week': 'கடந்த 7 நாட்கள்', 'group.older': 'பழையவை',
  'chat.options': 'உரையாடல் விருப்பங்கள்', 'chat.rename': 'பெயர் மாற்று', 'chat.delete': 'நீக்கு', 'chat.deleteTitle': 'உரையாடலை நீக்கவா?',
  'chat.deleteBody': '“{title}” உங்கள் உரையாடல் வரலாற்றிலிருந்து நீக்கப்படும். ஏற்கனவே சேமிக்கப்பட்ட சேவை அறிக்கைகளும் பாதுகாப்புப் பதிவுகளும் வைக்கப்படும்.',
  'chat.cancel': 'ரத்து செய்', 'chat.save': 'சேமி', 'chat.noChats': 'இன்னும் உரையாடல்கள் இல்லை', 'chat.noMatches': '“{q}” உடன் பொருந்தும் உரையாடல் இல்லை',
  'chat.searchPlaceholder': 'உங்கள் உரையாடல்களைத் தேடு', 'chat.loadError': 'உங்கள் உரையாடல்களை ஏற்ற முடியவில்லை.', 'chat.retry': 'மீண்டும் முயல்',
  'chat.workspace': 'பழுதுபார்ப்பு பணியிடம்', 'chat.downloadPdf': 'PDF பதிவிறக்கு', 'chat.preparing': 'தயாராகிறது…',
  'chat.disclaimer': 'FixSaathi தவறு செய்யலாம். எதையும் திறக்கும் முன் உங்கள் டெஸ்டரால் மின்சாரம் துண்டிக்கப்பட்டதை உறுதிசெய்யுங்கள்.',
  'chat.copy': 'நகலெடு', 'chat.copied': 'நகலெடுக்கப்பட்டது', 'chat.readAloud': 'உரக்கப் படி', 'chat.aiGenerated': 'AI உருவாக்கியது, செயல்படும் முன் சரிபார்க்கவும்',
  'chat.emptyTitle': 'உங்கள் பழுதுபார்ப்புக்கு எப்படி உதவலாம்?', 'chat.emptySub': 'பிழையை விவரிக்கவும், புகைப்படம் சேர்க்கவும், அல்லது மைக்கை அழுத்திப் பேசவும்.',
  'chat.notFound': 'இந்த உரையாடலைத் திறக்க முடியவில்லை. அது நீக்கப்பட்டிருக்கலாம்.', 'chat.backHome': 'முகப்புக்குத் திரும்பு',
  'chat.pdfTitle': 'பழுதுபார்ப்பு அறிக்கை தயார்', 'chat.pdfSub': 'இந்த உரையாடலின் பதிவுத் தரவிலிருந்து உருவாக்கப்பட்டது',
  'think.read': 'உங்கள் செய்தியைப் படிக்கிறது', 'think.check': 'பழுதுபார்ப்புப் பதிவுகளைச் சரிபார்க்கிறது', 'think.write': 'பதிலை எழுதுகிறது', 'think.slow': 'AI சேவை பரபரப்பாக உள்ளது, இன்னும் முயற்சிக்கிறது',
  'home.morning': 'காலை வணக்கம்', 'home.afternoon': 'மதிய வணக்கம்', 'home.evening': 'மாலை வணக்கம்', 'home.hello': 'வணக்கம், {name}',
  'home.sub': 'இன்று எதைச் சரிசெய்யலாம்?', 'home.appliance': 'சாதனம்',
  'composer.placeholder': 'பிழையை விவரிக்கவும், எ.கா. “LG ஸ்பிளிட் AC-யில் CH38 காட்டுகிறது, குளிரவில்லை”', 'composer.followup': 'தொடர் கேள்வி கேளுங்கள் அல்லது நீங்கள் சரிபார்த்ததைச் சொல்லுங்கள்',
  'voice.speak': 'பேசு', 'voice.start': 'பேசத் தொடங்கு', 'voice.listening': 'கேட்கிறது', 'voice.listenHint': 'இப்போது பேசுங்கள். முடிந்ததும் “முடிந்தது” அழுத்துங்கள்.',
  'voice.starting': 'மைக் தொடங்குகிறது…', 'voice.finishing': 'முடிக்கிறது…', 'voice.done': 'முடிந்தது', 'voice.cancel': 'ரத்து செய்',
  'voice.speakerOn': 'ஒலிபெருக்கி இயக்கம்: குரல் செய்திகளின் பதில்கள் பேசப்படும்', 'voice.speakerOff': 'ஒலிபெருக்கி நிறுத்தம்: குரல் செய்திகளின் பதில்கள் உரையாக மட்டும்',
  'voice.speaking': 'FixSaathi பேசுகிறது', 'voice.stop': 'நிறுத்து', 'voice.stopSpeaking': 'பேச்சை நிறுத்து',
  'voice.err.unsupported': 'குரல் உள்ளீட்டுக்கு Chrome, Edge அல்லது Safari தேவை.', 'voice.err.mic-denied': 'மைக் அனுமதி மறுக்கப்பட்டது. உலாவி அமைப்புகளில் அனுமதித்து மீண்டும் முயலுங்கள்.',
  'voice.err.no-mic': 'மைக் கிடைக்கவில்லை, அல்லது வேறு செயலி அதைப் பயன்படுத்துகிறது.', 'voice.err.network': 'குரல் அறிதலுக்கு இணைய இணைப்பு தேவை.',
  'voice.err.empty': 'எனக்குக் கேட்கவில்லை. மைக்கை அழுத்தி மீண்டும் சொல்லுங்கள்.',
  'settings.title': 'அமைப்புகள்', 'settings.language': 'மொழி', 'settings.languageHint': 'மெனுக்களும் FixSaathi பதில்களும் இந்த மொழியில் இருக்கும். ஹிங்கிலிஷில் எழுதுவது எப்போதும் வேலை செய்யும்.',
  'settings.appearance': 'தோற்றம்', 'settings.dark': 'இருண்ட', 'settings.light': 'ஒளிர்வு', 'settings.system': 'கணினி',
  'settings.voice': 'குரல்', 'settings.voiceHint': 'தட்டச்சு செய்த செய்திகளுக்கு உரையில் மட்டும் பதில். ஸ்பீக்கர் இயக்கத்தில் இருந்தால் குரல் செய்திகளின் பதில்கள் பேசப்படும்; எந்தப் பதிலையும் கேட்கலாம்.',
  'voice.preparing': 'குரல் தயாராகிறது', 'voice.naturalVoice': 'இயல்பான குரல்', 'voice.personalVoice': 'உங்கள் குரல்', 'voice.deviceVoice': 'சாதனக் குரல்', 'settings.aiVoice': 'FixSaathi குரல்', 'settings.aiVoiceHint': 'இயல்பான Gemini குரல். கிடைக்காவிட்டால் கீழே உள்ள சாதனக் குரல் பயன்படும்.', 'settings.deviceOnly': 'சாதனக் குரல் மட்டும்', 'settings.deviceVoice': 'சாதனக் குரல் (மாற்று)', 'settings.testDevice': 'சாதனக் குரலைக் கேளுங்கள்',
  'settings.voiceAuto': 'தானியங்கி (சிறந்தது)', 'settings.test': 'குரலைச் சோதி', 'settings.speed': 'பேச்சு வேகம்',
  'settings.relaxed': 'மெதுவாக', 'settings.natural': 'இயல்பு', 'settings.brisk': 'வேகமாக', 'settings.speakReplies': 'ஸ்பீக்கர்: குரல் செய்திகளின் பதில்களைப் பேசு',
  'settings.noVoices': 'இந்த உலாவியில் இந்த மொழிக்கான குரல் இல்லை, எனவே பதில்கள் உரையாகக் காட்டப்படும்.', 'settings.account': 'கணக்கு', 'settings.saved': 'சேமிக்கப்பட்டது',
  'settings.voiceSample': 'முதலில் MCB-ஐ அணைக்கவும், பிறகு லைவ் லைன் இல்லை என்பதை டெஸ்டரால் சரிபார்க்கவும்.',
  'role.technician': 'தொழில்நுட்பர்', 'role.manager': 'மேலாளர்', 'role.admin': 'நிர்வாகி',
  'app.split_ac': 'ஸ்பிளிட் AC', 'app.washing_machine': 'சலவை இயந்திரம்', 'app.refrigerator': 'குளிர்சாதனப் பெட்டி', 'app.ceiling_fan': 'மின்விசிறி',
  'app.microwave_oven': 'மைக்ரோவேவ்', 'app.water_purifier': 'நீர் சுத்திகரிப்பான்', 'app.mcb_electrical': 'MCB / வயரிங்', 'app.rooftop_solar': 'கூரை சோலார்',
  'sug.ac': 'AC பிரச்சினையைக் கண்டறி', 'sug.fan': 'மின்விசிறியை ஆய்வு செய்', 'sug.wm': 'சலவை இயந்திரச் சிக்கலைத் தீர்', 'sug.part': 'மின் பாகத்தை அடையாளம் காண்',
}

const TABLES: Record<Language, Partial<Record<Key, string>>> = { English: en, Hindi: hi, Kannada: kn, Tamil: ta }
export const LANG_TAG: Record<Language, string> = { English: 'en', Hindi: 'hi', Kannada: 'kn', Tamil: 'ta' }
export const LANG_NATIVE: Record<Language, string> = { English: 'English', Hindi: 'हिन्दी', Kannada: 'ಕನ್ನಡ', Tamil: 'தமிழ்' }

export function translate(lang: Language | undefined, key: Key, vars?: Record<string, string>): string {
  let s = TABLES[lang ?? 'English']?.[key] ?? en[key]
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, v)
  return s
}

/** t('nav.newChat') in the signed-in technician's language. */
export function useT() {
  const lang = useMaybeAuth()?.user?.preferred_language
  return useCallback((key: Key, vars?: Record<string, string>) => translate(lang, key, vars), [lang])
}

export function useLanguage(): Language { return useMaybeAuth()?.user?.preferred_language ?? 'English' }
