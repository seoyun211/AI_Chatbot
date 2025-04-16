# ✅ backjoon.py - 백준 관련 기능 모듈
import requests
import httpx
import random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import Counter

# ✅ 티어 번호 → 이름 변환
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

# ✅ 사용자 정보 가져오기
async def get_user_info(boj_username: str):
    url = f"https://solved.ac/api/v3/user/show?handle={boj_username}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
    if res.status_code != 200:
        return None
    return res.json()

# ✅ 티어 기반 랜덤 문제 추천
async def recommend_problem(boj_username: str):
    try:
        user_data = await get_user_info(boj_username)
        tier = user_data.get("tier", 1)
        tier_name = convert_tier_name(tier)
        query = f"tier:{max(1, tier-5)}..{min(70, tier+2)}"
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

# ✅ 전체 푼 문제 ID 가져오기 (페이지 루프)
def get_all_solved_problem_ids(user_id):
    solved_ids = set()
    page = 1
    while True:
        url = f"https://solved.ac/api/v3/user/solve_history?handle={user_id}&page={page}"
        res = requests.get(url)
        items = res.json().get("items", [])
        if not items:
            break
        for item in items:
            solved_ids.add(item['problemId'])
        page += 1
    return solved_ids

# ✅ 푼 문제 태그 통계 가져오기
def get_user_tag_distribution(user_id):
    url = f"https://solved.ac/api/v3/user/problem_stats?handle={user_id}"
    res = requests.get(url)
    stats = res.json()['items']
    tags = {}
    for item in stats:
        for tag in item['tags']:
            tags[tag['key']] = tags.get(tag['key'], 0) + item['count']
    return tags

# ✅ 안 푼 문제 중 선호 태그 기준 추천
def get_unsolved_problems_by_tag(preferred_tags, solved_problems):
    candidate_problems = []
    top_tags = sorted(preferred_tags.items(), key=lambda x: -x[1])[:5]  # 상위 5개 태그
    for tag, _ in top_tags:
        url = f"https://solved.ac/api/v3/search/problem?query=tag:{tag}&direction=asc"
        res = requests.get(url)
        problems = res.json().get("items", [])
        for p in problems:
            if p["problemId"] not in solved_problems:
                candidate_problems.append(p)
    return random.sample(candidate_problems, min(10, len(candidate_problems)))

# ✅ AI 문제 추천 (태그 기반 + 푼 문제 제외)
def get_ai_problem_recommendation(user_id):
    solved_problems = get_all_solved_problem_ids(user_id)
    preferred_tags = get_user_tag_distribution(user_id)
    return get_unsolved_problems_by_tag(preferred_tags, solved_problems)

# ✅ 난이도별 문제 해결 분포 (Lv.0 ~ Lv.30)
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

# ✅ 도전 과제 생성

async def get_problems_by_level(level: int, count: int = 5):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://solved.ac/api/v3/search/problem?query=level:{level}&sort=random"
        )
        if res.status_code != 200:
            return []

        data = res.json()
        problems = data.get("items", [])

        # titleKo가 있는 문제만 사용 (언어 필터)
        korean_problems = [p for p in problems if "titleKo" in p]

        random.shuffle(korean_problems)
        selected = korean_problems[:count]

        return [
            {
                "title": problem["titleKo"],
                "id": problem["problemId"],
                "url": f"https://www.acmicpc.net/problem/{problem['problemId']}"
            }
            for problem in selected
        ]


async def generate_challenge_for_user(boj_username: str):
    user = await get_user_info(boj_username)
    if not user:
        return "⚠ 사용자 정보를 불러올 수 없습니다."

    tier = user["tier"]
    tier_name = convert_tier_name(tier)
    next_tier = tier + 1 if tier + 1 < 31 else 30
    next_tier_name = convert_tier_name(next_tier)

    problems = await get_problems_by_level(next_tier, count=5)
    if not problems:
        return "⚠ 추천할 문제를 불러올 수 없습니다."

    # 카드 UI 형태의 HTML
    problem_cards = "".join([
        f"""
        <button onclick="window.open('{p['url']}', '_blank')"
                style="padding: 10px 14px; background-color: #ffffff;
                       border: 1px solid #ccc; border-radius: 8px;
                       text-align: left; margin-bottom: 8px;
                       cursor: pointer; width: 100%;">
            {i+1}. {p['title']}
        </button>
        """
        for i, p in enumerate(problems)
    ])

    html_message = f"""
    <div style="background-color: #f0f8ff; border-left: 6px solid #4682b4;
                padding: 16px; border-radius: 12px;
                font-family: 'Pretendard', sans-serif; max-width: 400px;">
        <h3 style="margin-top: 0;">🎯 현재 티어: <strong style="color: #2f4f4f;">{tier_name}</strong></h3>
        <p style="margin: 4px 0 16px;">🆙 다음 티어 <strong style="color: #4169e1;">({next_tier_name})</strong>를 향해 도전해보세요!</p>
        <div style="display: flex; flex-direction: column;">
            {problem_cards}
        </div>
    </div>
    """

    return html_message

# ✅ 등급 업 전략 안내
async def generate_rankup_tip(boj_username: str):
    user = await get_user_info(boj_username)
    if not user:
        return "사용자 정보를 불러올 수 없습니다."

    tier = user["tier"]
    tier_name = convert_tier_name(tier)

    if tier < 6:
        tip = "브론즈는 구현, 수학, 문자열 문제 위주로 빠르게 풀이하세요."
    elif tier < 11:
        tip = "실버는 정렬, 탐색(BFS/DFS), 그리디 알고리즘이 중요합니다."
    elif tier < 16:
        tip = "골드는 자료구조, DP, 그래프 알고리즘을 공부하세요."
    else:
        tip = "이제는 알고리즘 난이도와 시간 복잡도 최적화가 핵심입니다."

    return f"현재 티어: {tier_name} → {tip}"

# ✅ 주간 활동 (월~일별 푼 문제 수)
async def get_weekly_activity(boj_username: str):
    try:
        url = f"https://www.acmicpc.net/status?user_id={boj_username}&result_id=4"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.acmicpc.net/",
            "Connection": "keep-alive",
            "DNT": "1",
        }

        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select("table#status-table tbody tr")

        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        counter = Counter()

        for row in rows:
            td_list = row.find_all('td')
            if len(td_list) < 9:
                continue

            date_str = td_list[8].text.strip()  
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                if dt.date() >= monday.date():
                    weekday = dt.strftime("%a")
                    counter[weekday] += 1
            except:
                continue

        weekdays_en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekdays_kr = ['월', '화', '수', '목', '금', '토', '일']
        counts = [1,2,3,4,5,6,7]

        return {"days": weekdays_kr, "counts": counts}

    except Exception as e:
        print(f"❗ 주간 분석 실패: {e}")
        return None
