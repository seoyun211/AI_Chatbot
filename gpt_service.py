# ✅ gpt_service.py - GPT 관련 기능 모듈 (파일 분석 + 백준 분석 둘 다 지원)
from openai import OpenAI, APITimeoutError
from analy import run_pandas_code

client = OpenAI(api_key="")  # OpenAI API 키 필요

# 💬 단순 GPT 챗봇 응답 함수
def ask_chatbot(question: str) -> str:
    model = "gpt-4"
    gpt_response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "친절하고 유용한 챗봇이야. 한국어로 대화해."},
            {"role": "user", "content": question}
        ]
    )
    return gpt_response.choices[0].message.content

# 📊 업로드된 파일을 기반으로 GPT 분석 수행
def analyze_file(file, question: str):
    import shutil
    file_path = "uploaded_data.csv"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    model = "gpt-3.5-turbo"

    try:
        # GPT에게 pandas 분석 코드 생성 요청
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

        # GPT에게 분석 요약 설명 요청
        gpt_summary = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "데이터 분석 결과를 설명해줘."},
                {"role": "user", "content": f"분석 결과:\n{result}"}
            ],
            timeout=20
        )
        summary = gpt_summary.choices[0].message.content

        return {"summary": summary, "image_url": f"/static/{image_path}" if image_path else "", "code": code}

    except APITimeoutError:
        return {"error": "⏱ GPT 응답 시간이 초과되었습니다."}

    except Exception as e:
        return {"error": f"❗ 분석 도중 오류 발생: {str(e)}"}

# 📊 백준 API 정보 기반 분석 요청 → GPT 분석 요약 반환 (파일 업로드 없이 사용)
def analyze_boj_info(prompt: str) -> str:
    model = "gpt-3.5-turbo"
    gpt_response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 알고리즘 실력을 분석해주는 데이터 분석가입니다."},
            {"role": "user", "content": prompt}
        ],
        timeout=20
    )
    return gpt_response.choices[0].message.content