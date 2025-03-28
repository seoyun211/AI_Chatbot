from fastapi import FastAPI, UploadFile, Form # fastapi = api쓰겟따 uploadfile 파일을 받기위해 form html로 부터 질문을 받기위해
from fastapi.responses import JSONResponse # 응답을 json 형식으로 반환하기 위해
import openai # api라이브러리 
import shutil # 파일 저장 복사
from panda import run_pandas_code # panda라는 파일에서 pandas를 실행 시키겠다 panda는 임시 이름 

app = FastAPI()
openai.api_key = "key 넣기"

# 1. 사용자에게 파일을 받는 부분 파일을 받아서 uploaded_data.csv에 wb로 복사
 
@app.post("/analyze")  # analyza라는 주소로 post요청이 오면 함수를 실행시키겠다는 뜻
async def analyze(file: UploadFile, question: str = Form(...)):  # async 비동기 함수 속도 빠르게 하기 위해 
    file_path = "uploaded_data.csv"
    with open(file_path, "wb") as f: # w(쓰기)b(바이너리) (0과1로 저장 (excel과 csv파일은 바이너리가 적합)) with as 파일 자동 열고 닫기
        shutil.copyfileobj(file.file, f) # 받은 파일을 f에 저장 f는 file_path 

    model = "gpt-4"

# 2. gpt 프롬포트 설정 및 사용자에게 질문을 받고 pandas로 코드 시각화화
# system = gpt 프롬포트 user = 사용자 질문 assistant = 답변 
    gpt_response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 pandas로 데이터 분석을 해야해."},
            {"role": "system", "content": "한국어로 말해."},
            {"role": "user", "content": f"{question} 에 맞는 pandas 코드를 작성해줘. 'df'라는 변수에 데이터가 들어 있다고 가정해."} #사용자 질문을 받음 그리고 프레임워크가 df 이름으로 하라고 지정
        ]
    )
    code = gpt_response['choices'][0]['message']['content'] # gpt응답에서 코드만 추출하는 부분 api에서는 리스트 형식으로 답변한다는데 뭔말인지는 아직 잘 모르겠네

    result, image_path = run_pandas_code(file_path, code) #file_path와 code로 pandas 분석 하고 result와 image로 받음

# 3. 결과 요약 요청
    gpt_summary = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 데이터 분석 결과를 사용자에게 설명해줘."},
            {"role": "user", "content": f"이 결과를 쉽게 요약해줘:\n{result}"}
        ]
    )
    summary = gpt_summary['choices'][0]['message']['content'] # gpt응답에서 자연어만 추출 이것도 리스트 기반 
# 4. json으로 반환
    return JSONResponse(content={
        "summary": summary,   # 이건 gpt 답변 자연어 부분 이걸 답변창에 띄우고
        "image_url": f"/static/{image_path}" if image_path else "",     # 이건 이미지 이것도 맞는 구역에 
        "code": code       # 이건 gpt가 생성한 코드 보여줘도 괜찮고 안보여줘도 괜찮을듯듯 
    })
