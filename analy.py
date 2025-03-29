import pandas as pd # pandas 라이브러리 
import matplotlib.pyplot as plt # 그래프 그림

# 1. gpt 코드 실행
def run_pandas_code(file_path: str, code: str): # gpt가 만들 코드 실행

        
        df = pd.read_csv(file_path) # file을 df라는곳에 저장

        local_vars = {"df": df} # gpt가 df를 시용하므로 df를 지역 변수로 설정
        exec(code, {}, local_vars) # # exec를 사용하여 외부 코드 실행

# 2. 결과
        result = local_vars.get("result", df.head().to_string())  # result 키가 있으면 가져오고 없으면 기본값 사용 df의 상위행 반환 to.string 데이터를 문자로 바꿈                                                                   

# 3. 시각화 저장
        image_path = "" # 경로 초기화
        figs = [plt.figure(n) for n in plt.get_fignums()] # 열려있는 figure 번호 반환 그리고 해당 번호 fiugure 객체 가져옴
        if figs: # 만약 그래프가 존재한다면
            image_path = "result_plot.png"
            figs[-1].savefig(f"static/{image_path}") # 가장 최근에 만들어진 figure
            plt.close('all') # 모든 그래프 닫기기

        return result, image_path # 결과반환
