"""화면 시험 (기능 수정 때).  python3 tests/smoke.py
가짜 파이어베이스를 끼워 넣고 크롬으로 손님 화면, 가입 신청, 고치기, 운영진 회원 관리를 PC와 휴대폰 크기로 밟아 본다.
실제 구글 로그인과 실제 데이터베이스 규칙은 확인하지 못한다.
"""
import asyncio, json, re, sys, pathlib
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "index.html").read_text(encoding="utf-8")
TMP = ROOT / "tests" / "_smoke.html"

def build(user, configured=True, db=None):
    cfg = '{apiKey:"k",authDomain:"a",databaseURL:"d",projectId:"p",appId:"x"}' if configured else '{apiKey:""}'
    stub = f"""<script>
window.JACE_FIREBASE={cfg};window.JACE_ADMINS=["admin@x.kr"];window.JACE_MANAGERS=["boss@x.kr"];
window.__DB={json.dumps(db or {}, ensure_ascii=False)};window.__W=[];
let __U={json.dumps(user)};let __cb=null;
const __A={{onAuthStateChanged(cb){{__cb=cb;setTimeout(()=>cb(__U),20)}},signInWithPopup(){{__U={{uid:"new",email:"new@x.kr",displayName:"새교사"}};setTimeout(()=>__cb(__U),10);return Promise.resolve()}},signOut(){{__U=null;setTimeout(()=>__cb(null),10);return Promise.resolve()}}}};
function __get(p){{return p.split("/").reduce((o,k)=>o==null?undefined:o[k],window.__DB)}}
function __set(p,v){{const ks=p.split("/");let o=window.__DB;ks.slice(0,-1).forEach(k=>{{o[k]=o[k]||{{}};o=o[k]}});o[ks[ks.length-1]]=v;window.__W.push([p,v])}}
window.firebase={{initializeApp(){{}},auth:Object.assign(()=>__A,{{GoogleAuthProvider:function(){{}}}}),database:()=>({{ref:p=>({{get:async()=>({{val:()=>{{const v=__get(p);return v===undefined?null:JSON.parse(JSON.stringify(v))}}}}),set:async v=>__set(p,JSON.parse(JSON.stringify(v)))}})}})}};
</script>"""
    s = re.sub(r'<script src="https://www\.gstatic\.com[^"]*"></script>\n', "", SRC).replace('<script src="config.js"></script>', stub)
    s = s.replace('family=Montserrat', 'family=None')
    TMP.write_text(s, encoding="utf-8"); return TMP.as_uri()

R = []
def check(n, ok, info=""): R.append((n, bool(ok), info))

async def run(b, vp, tag):
    async def page(user, configured=True, db=None):
        pg = await b.new_page(viewport=vp); pg.set_default_timeout(4000); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, body=""))
        await pg.goto(build(user, configured, db)); await pg.wait_for_timeout(250)
        return pg, errs
    # 1 설정 전
    pg, errs = await page(None, configured=False)
    check(f"{tag} 설정 전: 준비 중 표시", await pg.locator("#joinActs").inner_text() == "가입 신청 준비 중")
    check(f"{tag} 설정 전: 오류 없음", not errs, "; ".join(errs)); await pg.close()
    # 2 손님 → 로그인 → 신청
    pg, errs = await page(None)
    await pg.locator("#joinActs button", has_text="가입 신청").click()
    check(f"{tag} 손님: 로그인 안내 창", await pg.locator("#mbox", has_text="구글 계정으로 먼저 로그인").count() == 1)
    await pg.get_by_role("button", name="구글 계정으로 로그인").click(); await pg.wait_for_timeout(250)
    check(f"{tag} 로그인 뒤 신청서가 바로 열림", await pg.locator("#jn").count() == 1)
    check(f"{tag} 이름 칸에 구글 이름", await pg.locator("#jn").input_value() == "새교사")
    await pg.get_by_role("button", name="신청서 보내기").click()
    check(f"{tag} 빈칸이면 안내", "휴대전화" in await pg.locator("#jerr").inner_text())
    await pg.locator("#jp").press_sequentially("010-1234 5678")
    check(f"{tag} 휴대전화: 숫자만 남음", await pg.locator("#jp").input_value() == "01012345678")
    await pg.fill("#js", "햇살초등학교")
    await pg.select_option("#jl", "초등학교"); await pg.select_option("#jpos", "교사")
    await pg.fill("#jsub", "초등교과전반"); await pg.select_option("#jo", "1개")
    await pg.check("#jelig"); await pg.check("#jpriv")
    await pg.get_by_role("button", name="신청서 보내기").click()
    check(f"{tag} 명단 동의 없으면 막힘", "명단 제출" in await pg.locator("#jerr").inner_text())
    await pg.check("#jreg"); await pg.get_by_role("button", name="신청서 보내기").click(); await pg.wait_for_timeout(150)
    saved = await pg.evaluate("window.__DB.members && window.__DB.members.new")
    check(f"{tag} 신청 저장", bool(saved) and saved["status"] == "대기" and saved["phone"] == "010-1234-5678" and saved["email"] == "new@x.kr", json.dumps(saved, ensure_ascii=False))
    check(f"{tag} 승인 대기 표시", "승인 대기 중" in await pg.locator("#hright").inner_text() and "접수" in await pg.locator("#joinState").inner_text())
    check(f"{tag} 일반 회원에게 회원 관리 없음", await pg.get_by_role("button", name="회원 관리").count() == 0)
    await pg.get_by_role("button", name="신청 내용 고치기").click()
    check(f"{tag} 고치기: 저장한 값이 채워짐", await pg.locator("#js").input_value() == "햇살초등학교" and await pg.locator("#jp").input_value() == "01012345678" and await pg.locator("#jreg").is_checked())
    await pg.fill("#jsub", "체육"); await pg.get_by_role("button", name="고친 내용 보내기").click(); await pg.wait_for_timeout(150)
    s2 = await pg.evaluate("window.__DB.members.new")
    check(f"{tag} 고치기 저장(신청일 유지)", s2["subject"] == "체육" and s2["t"] == saved["t"])
    await pg.get_by_role("button", name="로그아웃").click(); await pg.wait_for_timeout(150)
    check(f"{tag} 로그아웃", "로그인" in await pg.locator("#hright").inner_text())
    check(f"{tag} 가입 흐름 오류 없음", not errs, "; ".join(errs)); await pg.close()
    # 3 승인된 회원
    db = {"members": {"m1": {"name": "가교사", "school": "달빛중학교", "level": "중학교", "pos": "교사", "subject": "체육", "phone": "010-1111-2222", "others": "없음", "status": "승인", "t": 1}}}
    pg, errs = await page({"uid": "m1", "email": "m1@x.kr"}, db=db)
    check(f"{tag} 승인 회원: 회원 표시", "가교사 선생님" in await pg.locator("#hright").inner_text() and "등록되었습니다" in await pg.locator("#joinState").inner_text())
    check(f"{tag} 승인 회원: 고치기 단추 없음", await pg.get_by_role("button", name="신청 내용 고치기").count() == 0); await pg.close()
    # 4 운영진
    db["members"]["w1"] = {"name": "나교사", "school": "별초등학교", "level": "초등학교", "pos": "교감", "subject": "초등교과전반", "phone": "010-3333-4444", "others": "2개 이상", "status": "대기", "t": 2}
    db["members"]["ad"] = {"name": "전북AI융합교육연구회", "school": "-", "phone": "010-0000-0000", "email": "admin@x.kr", "status": "대기", "t": 3}
    pg, errs = await page({"uid": "ad", "email": "Admin@x.kr"}, db=db)
    check(f"{tag} 대표 계정: 운영진 표시", "대표 계정" in await pg.locator("#hright").inner_text())
    check(f"{tag} 대표 계정: 가입 신청 단추 없음", await pg.get_by_role("button", name="가입 신청서 쓰기").count() == 0 and await pg.get_by_role("button", name="가입 신청").count() == 0)
    await pg.locator("#hright").get_by_role("button", name="회원 관리").click(); await pg.wait_for_timeout(150)
    check(f"{tag} 운영진: 명단 2줄", await pg.locator("table.adm tr").count() == 3)
    check(f"{tag} 운영진: 인원 집계", "회원 1명" in await pg.locator(".adm-top").inner_text() and "9명" in await pg.locator(".adm-top").inner_text())
    check(f"{tag} 운영진: 3개 초과 경고", await pg.locator("td.warn").count() == 1)
    await pg.locator("table.adm tr", has_text="나교사").get_by_role("button", name="승인").click(); await pg.wait_for_timeout(150)
    check(f"{tag} 운영진: 승인 저장", await pg.evaluate("window.__DB.members.w1.status") == "승인" and "회원 2명" in await pg.locator(".adm-top").inner_text())
    await pg.context.grant_permissions(["clipboard-read", "clipboard-write"])
    await pg.get_by_role("button", name="명단 복사 (승인 회원)").click(); await pg.wait_for_timeout(150)
    clip = await pg.evaluate("navigator.clipboard.readText()")
    check(f"{tag} 운영진: 명단 복사", clip.splitlines()[0] == "순\t역할\t소속\t직위\t성명\t교과" and len(clip.splitlines()) == 3 and "나교사" in clip, clip)
    check(f"{tag} 운영진 흐름 오류 없음", not errs, "; ".join(errs)); await pg.close()
    # 4-2 회장(회원 + 관리)
    pg, errs = await page({"uid": "bs", "email": "boss@x.kr", "displayName": "회장님"}, db=json.loads(json.dumps(db)))
    check(f"{tag} 회장: 가입 전엔 신청서 단추와 회원 관리 둘 다", await pg.get_by_role("button", name="가입 신청서 쓰기").count() == 1 and await pg.locator("#joinActs").get_by_role("button", name="회원 관리").count() == 1)
    await pg.get_by_role("button", name="가입 신청서 쓰기").click()
    await pg.fill("#jp", "01055556666"); await pg.fill("#js", "봄초등학교"); await pg.select_option("#jl", "초등학교"); await pg.select_option("#jpos", "교사")
    await pg.fill("#jsub", "초등교과전반"); await pg.select_option("#jo", "없음"); await pg.check("#jelig"); await pg.check("#jpriv"); await pg.check("#jreg")
    await pg.get_by_role("button", name="신청서 보내기").click(); await pg.wait_for_timeout(150)
    check(f"{tag} 회장: 신청하면 바로 승인", await pg.evaluate("window.__DB.members.bs.status") == "승인")
    check(f"{tag} 회장: 내 정보 고치기 가능", await pg.get_by_role("button", name="내 정보 고치기").count() == 1)
    await pg.locator("#hright").get_by_role("button", name="회원 관리").click(); await pg.wait_for_timeout(150)
    await pg.context.grant_permissions(["clipboard-read", "clipboard-write"])
    await pg.get_by_role("button", name="명단 복사 (승인 회원)").click(); await pg.wait_for_timeout(150)
    clip = await pg.evaluate("navigator.clipboard.readText()")
    check(f"{tag} 회장: 명단 맨 위에 회장", clip.splitlines()[1].startswith("1\t회장\t봄초등학교"), clip)
    check(f"{tag} 회장 흐름 오류 없음", not errs, "; ".join(errs)); await pg.close()
    # 5 기존 화면
    pg, errs = await page(None)
    for sec in ["about", "topic", "tracks", "plan", "join"]:
        check(f"{tag} 기존 구역 #{sec} 있음", await pg.locator("#" + sec).count() == 1)
    w = await pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    check(f"{tag} 가로 넘침 없음", w); await pg.close()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await run(b, {"width": 1280, "height": 900}, "PC")
        await run(b, {"width": 390, "height": 844}, "폰")
        await b.close()
    TMP.unlink(missing_ok=True)
    bad = [r for r in R if not r[1]]
    for n, ok, info in R:
        if not ok: print("실패 " + n + (" :: " + info if info else ""))
    print(f"화면 시험 {len(R) - len(bad)}/{len(R)} 통과"); print("FAIL" if bad else "OK"); sys.exit(1 if bad else 0)
asyncio.run(main())
