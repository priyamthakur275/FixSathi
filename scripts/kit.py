from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
F='/usr/share/fonts/truetype/google-fonts/'
for n,f in [('P','Poppins-Regular.ttf'),('PB','Poppins-Bold.ttf'),('PM','Poppins-Medium.ttf')]:
    pdfmetrics.registerFont(TTFont(n,F+f))
W,H=A4; M=40
BLUE=HexColor('#1a73e8'); INK=HexColor('#202124'); GREY=HexColor('#5f6368'); LINE=HexColor('#dadce0'); BG=HexColor('#e8f0fe'); GREEN=HexColor('#188038')

def wrap(c,text,x,y,w,font='P',size=10,lead=14,color=INK):
    c.setFont(font,size); c.setFillColor(color)
    words=text.split(); line=''
    for wd in words:
        t=(line+' '+wd).strip()
        if c.stringWidth(t,font,size)>w: c.drawString(x,y,line); y-=lead; line=wd
        else: line=t
    if line: c.drawString(x,y,line); y-=lead
    return y

def header(c,title,sub):
    c.setFillColor(BLUE); c.rect(0,H-70,W,70,fill=1,stroke=0)
    c.setFillColor(HexColor('#ffffff')); c.setFont('PB',18); c.drawString(M,H-40,title)
    c.setFont('P',10); c.drawString(M,H-57,sub)
    c.setFont('PB',11); c.drawRightString(W-M,H-40,'FixSaathi')

def lines(c,y,n,x=M,w=None):
    w=w or W-2*M; c.setStrokeColor(LINE); c.setLineWidth(.7)
    for i in range(n): c.line(x,y-i*18,x+w,y-i*18)
    return y-n*18

def footer(c,t):
    c.setFont('P',8); c.setFillColor(GREY); c.drawString(M,22,t); c.drawRightString(W-M,22,'Tensor Trailblazers · BMSCE Bengaluru')

c=canvas.Canvas('/home/claude/fixsathi/round2/FixSaathi_Field_Visit_Kit.pdf',pagesize=A4)
c.setTitle('FixSaathi Field Visit Kit')

# Page 1: how to run the visit
header(c,'Field visit kit: technician trial','Use at 2–3 repair shops or service centres. 10 minutes per technician.')
y=H-100
c.setFont('PB',12); c.setFillColor(INK); c.drawString(M,y,'Before you go'); y-=18
for t in ['Open the deployed FixSaathi link on your phone; check "AI ready" on the start screen.',
          'Phone charged, volume up, hotspot on. Carry 1 printed letter-of-interest sheet per shop.',
          'Ask the owner first: "We are BMSCE students building an AI helper for technicians. Can one technician try it for 5 minutes?"']:
    y=wrap(c,'•  '+t,M,y,W-2*M,size=10); y-=2
y-=8
c.setFont('PB',12); c.drawString(M,y,'Run the 5-minute trial'); y-=18
steps=['Hand the phone to the technician. Language: Hinglish (or Kannada/Tamil if they prefer).',
 'Point the camera at any fan, AC, MCB board or washing machine in the shop.',
 'Let them speak the problem in their own words (e.g. "pankha slow chal raha hai").',
 'Do NOT help unless they are stuck. Watch: do they trust it? Is the safety step clear?',
 'Ask them to tap thumbs up / down at the end ("Was the guidance correct?"). This feeds our accuracy number.',
 'Then ask the 5 questions on page 2 and write the answers.',
 'With permission, record a 15-second video: name (or first name), shop, and one sentence about FixSaathi.']
for i,t in enumerate(steps,1):
    c.setFillColor(BLUE); c.circle(M+8,y+3.5,8,fill=1,stroke=0); c.setFillColor(HexColor('#ffffff')); c.setFont('PB',9); c.drawCentredString(M+8,y+0.5,str(i))
    y=wrap(c,t,M+24,y,W-2*M-24,size=10); y-=4
y-=8
c.setFillColor(BG); c.roundRect(M,y-112,W-2*M,112,8,fill=1,stroke=0)
yy=y-18; c.setFont('PB',11); c.setFillColor(INK); c.drawString(M+12,yy,'Say this to the owner (Hinglish)'); yy-=16
for t in ['"Sir, ek repeat visit mein aapka petrol, technician ka aadha din aur customer ka gussa jaata hai.',
          'FixSaathi technician ko live guide karta hai, safety pehle, aur report apne aap aapke phone par aati hai.',
          'Hum 4 hafte ka free pilot kar rahe hain. Kya aap interest letter de sakte hain? Ye koi payment commitment nahi hai."']:
    yy=wrap(c,t,M+12,yy,W-2*M-24,size=10,lead=14); yy-=2
y-=124
c.setFont('PB',12); c.setFillColor(INK); c.drawString(M,y,'Rules'); y-=16
for t in ['Only write what they actually said. Never add or improve quotes.',
          'Ask before recording or quoting anyone. First name only is fine.',
          'Note the shop name and area: "a service centre in Jayanagar" is strong proof for the jury.']:
    y=wrap(c,'•  '+t,M,y,W-2*M,size=10); y-=2
footer(c,'Page 1 of 3 · Keep answers honest')
c.showPage()

# Page 2: questions
header(c,'Technician interview (one page per technician)','Print 3 copies. Write answers in their words.')
y=H-96
c.setFont('P',10); c.setFillColor(INK)
for lab in ['Technician name (or first name):','Shop / company and area:','Years of experience:            Appliances they repair:']:
    c.drawString(M,y,lab); c.setStrokeColor(LINE); c.line(M+c.stringWidth(lab,'P',10)+6,y-2,W-M,y-2); y-=22
y-=6
qs=['How often do you get a fault you are not sure about? What do you do then? (Kitni baar aisa fault aata hai jo samajh nahi aata? Tab kya karte ho?)',
    'After trying FixSaathi: was the guidance correct? Would you use it on a real job? (Kya guidance sahi thi? Asli kaam pe use karoge?)',
    'Would your company pay ₹299–499 per technician per month? Would you pay ₹99 yourself? (Company ₹299–499 degi? Aap khud ₹99 doge?)',
    'What was missing or wrong? (Kya kami thi ya galat tha?)',
    'Can we quote you? Name or first name only? Video OK? (Kya hum aapka naam aur baat use kar sakte hain?)']
for i,q in enumerate(qs,1):
    y=wrap(c,f'{i}. {q}',M,y,W-2*M,font='PM',size=10,lead=14); y-=4
    y=lines(c,y,4 if i<5 else 2); y-=10
c.setFont('PB',10); c.drawString(M,y,'Trial result:'); c.setFont('P',10)
c.drawString(M+80,y,'Appliance: __________________   Fault: __________________'); y-=18
c.drawString(M+80,y,'Guidance correct?   Yes / No          Safety step clear?   Yes / No')
footer(c,'Page 2 of 3')
c.showPage()

# Page 3: letter of interest
header(c,'Letter of interest: pilot','For the owner or manager to sign. Not a purchase commitment.')
y=H-110
c.setFont('P',10.5); c.setFillColor(INK)
c.drawString(M,y,'Date: ____________________'); y-=34
c.setFont('PB',13); c.drawString(M,y,'To: Tensor Trailblazers (FixSaathi), BMS College of Engineering, Bengaluru'); y-=30
c.setFont('PB',12); c.drawString(M,y,'Subject: Interest in piloting FixSaathi'); y-=26
txt=('We, ______________________________________ (business name), located at ______________________________, Bengaluru, '
     'employ / work with ______ technicians who repair ACs, home appliances and/or electrical systems. '
     'We have seen a demonstration of FixSaathi, an AI repair copilot that guides technicians live through the phone camera and voice, '
     'enforces safety checks and generates service reports. '
     'We are interested in piloting FixSaathi with ______ of our technicians for about 4 weeks, to measure the first-time-fix rate and the number of repeat visits. '
     'This letter expresses interest only and is not a commitment to purchase.')
c.setFont('P',11)
y=wrap(c,txt,M,y,W-2*M,size=11,lead=22)
y-=30
for lab in ['Name:','Role / designation:','Phone:','Signature and stamp:']:
    c.setFont('P',11); c.drawString(M,y,lab); c.setStrokeColor(LINE); c.line(M+130,y-2,W-M,y-2); y-=36
y-=10
c.setFillColor(BG); c.roundRect(M,y-62,W-2*M,62,8,fill=1,stroke=0)
c.setFillColor(INK); c.setFont('PB',10); c.drawString(M+12,y-20,'WhatsApp is fine too.')
wrap(c,'If they prefer, ask the owner to send this paragraph on WhatsApp from the business number, with their name and role. Screenshot it for the deck.',M+12,y-36,W-2*M-24,size=9.5,lead=13)
footer(c,'Page 3 of 3 · Print 2–3 copies')
c.save()
print('ok')
