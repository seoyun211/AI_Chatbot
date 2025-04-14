# ✅ backjoon.py - 백준 관련 기능 모듈
import requests
import httpx
import random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import Counter

# 특수 수자 티어 번호를 판정하여 티어 이름으로 변환
# solved.ac의 티어 수자가 1~30이며 이름은 다음 순서의 번역을 가지고 있음
# 번역을 복사하여 키 수준으로 바이로 출력

def convert_tier_name(tier: int) -> str:
    tiers = [
        "Unrated", "Bronze V", "Bronze IV", "Bronze III", "Bronze II", "Bronze I",
        "Silver V", "Silver IV", "Silver III", "Silver II", "Silver I",
        "Gold V", "Gold IV", "Gold III", "Gold II", "Gold I",
        "Platinum V", "Platinum IV", "Platinum III", "Platinum II", "Platinum I",
        "Diamond V", "Diamond IV", "Diamond III", "Diamond II", "Diamond I",
        "Ruby V", "Ruby IV", "Ruby III", "Ruby II", "Ruby I",
        "Master", "Grandmaster", "Challenger"
    ]
    return tiers[tier] if 0 <= tier < len(tiers) else "Unknown"

# 백준 사용자 정보 조회 (solved.ac)
async def get_user_info(boj_username: str):
    url = f"https://solved.ac/api/v3/user/show?handle={boj_username}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
    if res.status_code != 200:
        return None
    return res.json()

# 사용자 티어 기본으로 드롭은 매크로 문제 발생할 때 참고 (solved.ac random search)
async def recommend_problem(boj_username: str):
    try:
        user_data = await get_user_info(boj_username)
        tier = user_data.get("tier", 1)
        tier_name = convert_tier_name(tier)

        url = f"https://solved.ac/api/v3/search/problem?query=tier:{tier}&sort=random"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            problem_data = res.json()

        if not problem_data["items"]:
            return None

        p = problem_data["items"][0]
        return {
            "problemId": p["problemId"],
            "title": p["titleKo"],
            "tier": p["level"],
            "tierName": tier_name
        }
    except:
        return None

# 사용자가 해결한 문제의 태그 비율 가져오기
def get_user_solved_problems(user_id):
    url = f"https://solved.ac/api/v3/user/problem_stats?handle={user_id}"
    res = requests.get(url)
    stats = res.json()['items']
    tags = {}
    for item in stats:
        for tag in item['tags']:
            tags[tag['key']] = tags.get(tag['key'], 0) + item['count']
    return tags

# 선호 태그에 까지된 범위에서 사용자가 해결하지 않은 문제 가져오기
def get_unsolved_problems_by_tag(preferred_tags, solved_problems):
    candidate_problems = []
    for tag, _ in sorted(preferred_tags.items(), key=lambda x: -x[1])[:3]:
        url = f"https://solved.ac/api/v3/search/problem?query=tag:{tag}&direction=asc"
        res = requests.get(url)
        problems = res.json().get("items", [])
        for p in problems:
            if p["problemId"] not in solved_problems:
                candidate_problems.append(p)
    return random.sample(candidate_problems, min(5, len(candidate_problems)))

# AI 문제 추천 통합 방식
def get_ai_problem_recommendation(user_id):
    url = f"https://solved.ac/api/v3/user/solve_history?handle={user_id}&page=1"
    res = requests.get(url)
    solved_problems = [item['problemId'] for item in res.json().get("items", [])]
    preferred_tags = get_user_solved_problems(user_id)
    return get_unsolved_problems_by_tag(preferred_tags, solved_problems)

# 난이도별 문제 해결 분포 (Lv.0~Lv.30)
async def get_distribution(boj_username: str):
    url = f"https://solved.ac/api/v3/user/problem_stats?handle={boj_username}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)

    if res.status_code != 200:
        return None

    try:
        stats = res.json()
    except:
        return None

    level_counts = [0] * 31
    for item in stats:
        level = item.get("level")
        solved = item.get("solved", 0)
        if level is not None and 0 <= level <= 30:
            level_counts[level] = solved

    levels = [f"Lv.{i}" for i in range(31)]
    return {"levels": levels, "counts": level_counts}




# 주간 해결 행정은 해제됨
# async def get_weekly_activity(boj_username: str):
#     try:
#         url = f"https://www.acmicpc.net/status?user_id={boj_username}&result_id=4"
#         headers = {
#             "User-Agent": (
#                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 (KHTML, like Gecko) "
#                 "Chrome/120.0.0.0 Safari/537.36"
#             ),
#             "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
#             "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
#             "Referer": "https://www.acmicpc.net/",
#             "Connection": "keep-alive",
#             "DNT": "1",
#             "Cookie": "onlinejudge=bfn0a65g7tev2q2n1urt5kqktu; bojautologin=be1aeee46d164beee311977970f09e23c4523abc"
#         }

#         async with httpx.AsyncClient(headers=headers) as client:
#             response = await client.get(url)
#             print("📱 상태 코드:", response.status_code)
#             print("📄 HTML 일반:", response.text[:300])
#             response.raise_for_status()

#         soup = BeautifulSoup(response.text, 'html.parser')
#         rows = soup.select("table#status-table tbody tr")
#         print("🔍 제주 행 개수:", len(rows))

#         today = datetime.now()
#         monday = today - timedelta(days=today.weekday())
#         counter = Counter()

#         for row in rows:
#             td_list = row.find_all('td')
#             if len(td_list) < 9:
#                 continue

#             date_str = td_list[8].text.strip()
#             try:
#                 dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
#                 if dt.date() >= monday.date():
#                     weekday = dt.strftime("%a")
#                     counter[weekday] += 1
#             except Exception as ex:
#                 print("⚠️ 날짜 파싱 실패:", date_str, ex)
#                 continue

#         weekdays_en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
#         weekdays_kr = ['월', '화', '수', '목', '금', '토', '일']
#         counts = [counter.get(day, 0) for day in weekdays_en]

#         result = {"days": weekdays_kr, "counts": counts}
#         print("✅ 차지 결과:", result)
#         return result

#     except Exception as e:
#         print(f"❗ 주간 분석 실패: {e}")
#         return None