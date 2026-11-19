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
DB0 = {"members": {
  "m1": {"name": "가교사", "school": "달빛중학교", "level": "중학교", "pos": "교사", "subject": "체육", "phone": "010-1111-2222", "others": "없음", "status": "승인", "role": "회원", "email": "m1@x.kr", "t": 1},
  "w1": {"name": "나교사", "school": "별초등학교", "level": "초등학교", "pos": "교감", "subject": "초등교과전반", "phone": "010-3333-4444", "others": "2개 이상", "status": "대기", "email": "w1@x.kr", "t": 2},
  "bs": {"name": "박회장", "school": "봄초등학교", "level": "초등학교", "pos": "교사", "subject": "초등교과전반", "phone": "010-5555-6666", "others": "없음", "status": "승인", "email": "boss@x.kr", "t": 0}}}


def build(user, db=None, api=True):
    stub = f"""<script>
window.JACE_FIREBASE={{apiKey:"k",authDomain:"a",databaseURL:"",projectId:"p",appId:"x"}};
window.JACE_API_URL={json.dumps("https://api.invalid/exec" if api else "")};window.JACE_ADMINS=["jace.edulab@gmail.com"];window.JACE_MANAGERS=["boss@x.kr"];
window.__CALLS=[];window.__DB={json.dumps(db or {}, ensure_ascii=False)};
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
    pg, errs = await newpage(b, width, None)
    check(f"{tag} 첫 화면은 JACE 소개", await pg.locator(".ahero").count() == 1 and await pg.locator(".atabs button").count() == 5)
    for k, txt in [("topic", "교과별 실천 연구"), ("tools", "기록하고 쌓는 도구"), ("plan", "월 1회 모임"), ("join", "창립 회원")]:
        await pg.evaluate(f"pickA('{k}')"); await pg.wait_for_timeout(80)
        check(f"{tag} 소개 하위 탭 {k}", await pg.locator("main", has_text=txt).count() == 1)
    await pg.evaluate("go('public');render()"); await pg.wait_for_timeout(200)
    check(f"{tag} 자료실 카드 4개", await pg.locator(".card.app").count() == 4)
    check(f"{tag} 썸네일 있는 카드와 색 카드", await pg.locator(".card.app .thumb.ph").count() == 3 and await pg.locator(".card.app .thumb:not(.ph)").count() == 1)
    check(f"{tag} 프로그램 카드에 바로 열기", await pg.locator(".card.app", has_text="점퍼스").locator(".openbtn", has_text="바로 열기").count() == 1)
    check(f"{tag} 회원만 자료는 바로 열기 없음", await pg.locator(".card.app", has_text="티니클링").locator(".openbtn").count() == 0)
    await pg.locator("aside").get_by_role("button", name="프로그램", exact=True).click(); await pg.wait_for_timeout(150)
    check(f"{tag} 자료 종류 고르기", await pg.locator(".card.app").count() == 1)
    await pg.click(".freset"); await pg.wait_for_timeout(150)
    await pg.locator("aside").get_by_role("button", name="중학교", exact=True).click(); await pg.wait_for_timeout(150)
    check(f"{tag} 학교급 고르기", await pg.locator(".card.app").count() == 1)
    await pg.click(".freset"); await pg.wait_for_timeout(150)
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
    await pg.evaluate("closeM();location.hash='#guide'"); await pg.wait_for_timeout(250)
    check(f"{tag} 사용 안내", await pg.locator(".guide .panel").count() >= 5)
    await pg.evaluate("location.hash='#members'"); await pg.wait_for_timeout(200)
    check(f"{tag} 회원 공간은 잠김", await pg.locator(".gate").count() == 1)
    w = await pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    check(f"{tag} 가로 넘침 없음", w)
    check(f"{tag} 손님 오류 없음", not errs, "; ".join(errs)); await pg.close()


async def join_flow(b, width):
    tag = "휴대폰" if width < 500 else "PC"
    pg, errs = await newpage(b, width, None, db=json.loads(json.dumps(DB0)))
    await pg.locator("#hright").get_by_role("button", name="가입 신청").click(); await pg.wait_for_timeout(300)
    check(f"{tag} 가입: 로그인 뒤 신청서", await pg.locator("#jn").count() == 1 and await pg.input_value("#jn") == "새교사")
    await pg.locator("#jp").press_sequentially("010-1234 5678")
    check(f"{tag} 가입: 휴대전화 숫자만", await pg.input_value("#jp") == "01012345678")
    await pg.fill("#js", "햇살초등학교"); await pg.select_option("#jl", "초등학교"); await pg.select_option("#jpos", "교사")
    await pg.fill("#jsub", "초등교과전반"); await pg.select_option("#jo", "1개"); await pg.check("#jelig"); await pg.check("#jpriv")
    await pg.get_by_role("button", name="신청서 보내기").click()
    check(f"{tag} 가입: 명단 동의 없으면 막힘", "명단 제출" in await pg.inner_text("#jerr"))
    await pg.check("#jreg"); await pg.get_by_role("button", name="신청서 보내기").click()
    check(f"{tag} 가입: 이용 약속 없으면 막힘", "약속" in await pg.inner_text("#jerr"))
    await pg.check("#jc"); await pg.get_by_role("button", name="신청서 보내기").click(); await pg.wait_for_timeout(300)
    sv = await pg.evaluate("window.__DB.members.new")
    check(f"{tag} 가입: 저장", sv and sv["status"] == "대기" and sv["phone"] == "010-1234-5678" and sv["book"] is True, json.dumps(sv, ensure_ascii=False))
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
    for k in ["chat", "cal", "notice", "book"]:
        await pg.evaluate(f"go('members');msub='{k}';msubPicked=true;render()"); await pg.wait_for_timeout(150)
        check(f"{tag} 회원 공간 '{k}' 탭", await pg.locator(".subtabs").count() == 1 and await pg.locator(".gate").count() == 0)
    check(f"{tag} 회원 공간 탭은 4개", await pg.locator(".subtabs button:not(.tabedit)").count() == 4)
    await pg.evaluate("go('members');msub='cal';render();openEv('s1')"); await pg.wait_for_timeout(150)
    check(f"{tag} 일정 창", await pg.locator("#ov", has_text="참석").count() >= 1)
    await pg.evaluate("closeM();go('members');msub='book';render()"); await pg.wait_for_timeout(150)
    check(f"{tag} 책자 탭 원고 양식", await pg.locator(".msguide a[href$='ms-template.hwpx']").count() == 1)
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
    await pg.fill("#ut", "새 자료"); await pg.locator("#ug .chip").first.click(); await pg.locator("#ua .chip").first.click()
    await pg.check("#c1"); await pg.check("#c2")
    await pg.evaluate("() => { sendUpload(); }"); await pg.wait_for_timeout(1500)
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
    check(f"{tag} 운영진: 명단 3줄", await pg.locator("table.adm tr").count() == 4)
    check(f"{tag} 운영진: 회장 맨 위", "박회장" in await pg.locator("table.adm tr >> nth=1").inner_text())
    check(f"{tag} 운영진: 3개 초과 경고", await pg.locator("td.warn").count() == 1)
    check(f"{tag} 운영진: 내려받기 기록", await pg.locator("main", has_text="점퍼스").count() >= 1)
    await pg.locator("table.adm tr", has_text="나교사").get_by_role("button", name="승인").click(); await pg.wait_for_timeout(200)
    check(f"{tag} 운영진: 승인 저장", await pg.evaluate("window.__DB.members.w1.status") == "승인")
    await pg.locator("table.adm tr", has_text="가교사").locator("select").select_option("총무"); await pg.wait_for_timeout(200)
    check(f"{tag} 운영진: 역할 저장", await pg.evaluate("window.__DB.members.m1.role") == "총무")
    await pg.context.grant_permissions(["clipboard-read", "clipboard-write"])
    await pg.get_by_role("button", name="명단 복사 (승인 회원)").click(); await pg.wait_for_timeout(200)
    clip = await pg.evaluate("navigator.clipboard.readText()")
    check(f"{tag} 운영진: 명단 복사", clip.splitlines()[0] == "순\t역할\t소속\t직위\t성명\t교과" and clip.splitlines()[1].startswith("1\t회장\t") and len(clip.splitlines()) == 4, clip)
    check(f"{tag} 대표 오류 없음", not errs, "; ".join(errs))
    db2 = await pg.evaluate("window.__DB"); await pg.close()
    # 총무가 된 회원은 운영진 관리 가능
    pg, errs = await newpage(b, width, {"uid": "m1", "email": "m1@x.kr"}, db=db2)
    check(f"{tag} 총무: 운영진 메뉴", await pg.locator("#navAdmin").is_visible())
    await pg.evaluate("location.hash='#admin'"); await pg.wait_for_timeout(500)
    check(f"{tag} 총무: 명단 열림", await pg.locator("table.adm tr").count() == 4)
    check(f"{tag} 총무 오류 없음", not errs, "; ".join(errs)); await pg.close()


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
            await guest(b, w); await join_flow(b, w); await member(b, w); await rep_admin(b, w)
        await no_server(b)
        await b.close()
    TMP.unlink(missing_ok=True)
    bad = [r for r in RESULTS if not r[1]]
    for n, ok, info in RESULTS:
        if not ok: print("실패 " + n + (" :: " + info if info else ""))
    print(f"화면 시험 {len(RESULTS) - len(bad)}/{len(RESULTS)} 통과"); print("FAIL" if bad else "OK"); sys.exit(1 if bad else 0)
asyncio.run(main())
