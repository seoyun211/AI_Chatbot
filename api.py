from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI, APITimeoutError
from matplotlib import pyplot as plt
from io import BytesIO
import base64
import shutil
from analy import run_pandas_code
import httpx
import requests
import random

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# OpenAI API 키 설정 (API 키 설정 필수)
client = OpenAI(api_key="")

@app.post("/analyze")
async def analyze(file: UploadFile, question: str = Form(...)):
    file_path = "uploaded_data.csv"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    model = "gpt-3.5-turbo"

    try:
        gpt_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "다음 지침을 무조건 따라야 합니다:"},
                {"role": "system", "content": "1. 오직 pandas로 작성된 Python 코드만 반환하세요."},
                {"role": "system", "content": "2. 절대 자연어 메시지, 설명, 요청, 거절 메시지를 포함하지 마세요."},
                {"role": "system", "content": "3. 파일을 직접 읽거나 쓰는 코드도 금지입니다. 데이터는 반드시 제공된 'df' DataFrame만 사용합니다."},
                {"role": "system", "content": "4. 최종 분석 결과는 반드시 'result'라는 변수에 저장합니다."},
                {"role": "system", "content": "5. 분석 요청이 불명확하면 무조건 'result = df.head()' 코드를 반환하세요."},
                {"role": "user", "content": question}
            ],
            timeout=20
        )
        code = gpt_response.choices[0].message.content
        result, image_path = run_pandas_code(file_path, code)

        gpt_summary = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "데이터 분석 결과를 설명해줘."},
                {"role": "user", "content": f"분석 결과:\n{result}"}
            ],
            timeout=20
        )

        summary = gpt_summary.choices[0].message.content

        return JSONResponse(content={
            "summary": summary,
            "image_url": f"/static/{image_path}" if image_path else "",
            "code": code
        })

    except APITimeoutError:
        return JSONResponse(content={"summary": "⏱ GPT 응답 시간이 초과되었습니다."}, status_code=504)

    except Exception as e:
        return JSONResponse(content={"summary": f"❗ 분석 도중 오류 발생: {str(e)}"}, status_code=500)


@app.post("/chat")
async def chat(question: str = Form(...)):
    model = "gpt-4"
    gpt_response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "친절하고 유용한 챗봇이야. 한국어로 대화해."},
            {"role": "user", "content": question}
        ]
    )
    answer = gpt_response.choices[0].message.content
    return JSONResponse(content={"answer": answer})


@app.get("/userinfo")
async def get_user_info(boj_username: str):
    url = f"https://solved.ac/api/v3/user/show?handle={boj_username}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        return JSONResponse(content={"error": "사용자를 찾을 수 없습니다."}, status_code=404)

    data = response.json()
    result = {
        "tier": data.get("tier"),
        "rank": data.get("rank"),
        "solved_count": data.get("solvedCount"),  
        "class": data.get("class"),
        "max_streak": data.get("maxStreak"),       
        "rating": data.get("rating")
    }

    return JSONResponse(content=result)


# ✅ recommend 엔드포인트 중복 제거된 최종 코드
@app.get("/recommend")
async def recommend_problem(boj_username: str):
    try:
        user_info_url = f"https://solved.ac/api/v3/user/show?handle={boj_username}"
        async with httpx.AsyncClient() as client:
            user_res = await client.get(user_info_url)
            user_data = user_res.json()

        tier = user_data.get("tier", 1)

        problem_url = f"https://solved.ac/api/v3/search/problem?query=tier:{tier}&sort=random"
        async with httpx.AsyncClient() as client:
            problem_res = await client.get(problem_url)
            problem_data = problem_res.json()

        problem = problem_data["items"][0] if problem_data["items"] else None
        if problem is None:
            return JSONResponse({"error": "추천할 문제가 없습니다."}, status_code=404)

        recommended_problem = {
            "problemId": problem["problemId"],
            "title": problem["titleKo"],
            "tier": problem["level"]
        }

        return JSONResponse(recommended_problem)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
def get_user_solved_problems(user_id):
    url = f"https://solved.ac/api/v3/user/problem_stats?handle={user_id}"
    res = requests.get(url)
    if res.status_code != 200:
        raise Exception("solved.ac 유저 데이터를 가져올 수 없습니다.")
    stats = res.json()['items']
    tags = {}
    for item in stats:
        for tag in item['tags']:
            key = tag['key']
            tags[key] = tags.get(key, 0) + item['count']
    return tags  # 태그별 풀었던 문제 수

def get_unsolved_problems_by_tag(preferred_tags, solved_problems):
    # 태그 기반 문제 검색 (예: 브루트포스, 그리디 등)
    candidate_problems = []
    for tag, _ in sorted(preferred_tags.items(), key=lambda x: -x[1])[:3]:  # 가장 많이 푼 3개 태그 기반
        url = f"https://solved.ac/api/v3/search/problem?query=tag:{tag}&direction=asc"
        res = requests.get(url)
        if res.status_code != 200:
            continue
        problems = res.json().get("items", [])
        for p in problems:
            if p["problemId"] not in solved_problems:
                candidate_problems.append(p)
    return random.sample(candidate_problems, min(5, len(candidate_problems)))  # 최대 5개 추천

def get_ai_problem_recommendation(user_id):
    # 사용자가 푼 문제 가져오기
    solved_url = f"https://solved.ac/api/v3/user/solve_history?handle={user_id}&page=1"
    res = requests.get(solved_url)
    if res.status_code != 200:
        return {"error": "사용자 풀이 기록을 불러올 수 없습니다."}

    solved_problems = [item['problemId'] for item in res.json().get("items", [])]
    preferred_tags = get_user_solved_problems(user_id)

    recommendations = get_unsolved_problems_by_tag(preferred_tags, solved_problems)
    return recommendations

#ai문제추천
@app.get("/recommend_ai")
async def recommend_ai_problem(boj_username: str):
    try:
        recommendations = get_ai_problem_recommendation(boj_username)
        if not recommendations:
            return JSONResponse(content={"error": "추천할 문제가 없습니다."}, status_code=404)

        formatted = [
            {
                "problemId": p["problemId"],
                "title": p["titleKo"],
                "tier": p["level"]
            } for p in recommendations
        ]
        return JSONResponse(content={"recommendations": formatted})
    
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
#풀이분포보기
@app.get("/distribution")
async def get_solved_distribution(boj_username: str):
    url = f"https://solved.ac/api/v3/user/problem_stats?handle={boj_username}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)

    if res.status_code != 200:
        return JSONResponse(content={"error": "사용자 데이터를 가져올 수 없습니다."}, status_code=404)

    try:
        stats = res.json()
    except Exception as e:
        return JSONResponse(content={"error": f"데이터 파싱 중 오류 발생: {e}"}, status_code=500)

    level_counts = [0] * 31  # Lv.0 ~ Lv.30
    for item in stats:
        level = item.get("level")
        count = item.get("count", 0)
        if level is not None and 0 <= level <= 30:
            level_counts[level] += count

    levels = [f"Lv.{i}" for i in range(31)]
    return JSONResponse(content={"levels": levels, "counts": level_counts})
