import json
import time
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.agents.router import route_query, ROUTE_REJECT
from app.services.retriever import query_document
from app.agents.router import answer_general_question


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0,
    )


# We use Gemini itself to judge answer quality.
# This is called "LLM-as-judge" — a standard evaluation technique in production RAG.
# The judge looks at the question, expected answer, and actual answer
# and scores it 0-2 with a reason.
JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert evaluator for a document question-answering system.
Your job is to compare an actual answer against an expected answer and score it.

Scoring rubric:
2 = Correct — the actual answer captures the key information from the expected answer
1 = Partial — the actual answer is related but misses important details
0 = Incorrect — the actual answer is wrong, hallucinated, or completely off-topic

Rules:
- Focus on factual correctness, not wording. Different phrasing is fine.
- A longer answer that contains the expected answer should score 2.
- An answer that says "I could not find" when the expected answer exists scores 0.
- For REJECTED questions: if the system correctly rejected, score 2. If it answered, score 0.

Respond with ONLY a JSON object in this exact format, nothing else:
{{"score": <0, 1, or 2>, "reason": "<one sentence explanation>"}}""",
        ),
        (
            "human",
            """Question: {question}
Expected answer: {expected_answer}
Actual answer: {actual_answer}

Score this response:""",
        ),
    ]
)


def judge_answer(question: str, expected: str, actual: str) -> dict:
    """
    Uses Gemini as a judge to score answer quality.
    Returns {"score": 0|1|2, "reason": "..."}
    """
    llm = get_llm()
    chain = JUDGE_PROMPT | llm

    response = chain.invoke(
        {"question": question, "expected_answer": expected, "actual_answer": actual}
    )

    try:
        # Strip any markdown code fences Gemini might add
        raw = (
            str(response.content)
            .strip()
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )
        return json.loads(raw)
    except Exception:
        return {"score": 0, "reason": f"Judge parsing failed: {response.content}"}


def run_evaluation(collection_name: str, test_file: Path | None = None) -> dict:
    """
    Runs the full evaluation suite against a collection.

    Args:
        collection_name: The Chroma collection to test against
        test_file: Path to the JSON test questions file

    Returns:
        Full evaluation report with per-question results and aggregate scores
    """
    if test_file is None:
        test_file = Path(__file__).parent / "test_questions.json"

    with open(test_file) as f:
        test_data = json.load(f)

    questions = test_data["questions"]
    results = []

    print(f"\n Running evaluation — {len(questions)} questions\n")

    for i, q in enumerate(questions):
        print(f"  [{i+1}/{len(questions)}] {q['question'][:60]}...")

        # ── Step 1: Route the question ────────────────────────────────────
        actual_route = route_query(q["question"])

        # ── Step 2: Get the system's answer ──────────────────────────────
        try:
            if actual_route == ROUTE_REJECT:
                actual_answer = "REJECTED"

            elif actual_route == "llm":
                actual_answer = answer_general_question(q["question"])

            else:  # rag
                result = query_document(
                    question=q["question"],
                    collection_name=collection_name,
                    chat_history=[],
                )
                actual_answer = result["answer"]

        except Exception as e:
            actual_answer = f"ERROR: {str(e)}"

        # ── Step 3: Judge the answer ──────────────────────────────────────
        judgment = judge_answer(q["question"], q["expected_answer"], actual_answer)

        # ── Step 4: Check routing accuracy ───────────────────────────────
        route_correct = actual_route == q.get("expected_route", actual_route)

        result = {
            "id": q["id"],
            "question": q["question"],
            "category": q.get("category", "unknown"),
            "expected_answer": q["expected_answer"],
            "actual_answer": actual_answer,
            "expected_route": q.get("expected_route"),
            "actual_route": actual_route,
            "route_correct": route_correct,
            "score": judgment["score"],
            "reason": judgment["reason"],
        }
        results.append(result)

        # Print live result
        score_icon = {2: "✅", 1: "⚠️ ", 0: "❌"}[judgment["score"]]
        route_icon = "✅" if route_correct else "❌"
        print(
            f"     Answer {score_icon} ({judgment['score']}/2) | Route {route_icon} | {judgment['reason']}"
        )

        # Small delay to avoid rate limiting between judge calls
        time.sleep(1)

    # ── Aggregate metrics ─────────────────────────────────────────────────
    total = len(results)
    total_score = sum(r["score"] for r in results)
    max_score = total * 2
    accuracy_pct = round((total_score / max_score) * 100, 1)

    perfect = sum(1 for r in results if r["score"] == 2)
    partial = sum(1 for r in results if r["score"] == 1)
    incorrect = sum(1 for r in results if r["score"] == 0)
    hallucinations = sum(
        1 for r in results if r["score"] == 0 and r["actual_route"] == "rag"
    )
    route_accuracy = round(
        sum(1 for r in results if r["route_correct"]) / total * 100, 1
    )

    # Per-category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "score": 0}
        categories[cat]["total"] += 1
        categories[cat]["score"] += r["score"]

    category_scores = {
        cat: round((v["score"] / (v["total"] * 2)) * 100, 1)
        for cat, v in categories.items()
    }

    summary = {
        "total_questions": total,
        "overall_accuracy": accuracy_pct,
        "route_accuracy": route_accuracy,
        "perfect_answers": perfect,
        "partial_answers": partial,
        "incorrect_answers": incorrect,
        "hallucinations_detected": hallucinations,
        "category_scores": category_scores,
        "results": results,
    }

    # Print summary
    print(f"\n{'─'*50}")
    print(f"  Overall accuracy:  {accuracy_pct}%")
    print(f"  Route accuracy:    {route_accuracy}%")
    print(f"  Perfect answers:   {perfect}/{total}")
    print(f"  Hallucinations:    {hallucinations}")
    print(f"  By category:       {category_scores}")
    print(f"{'─'*50}\n")

    return summary
