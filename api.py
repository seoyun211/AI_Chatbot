from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI, APITimeoutError
import shutil
from analy import run_pandas_code
import httpx

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
        "handle": data["handle"],
        "tier": data["tier"],
        "rating": data.get("rating", 0),
        "rank": data.get("rank", "알 수 없음"),
        "solvedCount": data.get("solvedCount", 0),
        "class": data.get("class", 0),
        "maxStreak": data.get("maxStreak", 0)
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
