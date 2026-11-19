import sys
sys.path.insert(0,'/home/claude/r2')
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
F='/usr/share/fonts/truetype/google-fonts/'
for n,f in [('P','Poppins-Regular.ttf'),('PB','Poppins-Bold.ttf'),('PM','Poppins-Medium.ttf')]:
    pdfmetrics.registerFont(TTFont(n,F+f))
W,H=A4; M=34
BLUE=HexColor('#1a73e8'); INK=HexColor('#202124'); GREY=HexColor('#5f6368'); LINE=HexColor('#dadce0')
COL={'b':HexColor('#4285f4'),'r':HexColor('#ea4335'),'y':HexColor('#fbbc04'),'g':HexColor('#34a853')}
TINT={'b':HexColor('#e8f0fe'),'r':HexColor('#fce8e6'),'y':HexColor('#fef7e0'),'g':HexColor('#e6f4ea')}

def wrap(c,text,x,y,w,font='P',size=9,lead=12.5,color=INK):
    c.setFont(font,size); c.setFillColor(color); line=''
    for wd in text.split():
        t=(line+' '+wd).strip()
        if c.stringWidth(t,font,size)>w: c.drawString(x,y,line); y-=lead; line=wd
        else: line=t
    if line: c.drawString(x,y,line); y-=lead
    return y

def box(c,x,y,w,h,k,title,items):
    c.setFillColor(TINT[k]); c.roundRect(x,y-h,w,h,8,fill=1,stroke=0)
    c.setFillColor(COL[k]); c.rect(x,y-4,w,4,fill=1,stroke=0)
    yy=y-20; c.setFont('PB',11); c.setFillColor(INK); c.drawString(x+12,yy,title); yy-=16
    for it in items:
        if isinstance(it,tuple):
            yy=wrap(c,it[0],x+12,yy,w-24,font='PM',size=9); yy=wrap(c,it[1],x+12,yy,w-24,size=8.6,color=GREY,lead=11.5); yy-=3
        else:
            yy=wrap(c,(it if it[:2] in ('1.','2.','3.','4.','5.','6.') else '•  '+it),x+12,yy,w-24,size=8.8,lead=12); yy-=1.5
    return yy

c=canvas.Canvas('/home/claude/fixsathi/round2/FixSaathi_One_Pager.pdf',pagesize=A4)
c.setTitle('FixSaathi: one-page summary')
# Header
c.setFillColor(white); c.rect(0,0,W,H,fill=1,stroke=0)
x=M
for k in 'brygb'[:4]: c.setFillColor(COL[k]); c.rect(x,H-12,(W-2*M)/4,5,fill=1,stroke=0); x+=(W-2*M)/4
c.setFont('PB',26); c.setFillColor(INK); c.drawString(M,H-50,'FixSaathi')
c.setFont('PM',11.5); c.setFillColor(BLUE); c.drawString(M,H-68,'A senior technician in every technician\'s pocket')
c.setFont('P',9); c.setFillColor(GREY); c.drawRightString(W-M,H-44,'Tensor Trailblazers · BMSCE Bengaluru')
c.drawRightString(W-M,H-57,'Google Startup Buildathon India 2026')
c.drawRightString(W-M,H-70,'Bengaluru City Buildathon')
y=H-88
y=wrap(c,'FixSaathi is a real-time AI repair copilot built on Gemini Live. It sees the machine through the technician\'s phone camera, talks them through the repair hands-free in Hinglish, Kannada, Tamil or English, never unlocks a risky step until power is safely off, and sends an automatic service report to the manager.',M,y,W-2*M,font='P',size=10,lead=14)
y-=8
cw=(W-2*M-12)/2
top=y
box(c,M,top,cw,172,'r','The problem',[
 'Room AC sales hit a record 12.5–13 million units in FY2025 (ICRA); 50 lakh+ homes added rooftop solar (PM Surya Ghar).',
 'India will need about 2 million skilled AC technicians by 2036-37, up from 0.37 million in 2022-23 (CEEW).',
 'Only about 1 in 4 informal AC technicians has formal training (CEEW). Unfamiliar faults mean guesses, wasted parts and repeat visits.'])
box(c,M+cw+12,top,cw,172,'b','How it works',[
 '1. See: Gemini Live identifies the appliance and reads the label.',
 '2. Listen: the technician describes the fault by voice.',
 '3. Safety first: steps stay locked until power-off and a tester check are confirmed (enforced in code).',
 '4. Diagnose and mark: ranked causes; the suspect part is boxed on screen.',
 '5. Guide: one spoken step at a time, with Nano Banana picture cards.',
 '6. Report: automatic service report and live manager dashboard.'])
y=top-184
box(c,M,y,cw,192,'y','Built on Google AI and Cloud',[
 ('Gemini Live API','Real-time camera + voice, function calling into our agents.'),
 ('Gemini API agents','Diagnosis, part locator and report agents with structured JSON output.'),
 ('Nano Banana','Visual step cards from the real camera frame.'),
 ('Google Cloud','Cloud Run (Mumbai), Firestore, Secret Manager, Cloud Build.'),
 ('Built with','Google AI Studio and Google Antigravity.')])
box(c,M+cw+12,y,cw,192,'g','Business model',[
 ('Service centres and repair companies','About ₹299–499 per technician per month. Saving one repeat visit a month pays for it.'),
 ('Brands (AC, appliance, solar)','Fault analytics by model and region; brand repair guides.'),
 ('Independent technicians','Freemium, then a low monthly fee.'),
 ('Moat','Every guided repair adds verified fault-to-fix data by brand, model and region.')])
y=y-204
box(c,M,y,cw,128,'b','Validation so far',[
 'Real appliance photos tested on Gemini: it read brands and specs from labels and spotted loose fan wiring and a damp, cracked ceiling on its own.',
 'Jitendra, an AC and appliance technician in Mumbai, reviewed the guidance and added safety knowledge (reversed wiring in old homes).',
 'Working MVP measures AI cost per repair, reply time and technician-rated accuracy on every job.'])
box(c,M+cw+12,y,cw,128,'r','Next 3 months',[
 'Pilot with 2 Bengaluru service centres, about 20 technicians.',
 'Measure first-time-fix rate and repeat visits against a baseline.',
 'Grow the knowledge base to the top 20 faults; add Gemma offline mode.'])
y=y-140
# Team
c.setStrokeColor(LINE); c.line(M,y,W-M,y); y-=16
c.setFont('PB',11); c.setFillColor(INK); c.drawString(M,y,'Team'); y-=15
y=wrap(c,'Prerana P Jois, Co-founder & CEO (product, backend, cloud): ex-Software Developer Intern (AI/ML) at Robomanthan; FastAPI, Firestore, GCP. linkedin.com/in/prerana-p-jois-38b883290',M,y,W-2*M,size=8.8,lead=12)
y=wrap(c,'Priyam Thakur, Co-founder & CTO (AI & engineering): built NutriSense AI (Gemini SaaS) and VisionGuard AI (real-time vision); Oracle Certified Agentic AI. linkedin.com/in/priyamthakur275',M,y,W-2*M,size=8.8,lead=12)
y=wrap(c,'Final-year B.E. CSE, BMS College of Engineering, Bengaluru. Building AI products together for over a year (ScamGuard, Kairon AI).',M,y,W-2*M,size=8.8,lead=12,color=GREY)
c.setFont('P',7.5); c.setFillColor(GREY)
c.drawString(M,22,'Sources: ICRA (room AC sales FY2025), CEEW (RAC technician demand and training), MNRE / PM Surya Ghar (rooftop solar installations).')
c.save(); print('ok')
