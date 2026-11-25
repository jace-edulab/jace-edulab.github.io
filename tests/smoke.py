"""JACE 화면 회귀 시험 (배포 전 확인용).

새 기능을 넣은 뒤 기존 흐름(목록·찾기·자료 창·가입·올리기·고치기·회원 공간·운영진)이
그대로 도는지 실제 브라우저(크롬)로 돌려 본다. 서버와 파이어베이스는 가짜로 바꿔 끼운다.

  sh tests/run.sh full            # 코드 검사 + 이 화면 시험. 실패가 하나라도 있으면 끝에 FAIL 과 함께 종료 코드 1
"""
import asyncio, json, re, sys, pathlib
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "index.html").read_text(encoding="utf-8")
TMP = ROOT / "tests" / "_smoke.html"

CFG = {"grades": ["초등학교", "중학교", "고등학교", "공통"],
       "areas": [{"n": "체육", "s": []}, {"n": "보건", "s": []}, {"n": "국어", "s": []}, {"n": "정보", "s": []}],
       "types": ["프로그램", "수업 사례", "수업 자료", "활동지", "영상", "평가 자료"], "bookTitle": "시험 자료집"}
ITEMS = [
    {"id": "p1", "t": "티니클링 수업 사례", "d": "표현 활동 사례", "g": ["초등학교"], "a": ["체육"], "ty": "수업 사례", "m": True,
     "by": "시험교사", "sc": "햇살초등학교", "dt": "2026-11-08", "v": 1, "hasFile": True, "fname": "a.pdf"},
    {"id": "p2", "t": "전략형 게임 지도안", "d": "지도안", "g": ["중학교"], "a": ["체육", "정보"], "ty": "수업 자료", "m": False,
     "by": "시험교사", "sc": "햇살초등학교", "dt": "2026-10-01", "v": 3, "hasFile": False,
     "link": "영상 | https://youtu.be/x\n긴 주소 | https://docs.google.com/spreadsheets/d/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/copy"},
    {"id": "p3", "t": "AI 판정 줄넘기 '점퍼스'", "d": "카메라 판정", "g": ["공통"], "a": ["체육", "정보"], "th": "data:image/gif;base64,R0lGODlhAQABAAAAACw=",
     "ty": "프로그램", "m": False, "by": "시험교사", "sc": "햇살초등학교", "dt": "2026-11-07", "v": 5, "hasFile": True, "fname": "z.zip",
     "link": "점퍼스 | https://example.org/jumpers"},
    {"id": "p4", "t": "여러 파일 자료", "d": "파일 두 개", "g": ["공통"], "a": ["보건"], "ty": "활동지", "m": False,
     "by": "시험교사", "sc": "햇살초등학교", "dt": "2026-11-18", "v": 0, "hasFile": True, "fname": "가.pdf",
     "files": ["가.pdf", "나.hwpx"], "urls": ["https://drive.google.com/file/d/A/view", "https://drive.google.com/file/d/B/view"]},
]
PUBLIC = {"ok": True, "config": CFG, "items": [{k: v for k, v in i.items() if not (i["m"] and k == "link")} for i in ITEMS]}
ME_ADMIN = {"email": "t@x.kr", "name": "시험교사", "school": "햇살초등학교", "status": "승인", "admin": True, "member": True,
            "hasPhone": True, "hasPos": True, "pos": "교사"}
MD = {"ok": True, "items": [dict(i, canEdit=True, own=True) for i in ITEMS],
      "schedules": [{"id": "s1", "d": "2026-11-04", "t": "11월 자율연수", "p": "체육관", "tm": "16:00", "x": "", "att": ["t@x.kr"], "big": False}],
      "notices": [{"id": "n1", "t": "공지 시험", "x": "내용", "by": "시험교사", "dt": "2026-11-01", "pin": True, "cm": []}],
      "book": {}, "members": []}
AD = {"ok": True, "sheetUrl": "#", "members": [
    {"email": "t@x.kr", "n": "시험교사", "sc": "햇살초등학교", "dt": "2026-11-01", "s": "승인", "role": "운영진", "book": True, "reg": True, "phone": "010-1111-2222", "pos": "교사"},
    {"email": "w@x.kr", "n": "대기교사", "sc": "달빛초등학교", "dt": "2026-11-10", "s": "대기", "role": "회원", "book": False, "reg": True, "phone": "010-3333-4444", "pos": "교감"}],
    "log": []}



B64 = "JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgKHB5cGRmKQo+PgplbmRvYmoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDIKL0tpZHMgWyA0IDAgUiA1IDAgUiBdCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUmVzb3VyY2VzIDw8Cj4+Ci9NZWRpYUJveCBbIDAuMCAwLjAgNTk1IDg0MiBdCi9QYXJlbnQgMiAwIFIKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1Jlc291cmNlcyA8PAo+PgovTWVkaWFCb3ggWyAwLjAgMC4wIDU5NSA4NDIgXQovUGFyZW50IDIgMCBSCj4+CmVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMDA1NCAwMDAwMCBuIAowMDAwMDAwMTE5IDAwMDAwIG4gCjAwMDAwMDAxNjggMDAwMDAgbiAKMDAwMDAwMDI2MiAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDYKL1Jvb3QgMyAwIFIKL0luZm8gMSAwIFIKPj4Kc3RhcnR4cmVmCjM1NgolJUVPRgo="
REP = {"uid": "rep", "email": "jace.edulab@gmail.com"}
RT0 = {"usedSc": {"p3": {"u1": "해초", "u2": "달초", "u3": "해초"}},
       "used": {"p3": {"u1": {"n": "다교사", "sc": "해초", "g": "초등학교", "a": "5학년 체육", "x": "줄넘기 시간에 잘 썼어요", "t": 1790000000000}}},
       "ideas": {"i1": {"uid": "zz", "n": "손님교사", "x": "모둠 차례 타이머가 있으면 좋겠어요", "g": "초등학교", "a": "체육", "t": 1790000000000},
                 "i2": {"uid": "zz", "n": "손님교사", "x": "완성된 도구 아이디어 예시", "t": 1780000000000, "claim": {"uid": "m1", "n": "가교사", "t": 1}, "done": {"id": "p3", "t": 2}}},
       "ideaLikes": {"i1": {"zz": True}}}
DB0 = {**RT0, "members": {
  "m1": {"name": "가교사", "school": "달빛중학교", "level": "중학교", "pos": "교사", "subject": "체육", "phone": "010-1111-2222", "others": "없음", "status": "승인", "role": "회원", "email": "m1@x.kr", "t": 1},
  "w1": {"name": "나교사", "school": "별초등학교", "level": "초등학교", "pos": "교감", "subject": "초등교과전반", "phone": "010-3333-4444", "others": "2개 이상", "status": "대기", "email": "w1@x.kr", "t": 2},
  "jn": {"name": "남도교사", "school": "남도중학교", "level": "중학교", "pos": "교사", "subject": "체육", "phone": "010-7777-8888", "others": "없음", "status": "승인", "role": "회원", "email": "jn@x.kr", "sido": "전라남도", "t": 3},
  "bs": {"name": "박회장", "school": "봄초등학교", "level": "초등학교", "pos": "교사", "subject": "초등교과전반", "phone": "010-5555-6666", "others": "없음", "status": "승인", "email": "boss@x.kr", "t": 0}}}


def build(user, db=None, api=True):
    stub = f"""<script>
window.JACE_FIREBASE={{apiKey:"k",authDomain:"a",databaseURL:"",projectId:"p",appId:"x"}};
window.JACE_API_URL={json.dumps("https://api.invalid/exec" if api else "")};window.JACE_ADMINS=["jace.edulab@gmail.com"];window.JACE_MANAGERS=["boss@x.kr"];
window.__RT_TEST=true;window.__NORECRUIT=true;window.__NOCONFIRM=true;window.__CALLS=[];window.__DB={json.dumps(db or {}, ensure_ascii=False)};
let __U={json.dumps(user)};if(__U)__U.getIdToken=async()=>"tok";let __cb=null;
const __A={{get currentUser(){{return __U}},setPersistence(){{return Promise.resolve()}},onAuthStateChanged(cb){{__cb=cb;setTimeout(()=>cb(__U),20)}},signInWithPopup(){{__U={{uid:"new",email:"new@x.kr",displayName:"새교사",getIdToken:async()=>"tok"}};setTimeout(()=>__cb(__U),10);return Promise.resolve()}},signOut(){{__U=null;setTimeout(()=>__cb(null),10);return Promise.resolve()}}}};
function __get(p){{return p.split("/").reduce((o,k)=>o==null?undefined:o[k],window.__DB)}}
function __set(p,v){{const ks=p.split("/");let o=window.__DB;ks.slice(0,-1).forEach(k=>{{o[k]=o[k]||{{}};o=o[k]}});o[ks[ks.length-1]]=v}}
const __ref=p=>({{get:async()=>({{val:()=>{{const v=__get(p);return v===undefined?null:JSON.parse(JSON.stringify(v))}}}}),set:async v=>__set(p,JSON.parse(JSON.stringify(v))),on(){{}},off(){{}},remove:async()=>{{}},update:async()=>{{}},orderByChild(){{return this}},limitToLast(){{return this}},push:async()=>{{}},onDisconnect(){{return{{update:async()=>{{}},remove:async()=>{{}}}}}}}});
window.firebase={{initializeApp(){{}},auth:Object.assign(()=>__A,{{Auth:{{Persistence:{{LOCAL:1}}}},GoogleAuthProvider:function(){{}}}}),database:Object.assign(()=>({{ref:__ref}}),{{ServerValue:{{TIMESTAMP:0}}}})}};
const __R={{upload:{{ok:true,id:"new1"}},addFile:{{ok:true,n:2}},updateItem:{{ok:true}},getFile:{{ok:true,name:"시험.pdf",mime:"application/pdf",b64:"{B64}"}},public:{json.dumps(PUBLIC, ensure_ascii=False)},memberData:{json.dumps(MD, ensure_ascii=False)},adminData:{{ok:true,log:[{{at:"2026-11-19 10:00",n:"가교사",t:"점퍼스"}}],sheetUrl:"#"}}}};
window.fetch=async(url,opt)=>{{let b={{ok:true}};
 if(String(url).includes("public")) b=__R.public;
 else if(opt&&opt.body){{const q=JSON.parse(opt.body);window.__CALLS.push(q);b=__R[q.action]||{{ok:true}};}}
 return new Response(JSON.stringify(b),{{status:200,headers:{{"Content-Type":"application/json"}}}});}};
</script>"""
    s = re.sub(r'<script src="https://www\.gstatic\.com[^"]*"></script>\n', "", SRC).replace('<script src="config.js"></script>', stub)
    s = s.replace('sc.src = "vendor/qrcode.js"', f'sc.src = "{(ROOT / "vendor" / "qrcode.js").as_uri()}"')
    s = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^"]*">', "", s)
    TMP.write_text(s, encoding="utf-8")
    return TMP.as_uri()


RESULTS = []
def check(name, ok, info=""):
    RESULTS.append((name, bool(ok), info))


async def route_pdflib(pg):
    js = (ROOT / "tests" / "vendor" / "pdf-lib.min.js").read_text(encoding="utf-8")
    await pg.route("**/pdf-lib.min.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=js))
    await pg.route("**/html2canvas*", lambda r: r.fulfill(status=200, content_type="application/javascript", body=""))


async def newpage(b, width, user, db=None, api=True, hash=""):
    pg = await b.new_page(viewport={"width": width, "height": 900}); pg.set_default_timeout(5000); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await route_pdflib(pg)
    await pg.goto(build(user, db, api) + hash); await pg.wait_for_timeout(900)
    return pg, errs


async def guest(b, width):
    tag = "휴대폰" if width < 500 else "PC"
    pg, errs = await newpage(b, width, None, db=json.loads(json.dumps(RT0)))
    check(f"{tag} 첫 화면은 JACE 소개(매거진 표지)", await pg.locator(".mz-cover").count() == 1 and "창간 준비호" in await pg.inner_text(".mz-issue"))
    check(f"{tag} 소개 차례 4꼭지", await pg.locator(".mz-toc li").count() == 4 and all([await pg.locator(f"#a0{i}").count() == 1 for i in range(1, 5)]))
    for txt in ["교과별 실천 연구", "기록하고 쌓는 도구", "월 1회 모임", "창립 회원을 모집합니다"]:
        check(f"{tag} 소개 글: {txt}", await pg.locator("main", has_text=txt).count() == 1)
    await pg.evaluate("go('public');render()"); await pg.wait_for_timeout(200)
    check(f"{tag} 자료실 카드 4개", await pg.locator(".card.app").count() == 4)
    check(f"{tag} 썸네일 있는 카드와 색 카드", await pg.locator(".card.app .thumb.ph").count() == 3 and await pg.locator(".card.app .thumb:not(.ph)").count() == 1)
    check(f"{tag} 프로그램 카드에 바로 열기", await pg.locator(".card.app", has_text="점퍼스").locator(".openbtn", has_text="바로 열기").count() == 1)
    check(f"{tag} 회원만 자료는 바로 열기 없음", await pg.locator(".card.app", has_text="티니클링").locator(".openbtn").count() == 0)
    check(f"{tag} 자료실: 이번 달 도구 큰 칸", await pg.locator(".mz-feat").count() == 1 and await pg.locator(".mz-h1").count() == 1)
    check(f"{tag} 자료실: 작업대 숫자 4칸", await pg.locator(".mz-bench .mz-cell").count() == 4)
    pb = pg.locator(".mz-pager button")
    if await pb.count() >= 2:
        await pb.nth(1).click(); await pg.wait_for_timeout(120)
        check(f"{tag} 자료실: 숫자 단추로 도구 바꾸기", await pg.evaluate("FEATI") == 1 and await pg.locator(".mz-pager button.on").count() == 1)
    check(f"{tag} 자료실: 추천이 없으면 아이디어함 칸", await pg.locator(".mz-side .mz-wait").count() == 1)
    check(f"{tag} 바닥글: PC 안내", "PC에 맞춰" in await pg.inner_text("footer"))
    check(f"{tag} 앱 설치: 설치 창 이벤트 전에는 단추 숨김", await pg.locator("#instBtn").is_hidden())
    await pg.evaluate("() => { const e = new Event('beforeinstallprompt'); e.prompt = () => { window.__P = 1; }; e.userChoice = Promise.resolve({}); window.dispatchEvent(e); }"); await pg.wait_for_timeout(80)
    check(f"{tag} 앱 설치: 단추가 나타남", await pg.locator("#instBtn").is_visible())
    await pg.click("#instBtn"); await pg.wait_for_timeout(120)
    check(f"{tag} 앱 설치: 설치 창 띄움", await pg.evaluate("window.__P") == 1 and await pg.locator("#instBtn").is_hidden())
    await pg.select_option("#fty", "프로그램"); await pg.wait_for_timeout(150)
    check(f"{tag} 자료 종류 고르기", await pg.locator(".card.app").count() == 1)
    await pg.select_option("#fty", ""); await pg.wait_for_timeout(150)
    await pg.locator(".mz-seg").get_by_role("button", name="중학교", exact=True).click(); await pg.wait_for_timeout(150)
    check(f"{tag} 학교급 고르기", await pg.locator(".card.app").count() == 1)
    await pg.locator(".mz-seg").get_by_role("button", name="전체", exact=True).click(); await pg.wait_for_timeout(150)
    await pg.fill("#q", "티니클링"); await pg.wait_for_timeout(300)
    check(f"{tag} 검색", await pg.locator(".card.app").count() == 1)
    await pg.fill("#q", ""); await pg.wait_for_timeout(300)
    await pg.evaluate("openItem('p2')"); await pg.wait_for_timeout(400)
    check(f"{tag} 자료 창 링크 2줄", await pg.locator("#ov .file").count() == 2)
    check(f"{tag} 자료 창 QR", await pg.locator("#qrBox canvas").count() == 1)
    await pg.evaluate("closeM();openItem('p3')"); await pg.wait_for_timeout(200)
    check(f"{tag} 자료 창 썸네일", await pg.locator("#ov .mthumb").count() == 1)
    await pg.evaluate("closeM();openItem('p1')"); await pg.wait_for_timeout(200)
    check(f"{tag} 회원만 자료 잠김", await pg.locator("#ov", has_text="회원만 내려받기").count() == 1)
    check(f"{tag} 카드에 '2개 학교 사용'", "2개 학교 사용" in await pg.locator(".card.app", has_text="점퍼스").inner_text())
    await pg.evaluate("closeM();openItem('p3')"); await pg.wait_for_timeout(300)
    ub = await pg.inner_text("#usedBox")
    check(f"{tag} 손님: 써 봤어요는 학교 수만", "2개 학교" in ub and "다교사" not in ub, ub)
    await pg.evaluate("closeM();location.hash='#ideas'"); await pg.wait_for_timeout(300)
    check(f"{tag} 아이디어함 2개", await pg.locator(".idea").count() == 2 and await pg.locator(".idea.done").count() == 1)
    check(f"{tag} 아이디어함: 손님은 맡기 단추 없음", await pg.get_by_role("button", name="제가 만들어 볼게요").count() == 0)
    check(f"{tag} 완성 아이디어에 도구 보기", await pg.locator(".idea.done").get_by_role("button", name="완성된 도구 보기").count() == 1)
    await pg.evaluate("closeM()")
    hb = pg.locator("nav .hlp-btn")
    na = await pg.locator("nav a[data-v=about]").bounding_box(); hbb = await hb.bounding_box()
    check(f"{tag} 사용 안내 단추: 메뉴 줄 맨 끝·높이 44 이상", abs((hbb["y"] + hbb["height"] / 2) - (na["y"] + na["height"] / 2)) < 4 and hbb["height"] >= 44 and await pg.evaluate("document.querySelector('nav .nwrap').lastElementChild.classList.contains('hlp-btn')"), f"{na} {hbb}")
    await hb.click(); await pg.wait_for_timeout(150)
    check(f"{tag} 사용 안내 창: 제목과 8개 항목", await pg.locator("#ov.show h2", has_text="JACE 간략 사용법").count() == 1 and await pg.locator(".hlp-list > li").count() == 8)
    check(f"{tag} 사용 안내 창: 미리보기 링크", (await pg.get_attribute(".hlp a.btn", "href") or "").endswith("?demo"))
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(100)
    check(f"{tag} 사용 안내 창: Esc로 닫힘", await pg.locator("#ov.show").count() == 0)
    await pg.evaluate("location.hash='#guide'"); await pg.wait_for_timeout(250)
    check(f"{tag} 옛 #guide 주소도 사용 안내 창", await pg.locator("#ov.show .hlp").count() == 1)
    await pg.get_by_role("button", name="확인").click(); await pg.wait_for_timeout(100)
    check(f"{tag} 사용 안내 창: 확인으로 닫힘", await pg.locator("#ov.show").count() == 0)
    await pg.evaluate("location.hash='#members'"); await pg.wait_for_timeout(200)
    check(f"{tag} 회원 공간은 잠김", await pg.locator(".gate").count() == 1)
    w = await pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    check(f"{tag} 가로 넘침 없음", w)
    await pg.evaluate("closeM();localStorage.removeItem('jace_recruit_hide');window.__NORECRUIT=false;recruitCheck()"); await pg.wait_for_timeout(150)
    check(f"{tag} 창립 회원 모집 팝업", await pg.locator("#ov.show .recruit").count() == 1)
    await pg.locator(".recruit").get_by_role("button", name="닫기").click(); await pg.wait_for_timeout(100)
    await pg.evaluate("recruitCheck()"); await pg.wait_for_timeout(100)
    check(f"{tag} 그냥 닫으면 다시 뜸", await pg.locator("#ov.show .recruit").count() == 1)
    await pg.check("#rhide"); await pg.locator(".recruit").get_by_role("button", name="닫기").click(); await pg.wait_for_timeout(100)
    await pg.evaluate("recruitCheck()"); await pg.wait_for_timeout(100)
    check(f"{tag} 오늘 하루 열지 않기", await pg.locator("#ov.show").count() == 0)
    check(f"{tag} 손님 오류 없음", not errs, "; ".join(errs)); await pg.close()


async def join_flow(b, width):
    tag = "휴대폰" if width < 500 else "PC"
    pg, errs = await newpage(b, width, None, db=json.loads(json.dumps(DB0)))
    await pg.locator("#hright").get_by_role("button", name="가입 신청").click(); await pg.wait_for_timeout(300)
    check(f"{tag} 가입: 로그인 뒤 신청서", await pg.locator("#jn").count() == 1 and await pg.input_value("#jn") == "새교사")
    await pg.locator("#jp").press_sequentially("010-1234 5678")
    check(f"{tag} 가입: 휴대전화 숫자만", await pg.input_value("#jp") == "01012345678")
    await pg.fill("#js", "햇살초등학교"); await pg.select_option("#jl", "초등학교"); await pg.select_option("#jpos", "교사")
    check(f"{tag} 가입: 교과 고르기 목록", await pg.locator("#jsub option").count() > 5 and not await pg.locator("#jsubx").is_visible())
    await pg.select_option("#jsub", "기타 (직접 입력)"); await pg.wait_for_timeout(50)
    check(f"{tag} 가입: 기타를 고르면 입력칸", await pg.locator("#jsubx").is_visible())
    await pg.fill("#jsubx", "중등체육 및 운동부"); await pg.select_option("#jsub", "체육")
    check(f"{tag} 가입: 다른 걸 고르면 입력칸 숨김", not await pg.locator("#jsubx").is_visible())
    await pg.select_option("#jsub", "기타 (직접 입력)"); await pg.fill("#jsubx", "초등교과전반 및 영재"); await pg.select_option("#jo", "1개"); await pg.check("#jelig"); await pg.check("#jpriv")
    await pg.get_by_role("button", name="신청서 보내기").click()
    check(f"{tag} 가입: 명단 동의 없으면 막힘", "명단 제출" in await pg.inner_text("#jerr"))
    await pg.check("#jreg"); await pg.get_by_role("button", name="신청서 보내기").click()
    check(f"{tag} 가입: 이용 약속 없으면 막힘", "약속" in await pg.inner_text("#jerr"))
    await pg.check("#jc"); await pg.get_by_role("button", name="신청서 보내기").click(); await pg.wait_for_timeout(300)
    sv = await pg.evaluate("window.__DB.members.new")
    check(f"{tag} 가입: 저장", sv and sv["status"] == "대기" and sv["phone"] == "010-1234-5678" and sv["book"] is True and sv["subject"] == "초등교과전반 및 영재", json.dumps(sv, ensure_ascii=False))
    check(f"{tag} 가입: 승인 대기 표시", "승인 대기 중" in await pg.inner_text("#hright"))
    check(f"{tag} 가입: 운영진 관리 메뉴 없음", await pg.locator("#navAdmin").is_hidden())
    check(f"{tag} 가입 흐름 오류 없음", not errs, "; ".join(errs)); await pg.close()


async def member(b, width):
    tag = "휴대폰" if width < 500 else "PC"
    db = json.loads(json.dumps(DB0))
    pg, errs = await newpage(b, width, {"uid": "m1", "email": "m1@x.kr"}, db=db)
    check(f"{tag} 회원: 머리말 이름·역할", "가교사 선생님" in await pg.inner_text("#hright") and "자료 올리기" in await pg.inner_text("#hright"))
    check(f"{tag} 회원: 대화용 people 기록", await pg.evaluate("JSON.stringify(window.__DB.people && window.__DB.people.m1)") == json.dumps({"n": "가교사", "sc": "달빛중학교", "admin": False, "book": True}, separators=(",", ":"), ensure_ascii=False))
    check(f"{tag} 회원: 운영진 메뉴 없음", await pg.locator("#navAdmin").is_hidden())
    await pg.evaluate("go('public');render()"); await pg.wait_for_timeout(200)
    check(f"{tag} 회원: 회원만 자료도 바로 열기 칸 판단", await pg.locator(".card.app").count() == 4)
    for k in ["chat", "meet", "cal", "review", "notice", "book"]:
        await pg.evaluate(f"go('members');msub='{k}';msubPicked=true;render()"); await pg.wait_for_timeout(150)
        check(f"{tag} 회원 공간 '{k}' 탭", await pg.locator(".subtabs").count() == 1 and await pg.locator(".gate").count() == 0)
    check(f"{tag} 회원 공간 탭은 6개", await pg.locator(".subtabs button:not(.tabedit)").count() == 6)
    await pg.evaluate("go('members');msub='cal';render();openEv('s1')"); await pg.wait_for_timeout(150)
    check(f"{tag} 일정 창", await pg.locator("#ov", has_text="참석").count() >= 1)
    await pg.evaluate("closeM();go('about');render();SEEN={pub:['p1'],ideas:1,mem:[]};navBadges()"); await pg.wait_for_timeout(100)
    nb = await pg.evaluate("['public','ideas','members'].map(k => (document.querySelector(`nav a[data-v=${k}] .cnt`) || {}).textContent || '')")
    check(f"{tag} 새 소식 숫자: 자료실·아이디어함·회원 공간", nb[0] == "3" and nb[1] == "2" and nb[2] not in ("", "0"), str(nb))
    await pg.evaluate("go('public');render()"); await pg.wait_for_timeout(100)
    check(f"{tag} 새 소식 숫자: 열어 보면 사라짐", await pg.locator('nav a[data-v=public] .cnt').count() == 0 and await pg.evaluate("window.__DB.seen && window.__DB.seen.m1 && window.__DB.seen.m1.pub.length") == 4)
    await pg.evaluate("closeM();go('public');render();openItem('p3')"); await pg.wait_for_timeout(300)
    check(f"{tag} 회원: 써 봤어요 소감 보임", "줄넘기 시간에 잘 썼어요" in await pg.inner_text("#usedBox"))
    await pg.get_by_role("button", name="써 봤어요 남기기").click(); await pg.wait_for_timeout(150)
    await pg.fill("#usa", "1학년 체육"); await pg.fill("#usx", "수업에 잘 썼어요"); await pg.check("#usr")
    await pg.get_by_role("button", name="남기기", exact=True).click(); await pg.wait_for_timeout(400)
    u = await pg.evaluate("[window.__DB.used.p3.m1, window.__DB.usedSc.p3.m1]")
    check(f"{tag} 회원: 써 봤어요 저장", u[0] and u[0]["x"] == "수업에 잘 썼어요" and u[0]["sc"] == "달빛중학교" and u[1] == "달빛중학교", str(u))
    check(f"{tag} 회원: 추천 기록", await pg.evaluate("window.__DB.usedRec && window.__DB.usedRec.p3 && window.__DB.usedRec.p3.m1") == await pg.evaluate("TODAY.slice(0,7)"))
    check(f"{tag} 회원: 카드 3개 학교로 늘어남", "3개 학교 사용" in await pg.locator(".card.app", has_text="점퍼스").inner_text())
    await pg.evaluate("closeM();location.hash='#ideas'"); await pg.wait_for_timeout(300)
    await pg.locator(".idea", has_text="모둠 차례").locator(".like").click(); await pg.wait_for_timeout(200)
    check(f"{tag} 아이디어: 저도 필요해요", await pg.evaluate("window.__DB.ideaLikes.i1.m1") is True and "2" in await pg.locator(".idea", has_text="모둠 차례").locator(".like").inner_text())
    await pg.get_by_role("button", name="제가 만들어 볼게요").click(); await pg.wait_for_timeout(200)
    check(f"{tag} 아이디어: 맡기", await pg.evaluate("window.__DB.ideas.i1.claim && window.__DB.ideas.i1.claim.uid") == "m1" and await pg.locator(".idea", has_text="가교사 선생님이 만드는 중").count() >= 1)
    await pg.get_by_role("button", name="아이디어 남기기").click(); await pg.wait_for_timeout(200)
    await pg.fill("#idx", "학급 발표 순서 뽑기 도구"); await pg.get_by_role("button", name="남기기", exact=True).click(); await pg.wait_for_timeout(300)
    nw = await pg.evaluate("Object.values(window.__DB.ideas).filter(d => d && d.uid === 'm1')")
    check(f"{tag} 아이디어: 남기기", len(nw) == 1 and nw[0]["n"] == "가교사" and await pg.locator(".idea").count() == 3, str(nw))
    await pg.evaluate("closeM();go('members');msub='book';render()"); await pg.wait_for_timeout(150)
    check(f"{tag} 회원 공간: 오른쪽 칸(모임·공지·책자)", await pg.locator(".mz-mside .mz-ev").count() == 1 and await pg.locator(".mz-mside .mz-box").count() == 2)
    check(f"{tag} 책자 탭 원고 양식", await pg.locator(".msguide a[href$='ms-template.hwpx']").count() == 1)
    await pg.evaluate("closeM();localStorage.removeItem('jace_recruit_hide');window.__NORECRUIT=false;recruitCheck()"); await pg.wait_for_timeout(100)
    check(f"{tag} 회원에게는 모집 팝업 없음", await pg.locator("#ov.show").count() == 0)
    check(f"{tag} 회원 오류 없음", not errs, "; ".join(errs)); await pg.close()


async def rep_admin(b, width):
    tag = "휴대폰" if width < 500 else "PC"
    db = json.loads(json.dumps(DB0))
    pg, errs = await newpage(b, width, REP, db=db)
    check(f"{tag} 대표: 운영진 표시", "대표 계정" in await pg.inner_text("#hright") and await pg.locator("#navAdmin").is_visible())
    await pg.evaluate("pickA('join')"); await pg.wait_for_timeout(100)
    check(f"{tag} 대표: 가입 신청 단추 없음", await pg.get_by_role("button", name="가입 신청서 쓰기").count() == 0)
    # 썸네일 + 여러 파일 올리기
    await pg.evaluate("() => { window.__CALLS = []; openUpload(); }"); await pg.wait_for_timeout(200)
    png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x02\x00\x00\x00\xfd\xd4\x9as\x00\x00\x00\x16IDATx\x9cc\xf8\x0f\x04\x0c\x0c\x0c\x00\x00\x00\x02\x00\x01\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    await pg.set_input_files("#uth", [{"name": "t.png", "mimeType": "image/png", "buffer": png}]); await pg.wait_for_timeout(400)
    check(f"{tag} 썸네일 미리보기", "data:image/jpeg" in (await pg.get_attribute("#tprev", "style") or ""))
    await pg.set_input_files("#uf", [{"name": f"f{i}.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4 test"} for i in range(3)])
    await pg.fill("#ut", "새 자료"); await pg.fill("#uwhy", "기록 재기가 오래 걸려서"); await pg.fill("#uver", "v1.0"); await pg.locator("#ug .chip").first.click(); await pg.locator("#ua .chip").first.click()
    await pg.check("#c1"); await pg.check("#c2")
    await pg.evaluate("() => { sendUpload(); }"); await pg.wait_for_timeout(1500)
    wv = await pg.evaluate("(window.__CALLS.find(c => c.action === 'upload') || {}).item")
    check(f"{tag} 올리기: 왜 만들었나·판 번호", wv and wv.get("why") == "기록 재기가 오래 걸려서" and wv.get("ver") == "v1.0", str(wv))
    calls = await pg.evaluate("window.__CALLS.map(c => ({a: c.action, more: c.more, last: c.last, name: c.name, th: !!c.thumb}))")
    up = [c for c in calls if c["a"] == "upload"]; adds = [c for c in calls if c["a"] == "addFile"]
    check(f"{tag} 올리기(썸네일 + 파일 3개)", len(up) == 1 and up[0]["more"] == 2 and up[0]["th"] and len(adds) == 2 and adds[-1]["last"], str(calls)[:300])
    await pg.evaluate("() => { window.__CALLS = []; closeM(); openUpload('p4'); }"); await pg.wait_for_timeout(200)
    check(f"{tag} 고치기 창에 지금 파일 2개", await pg.locator(".curf .urm").count() == 2)
    await pg.locator(".curf .urm input").first.check()
    await pg.set_input_files("#uf", [{"name": "new.pdf", "mimeType": "application/pdf", "buffer": b"%PDF-1.4 x"}])
    await pg.check("#c1"); await pg.check("#c2")
    await pg.evaluate("() => { sendUpload(); }"); await pg.wait_for_timeout(1500)
    calls = await pg.evaluate("window.__CALLS.map(c => ({a: c.action, edit: c.edit && {rm: c.edit.removeIdx, add: c.edit.addCount}, name: c.name}))")
    upd = [c for c in calls if c["a"] == "updateItem"]; adds = [c for c in calls if c["a"] == "addFile"]
    check(f"{tag} 고치기: 파일 빼고 더하기", upd and upd[0]["edit"] == {"rm": [0], "add": 1} and len(adds) == 1, str(calls)[:200])
    await pg.evaluate("() => { closeM(); window.__saved = null; window.saveBlob = (bytes, name) => { window.__saved = { n: bytes.length, name }; }; }")
    await pg.evaluate("() => { getFile('p1'); }"); await pg.wait_for_timeout(2500)
    sv = await pg.evaluate("window.__saved")
    check(f"{tag} 회원 자료 내려받기", sv and sv["n"] > 700 and sv["name"].endswith(".pdf"), str(sv))
    # 운영진 관리
    await pg.evaluate("location.hash='#admin'"); await pg.wait_for_timeout(500)
    check(f"{tag} 운영진 화면에도 사용 안내 단추", await pg.locator("nav .hlp-btn").is_visible())
    check(f"{tag} 운영진: 명단 4줄(다른 시·도 표시 포함)", await pg.locator("table.adm tr").count() == 5 and "전남" in await pg.locator("table.adm tr", has_text="남도교사").inner_text())
    check(f"{tag} 운영진: 회장 맨 위", "박회장" in await pg.locator("table.adm tr >> nth=1").inner_text())
    check(f"{tag} 운영진: 3개 초과 경고", await pg.locator("td.warn").count() == 1)
    check(f"{tag} 운영진: 내려받기 기록", await pg.locator("main", has_text="점퍼스").count() >= 1)
    await pg.locator("table.adm tr", has_text="나교사").get_by_role("button", name="승인").click(); await pg.wait_for_timeout(200)
    check(f"{tag} 운영진: 승인 저장", await pg.evaluate("window.__DB.members.w1.status") == "승인")
    await pg.locator("table.adm tr", has_text="가교사").locator("select").select_option("총무"); await pg.wait_for_timeout(200)
    check(f"{tag} 운영진: 역할 저장", await pg.evaluate("window.__DB.members.m1.role") == "총무")
    await pg.locator("table.adm tr", has_text="남도교사").get_by_role("button", name="고치기").click(); await pg.wait_for_timeout(150)
    check(f"{tag} 회원 고치기 창: 지금 값이 들어 있음", await pg.input_value("#en") == "남도교사" and await pg.input_value("#esd") == "전라남도" and await pg.input_value("#ep") == "01077778888")
    await pg.fill("#es", ""); await pg.locator("#es").press_sequentially("햇살"); await pg.wait_for_timeout(700)
    await pg.locator("#esList button").nth(1).click(); await pg.wait_for_timeout(100)
    check(f"{tag} 회원 고치기: 학교 찾기로 채움", await pg.input_value("#es") == "햇살중학교" and await pg.input_value("#esd") == "전라남도" and await pg.input_value("#el") == "중학교")
    await pg.fill("#es", "남도여자중학교"); await pg.fill("#esub", "체육 및 스포츠클럽"); await pg.locator("#ov").get_by_role("button", name="저장", exact=True).click(); await pg.wait_for_timeout(250)
    ed = await pg.evaluate("window.__DB.members.jn")
    check(f"{tag} 회원 고치기 저장", ed["school"] == "남도여자중학교" and ed["subject"] == "체육 및 스포츠클럽" and ed["phone"] == "010-7777-8888" and ed["status"] == "승인" and "남도여자중학교" in await pg.locator("table.adm").inner_text(), str(ed))
    await pg.context.grant_permissions(["clipboard-read", "clipboard-write"])
    await pg.get_by_role("button", name="명단 복사 (승인 회원)").click(); await pg.wait_for_timeout(200)
    clip = await pg.evaluate("navigator.clipboard.readText()")
    check(f"{tag} 운영진: 명단 복사(전북만)", "남도교사" not in clip and clip.splitlines()[0] == "순\t역할\t소속\t직위\t성명\t교과" and clip.splitlines()[1].startswith("1\t회장\t") and len(clip.splitlines()) == 4, clip)
    await pg.evaluate("() => { window.__CALLS = []; openOwner('p2'); }"); await pg.wait_for_timeout(200)
    opts = await pg.locator("#own option").all_inner_texts()
    check(f"{tag} 올린이 바꾸기: 승인 회원 + 운영진만", any("박회장" in o for o in opts) and any("JACE 운영진" in o for o in opts) and not any("대기교사" in o for o in opts), str(opts))
    await pg.select_option("#own", label=[o for o in opts if "박회장" in o][0])
    await pg.evaluate("() => { sendOwner(); }"); await pg.wait_for_timeout(600)
    oc = await pg.evaluate("window.__CALLS.filter(c => c.action === 'setOwner')")
    check(f"{tag} 올린이 바꾸기 보냄", len(oc) == 1 and oc[0]["id"] == "p2" and oc[0]["email"] == "boss@x.kr" and oc[0]["name"] == "박회장" and oc[0]["school"] == "봄초등학교", str(oc))
    await pg.evaluate("() => { const v = JSON.parse(JSON.stringify(window.__DB.members)); onMembersSnap(v); v.z9 = {name: '다새로', school: '바다초등학교', status: '대기', t: 9}; onMembersSnap(v); }"); await pg.wait_for_timeout(120)
    check(f"{tag} 실시간 가입 알림", "다새로 선생님(바다초등학교)" in (await pg.inner_text("#liveAlert")) and (await pg.inner_text('nav a[data-v=admin] .cnt')) == str(await pg.evaluate("Object.values(ALL).filter(m => m && m.status === '대기').length")))
    await pg.locator("#liveAlert").get_by_role("button", name="확인하러 가기").click(); await pg.wait_for_timeout(150)
    check(f"{tag} 알림에서 운영진 관리로", await pg.evaluate("view") == "admin" and await pg.locator("#liveAlert").count() == 0)
    await pg.fill("#sbe", "초등교과전반\n체육\n영양"); await pg.get_by_role("button", name="저장", exact=True).click(); await pg.wait_for_timeout(200)
    check(f"{tag} 교과 목록 고치기", await pg.evaluate("window.__DB.config.subjects.e.join(',')") == "초등교과전반,체육,영양" and await pg.evaluate("subjList('초등학교').includes('영양')"))
    check(f"{tag} 활동 실적 칸", await pg.locator(".kpi").count() == 6 and await pg.locator(".kpi", has_text="써 봤어요").locator("b").inner_text() == "1건")
    await pg.get_by_role("button", name="실적 복사").click(); await pg.wait_for_timeout(200)
    st = await pg.evaluate("navigator.clipboard.readText()")
    check(f"{tag} 활동 실적 복사", st.startswith("[JACE 활동 실적]") and "도구 아이디어: 2건 (완성 1" in st and "모임: 1회, 참석 연인원 1명" in st, st[:300])
    await pg.get_by_role("button", name="이달 소식 카드").click(); await pg.wait_for_timeout(1200)
    sz = await pg.evaluate("(() => { const i = document.querySelector('#newsPrev img'); return i ? [i.naturalWidth, i.naturalHeight] : null; })()")
    check(f"{tag} 이달 소식 카드 그림", sz == [1080, 1500], str(sz))
    await pg.evaluate("closeM()")
    check(f"{tag} 대표 오류 없음", not errs, "; ".join(errs))
    db2 = await pg.evaluate("window.__DB"); await pg.close()
    # 총무가 된 회원은 운영진 관리 가능
    pg, errs = await newpage(b, width, {"uid": "m1", "email": "m1@x.kr"}, db=db2)
    check(f"{tag} 총무: 운영진 메뉴", await pg.locator("#navAdmin").is_visible())
    await pg.evaluate("location.hash='#admin'"); await pg.wait_for_timeout(500)
    check(f"{tag} 총무: 명단 열림", await pg.locator("table.adm tr").count() == 5)
    check(f"{tag} 총무 오류 없음", not errs, "; ".join(errs)); await pg.close()


async def demo(b, width):
    tag = "휴대폰" if width < 500 else "PC"
    pg, errs = await newpage(b, width, {"uid": "m1", "email": "m1@x.kr"}, db=json.loads(json.dumps(DB0)), hash="?demo")
    check(f"{tag} 미리보기: 안내 줄", "미리보기" in await pg.inner_text("#setupBar") and "로그인 확인" not in await pg.inner_text("#hright"))
    await pg.evaluate("go('public');render()"); await pg.wait_for_timeout(200)
    check(f"{tag} 미리보기: 지어낸 자료 5개", await pg.locator(".card.app").count() == 5 and "3개 학교 사용" in await pg.locator(".card.app", has_text="모둠 차례 타이머").inner_text())
    await pg.evaluate("location.hash='#ideas'"); await pg.wait_for_timeout(200)
    check(f"{tag} 미리보기: 아이디어 3개", await pg.locator(".idea").count() == 3)
    await pg.evaluate("go('public');render()"); await pg.wait_for_timeout(150)
    check(f"{tag} 미리보기: 이달의 추천 도구와 판 번호", "줄넘기" in await pg.inner_text(".mz-side .mz-rec") and await pg.locator(".card.app .mz-ver").count() >= 2 and await pg.locator(".card.app .mz-why").count() >= 2)
    await pg.evaluate("location.hash='#ideas'"); await pg.wait_for_timeout(150)
    await pg.locator("nav .hlp-btn").click(); await pg.wait_for_timeout(100)
    check(f"{tag} 미리보기 안에서는 미리보기 링크 숨김", await pg.locator(".hlp a.btn").count() == 0)
    await pg.evaluate("closeM();login()"); await pg.wait_for_timeout(100)
    check(f"{tag} 미리보기: 로그인 막음", "둘러보기만" in await pg.inner_text("#toast"))
    check(f"{tag} 미리보기 오류 없음", not errs, "; ".join(errs)); await pg.close()


async def no_server(b):
    pg, errs = await newpage(b, 1280, {"uid": "m1", "email": "m1@x.kr"}, db=json.loads(json.dumps(DB0)), api=False)
    check("서버 없을 때: 준비 중 안내", await pg.locator("#setupBar").is_visible())
    check("서버 없을 때: 소개 화면", await pg.locator(".ahero").count() == 1)
    await pg.evaluate("go('members');msub='cal';render()"); await pg.wait_for_timeout(150)
    check("서버 없을 때: 회원 공간 안내", await pg.locator("main", has_text="서버를 설치하면").count() == 1)
    check("서버 없을 때 오류 없음", not errs, "; ".join(errs)); await pg.close()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w in (1280, 390):
            await guest(b, w); await join_flow(b, w); await member(b, w); await rep_admin(b, w); await demo(b, w)
        await no_server(b)
        await b.close()
    TMP.unlink(missing_ok=True)
    bad = [r for r in RESULTS if not r[1]]
    for n, ok, info in RESULTS:
        if not ok: print("실패 " + n + (" :: " + info if info else ""))
    print(f"화면 시험 {len(RESULTS) - len(bad)}/{len(RESULTS)} 통과"); print("FAIL" if bad else "OK"); sys.exit(1 if bad else 0)
asyncio.run(main())
