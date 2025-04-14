# ✅ api.py - FastAPI 진입점 (라우터 정의 및 서비스 호출)
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gpt_service import analyze_file, ask_chatbot, analyze_boj_info
from backjoon import get_user_info, recommend_problem, get_ai_problem_recommendation, get_distribution

app = FastAPI()

# 🌐 CORS 설정 - 프론트엔드와 통신 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📁 정적 파일 (예: 이미지) 서빙 경로 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 📊 CSV 파일 기반 분석 요청 (POST)
@app.post("/analyze")
async def analyze(file: UploadFile, question: str = Form(...)):
    result = analyze_file(file, question)
    if "error" in result:
        return JSONResponse(content={"summary": result["error"]}, status_code=500)
    return JSONResponse(content=result)

# 💬 일반 챗봇 질문 응답
@app.post("/chat")
async def chat(question: str = Form(...)):
    try:
        answer = ask_chatbot(question)
        return JSONResponse(content={"answer": answer})
    except Exception as e:
        return JSONResponse(content={"answer": f"⚠ 오류 발생: {e}"}, status_code=500)

# 👤 사용자 정보 조회 API
@app.get("/userinfo")
async def userinfo(boj_username: str):
    user = await get_user_info(boj_username)
    if not user:
        return JSONResponse(content={"error": "사용자를 찾을 수 없습니다."}, status_code=404)
    return JSONResponse(content={
        "tier": user["tier"],
        "rank": user["rank"],
        "solved_count": user["solvedCount"],
        "class": user["class"],
        "max_streak": user["maxStreak"],
        "rating": user["rating"]
    })

# 🎯 티어 기반 랜덤 문제 추천
@app.get("/recommend")
async def recommend(boj_username: str):
    rec = await recommend_problem(boj_username)
    if not rec:
        return JSONResponse(content={"error": "추천할 문제가 없습니다."}, status_code=404)
    return JSONResponse(content=rec)

# 🧠 태그 기반 AI 문제 추천
@app.get("/recommend_ai")
async def recommend_ai(boj_username: str):
    try:
        results = get_ai_problem_recommendation(boj_username)
        formatted = [
            {"problemId": p["problemId"], "title": p["titleKo"], "tier": p["level"]}
            for p in results
        ]
        return JSONResponse(content={"recommendations": formatted})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 📄 백준 정보 기반 GPT 분석 요청 (추가 기능용)
@app.post("/analyze_boj")
async def analyze_boj(question: str = Form(...)):
    try:
        summary = analyze_boj_info(question)
        return JSONResponse(content={"summary": summary})
    except Exception as e:
        return JSONResponse(content={"summary": f"분석 실패: {e}"}, status_code=500)

# 📊 난이도별 문제 풀이 분포 반환
@app.get("/distribution")
async def distribution(boj_username: str):
    data = await get_distribution(boj_username)
    if not data:
        return JSONResponse(content={"error": "분포 데이터를 가져올 수 없습니다."}, status_code=500)
    return JSONResponse(content=data)

# 📆 주간 활동 API (GraphQL 기반 버전용)
@app.get("/weekly_activity")
async def weekly_activity(boj_username: str):
    from backjoon import get_weekly_activity
    data = await get_weekly_activity(boj_username)
    if not data:
        return JSONResponse(content={"error": "주간 데이터를 가져올 수 없습니다."}, status_code=500)
    return JSONResponse(content=data)  # ✅ 여기 수정됨!

# 🎯 도전 과제 생성 API
@app.get("/challenge")
async def generate_challenge(boj_username: str):
    try:
        from backjoon import generate_challenge_for_user
        challenge = await generate_challenge_for_user(boj_username)
        return JSONResponse(content={"challenge": challenge})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 📈 등급 업 전략 안내 API
@app.get("/rankup_tip")
async def rankup_tip(boj_username: str):
    try:
        from backjoon import generate_rankup_tip
        tip = await generate_rankup_tip(boj_username)
        return JSONResponse(content={"tip": tip})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
