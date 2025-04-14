# ✅ backjoon.py - 백준 관련 기능 모듈
import requests
import httpx
import random

# 🔢 숫자 티어 값을 티어 이름 문자열로 변환
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

# 👤 사용자 정보 조회 API 호출 (비동기)
async def get_user_info(boj_username: str):
    url = f"https://solved.ac/api/v3/user/show?handle={boj_username}"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
    if res.status_code != 200:
        return None
    return res.json()

# 🎲 티어 기반 랜덤 문제 추천 (비동기)
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

# ✅ 사용자 문제 태그 통계 가져오기
def get_user_solved_problems(user_id):
    url = f"https://solved.ac/api/v3/user/problem_stats?handle={user_id}"
    res = requests.get(url)
    stats = res.json()['items']
    tags = {}
    for item in stats:
        for tag in item['tags']:
            tags[tag['key']] = tags.get(tag['key'], 0) + item['count']
    return tags  # {"greedy": 5, "dp": 10, ...}

# ✅ 특정 태그 기반으로 아직 안 푼 문제 가져오기
def get_unsolved_problems_by_tag(preferred_tags, solved_problems):
    candidate_problems = []
    for tag, _ in sorted(preferred_tags.items(), key=lambda x: -x[1])[:3]:  # 가장 많이 푼 태그 3개
        url = f"https://solved.ac/api/v3/search/problem?query=tag:{tag}&direction=asc"
        res = requests.get(url)
        problems = res.json().get("items", [])
        for p in problems:
            if p["problemId"] not in solved_problems:
                candidate_problems.append(p)
    return random.sample(candidate_problems, min(5, len(candidate_problems)))  # 최대 5개 추천

# 🧠 AI 문제 추천 핵심 로직
def get_ai_problem_recommendation(user_id):
    # 사용자가 푼 문제 목록 조회
    url = f"https://solved.ac/api/v3/user/solve_history?handle={user_id}&page=1"
    res = requests.get(url)
    solved_problems = [item['problemId'] for item in res.json().get("items", [])]

    # 선호 태그 기반으로 아직 안 푼 문제 추천
    preferred_tags = get_user_solved_problems(user_id)
    return get_unsolved_problems_by_tag(preferred_tags, solved_problems)

# 📊 난이도별 문제 풀이 분포 조회 API
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

    level_counts = [0] * 31  # Lv.0 ~ Lv.30
    for item in stats:
        level = item.get("level")
        solved = item.get("solved", 0)
        if level is not None and 0 <= level <= 30:
            level_counts[level] = solved

    levels = [f"Lv.{i}" for i in range(31)]
    return {"levels": levels, "counts": level_counts}
