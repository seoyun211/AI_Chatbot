from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI, APITimeoutError
import shutil
from analy import run_pandas_code
import time
import httpx  # 비동기 HTTP 요청을 위한 라이브러리

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

# OpenAI API 키 설정
client = OpenAI(api_key="")

@app.post("/analyze")
async def analyze(file: UploadFile, question: str = Form(...)):
    file_path = "uploaded_data.csv"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    model = "gpt-3.5-turbo"

    try:
        print("🔍 GPT 코드 생성 요청 시작")
        gpt_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "다음 지침을 무조건 따라야 합니다:"},
                {"role": "system", "content": "1. 오직 pandas로 작성된 Python 코드만 반환하세요."},
                {"role": "system", "content": "2. 절대 자연어 메시지, 설명, 요청, 거절 메시지를 포함하지 마세요."},
                {"role": "system", "content": "3. 파일을 직접 읽거나 쓰는 코드도 금지입니다. 데이터는 반드시 제공된 'df' DataFrame만 사용합니다."},
                {"role": "system", "content": "4. 최종 분석 결과는 반드시 'result'라는 변수에 저장합니다."},
                {"role": "system", "content": "5. 분석 요청이 불명확하면 무조건 'result = df.head()' 코드를 반환하세요. 절대 자연어로 답변하지 마세요."},
                {"role": "user", "content": f"{question}"}
            ],
            timeout=20
        )
        code = gpt_response.choices[0].message.content
        print("✅ GPT 코드 생성 완료")
        print("📄 실행할 코드:\n", code)

        result, image_path = run_pandas_code(file_path, code)
        print("✅ 코드 실행 완료")

        gpt_summary = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "데이터 분석 결과를 설명해줘."},
                {"role": "user", "content": f"분석 결과:\n{result}"}
            ],
            timeout=20
        )
        
        summary = gpt_summary.choices[0].message.content
        print("✅ 요약 생성 완료")

        return JSONResponse(content={
            "summary": summary,
            "image_url": f"/static/{image_path}" if image_path else "",
            "code": code
        })

    except APITimeoutError:
        return JSONResponse(content={"summary": "⏱ GPT 응답 시간이 초과되었습니다. 다시 시도해주세요."}, status_code=504)

    except Exception as e:
        print("❌ 오류 발생:", e)
        return JSONResponse(content={"summary": f"❗ 분석 도중 오류가 발생했습니다: {str(e)}"}, status_code=500)


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


@app.post("/analyze-file")
async def analyze_file(file: UploadFile, question: str = Form(...)):
    file_path = f"./{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    uploaded_file = client.files.create(
        file=open(file_path, "rb"),
        purpose='assistants'
    )

    assistant = client.beta.assistants.create(
        name="Data Analysis Assistant",
        instructions="너는 업로드된 파일을 분석하고 사용자의 질문에 답해야 해.",
        model="gpt-4-turbo",
        tools=[{"type": "code_interpreter"}],
        file_ids=[uploaded_file.id]
    )

    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=question,
        file_ids=[uploaded_file.id]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        time.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    analysis_result = messages.data[0].content[0].text.value

    return JSONResponse(content={"analysis_result": analysis_result})

# 백준
@app.get("/userinfo")
async def get_user_info(boj_username: str):
    try:
        # solved.ac 사용자 정보 API 요청
        url = f"https://solved.ac/api/v3/user/show?handle={boj_username}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        # 잘못된 사용자일 경우 404 반환
        if response.status_code != 200:
            return JSONResponse(content={"error": "사용자를 찾을 수 없습니다."}, status_code=404)

        # 응답 데이터에서 필요한 항목 추출
        data = response.json()
        result = {
            "handle": data["handle"],          # 사용자 아이디
            "tier": data["tier"],              # 티어 (숫자 값, 티어 이름은 변환 필요)
            "rating": data.get("rating", 0),   # 평점 (있을 경우)
            "rank": data.get("rank", "알 수 없음"),  # 전역 랭킹
            "solvedCount": data.get("solvedCount", 0),  # 푼 문제 수
            "class": data.get("class", 0),     # 클래스 (solved.ac 기준)
            "maxStreak": data.get("maxStreak", 0)  # 최장 연속 풀이일
        }

        return JSONResponse(content=result)

    except Exception as e:
        # 예외 발생 시 에러 메시지 반환
        return JSONResponse(content={"error": str(e)}, status_code=500)

