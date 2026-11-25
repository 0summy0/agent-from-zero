import json
import re


CHAPTER_ID = "4.1-multi-agent"
DEFAULT_REQUEST = "请说明多智能体协作。要点：角色分工、独立检查。"
MAX_ROUNDS = 2

# Fixed local knowledge keeps the teaching path deterministic and offline.
POINT_DETAILS = {
    "角色分工": "Writer 负责起草，Orchestrator 负责调度与汇总",
    "独立检查": "Critic 对照用户要点审查草稿，而不是只做文字润色",
    "终止条件": "要点全部满足或达到两轮检查上限时停止",
    "代价": "额外角色通常会增加延迟、成本和错误传播机会",
}


def _validate_request(request):
    if not isinstance(request, str):
        raise TypeError("request must be a string")
    if not request.strip():
        raise ValueError("request must not be empty")


def _resolve_required_points(request, required_points=None):
    _validate_request(request)
    if required_points is None:
        if "要点：" not in request:
            raise ValueError("request must contain '要点：' or provide required_points")
        raw_text = request.split("要点：", 1)[1]
        raw_text = re.split(r"[。.!?\n]", raw_text, maxsplit=1)[0]
        raw_points = re.split(r"[、,，;；]", raw_text)
    else:
        if not isinstance(required_points, (list, tuple)):
            raise TypeError("required_points must be a list or tuple")
        raw_points = required_points

    points = []
    for point in raw_points:
        if not isinstance(point, str):
            raise TypeError("each required point must be a string")
        point = point.strip()
        if not point:
            continue
        if point not in points:
            points.append(point)
    if not points:
        raise ValueError("required_points must not be empty")
    return points


class Writer:
    """Draft one supported point, then add at most one missing point per revision."""

    def write(self, request, required_points, critique=None, draft=None):
        points = _resolve_required_points(request, required_points)
        if critique is None:
            supported = [point for point in points if point in POINT_DETAILS]
            if not supported:
                return "暂时没有可用的本地要点。"
            point = supported[0]
            return f"{point}：{POINT_DETAILS[point]}。"

        if not isinstance(draft, str):
            raise ValueError("draft is required for a revision")
        missing = critique.get("missing_points", [])
        supported_missing = [point for point in missing if point in POINT_DETAILS]
        if not supported_missing:
            return draft
        point = supported_missing[0]
        return f"{draft}{point}：{POINT_DETAILS[point]}。"


class Critic:
    """Check required-point coverage with a deterministic substring rule."""

    def review(self, draft, required_points):
        points = _resolve_required_points("Critic review", required_points)
        missing = [point for point in points if point not in draft]
        feedback = (
            "要点齐全，可以终止。"
            if not missing
            else "请补充以下要点：" + "、".join(missing) + "。"
        )
        return {
            "satisfied": not missing,
            "missing_points": missing,
            "feedback": feedback,
        }


class Orchestrator:
    """Run at most two checks, allowing one revision between them."""

    def __init__(self, writer=None, critic=None):
        self.writer = writer if writer is not None else Writer()
        self.critic = critic if critic is not None else Critic()

    def run(self, request=DEFAULT_REQUEST, required_points=None):
        points = _resolve_required_points(request, required_points)
        initial_draft = self.writer.write(request, points)
        draft = initial_draft
        critique = None

        for rounds in range(1, MAX_ROUNDS + 1):
            critique = self.critic.review(draft, points)
            if critique["satisfied"]:
                break
            if rounds == MAX_ROUNDS:
                break
            draft = self.writer.write(request, points, critique, draft)

        return {
            "draft": initial_draft,
            "critique": critique,
            "final": draft,
            "rounds": rounds,
        }


def run_minimal_path(request=DEFAULT_REQUEST, required_points=None):
    """Return a JSON-serializable Writer/Critic/Orchestrator result."""
    return Orchestrator().run(request, required_points)


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
