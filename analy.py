import pandas as pd
import matplotlib.pyplot as plt

def run_pandas_code(file_path: str, code: str):
    """
    사용자가 업로드한 CSV 파일을 기반으로 GPT가 생성한 pandas 코드 실행 및 시각화 이미지 저장.
    오류가 발생할 경우 에러 메시지를 문자열로 반환.
    """
    try:
        # 파일 읽기
        df = pd.read_csv(file_path)
        local_vars = {"df": df}

        # 코드 실행
        try:
            exec(code, {}, local_vars)
        except Exception as e:
            return f"❗ 코드 실행 중 오류 발생: {e}", ""

        # 결과 추출
        result = local_vars.get("result", df.head().to_string())

        # 시각화 이미지 저장
        image_path = ""
        figs = [plt.figure(n) for n in plt.get_fignums()]
        if figs:
            image_path = "result_plot.png"
            try:
                figs[-1].savefig(f"static/{image_path}")
                plt.close('all')
            except Exception as e:
                return f"❗ 그래프 저장 중 오류 발생: {e}", ""

        return result, image_path

    except Exception as e:
        return f"❗ 전체 실행 중 예상치 못한 오류 발생: {e}", ""