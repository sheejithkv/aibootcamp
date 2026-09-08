import json

from shared.agent import run_agent
from shared.llm_client import call_llm
from shared.task_store import get_task, update_task


_PLANNER_SYSTEM_PROMPT = """You are a task planner. Break the user's request
into a sequence of 2 to 5 concrete, actionable steps that an AI agent can
execute one by one.

Each step should:
- Be a standalone instruction
- Be specific enough to execute
- Preserve important inputs such as cluster names, alerts, and severity
- Build on previous results where needed

Return ONLY a JSON object in this exact format:
{"steps": ["Step 1", "Step 2"]}
"""


_SYNTHESIZER_SYSTEM_PROMPT = """You are a helpful OpenShift and Kubernetes
SRE assistant. You have completed a multi-step task.

Write a clear, concise final response that:
- Directly answers the original request
- Includes the important information from all completed actions
- Does not invent information
- Does not mention the internal planning process
"""


async def make_plan(message: str) -> list[str]:
    messages = [
        {"role": "system", "content": _PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    try:
        response = await call_llm(
            messages=messages,
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        raw = response.content or "{}"
        parsed = json.loads(raw)

        if isinstance(parsed, dict):
            for key in ("steps", "plan", "tasks"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
            else:
                return [message]

        if not isinstance(parsed, list):
            return [message]

        steps = [
            str(step).strip()
            for step in parsed[:5]
            if str(step).strip()
        ]

        return steps or [message]

    except Exception:
        return [message]


async def execute_plan(task_id: str) -> None:
    try:
        task = get_task(task_id)

        if task is None:
            return

        update_task(
            task_id,
            status="executing",
            steps_completed=[],
        )

        steps_completed = []
        plan = task.plan or []

        for i, step in enumerate(plan):
            step_result = await run_agent(
                message=step,
                session_id=task.session_id,
                tenant_id=task.tenant_id,
            )

            step_record = {
                "step_index": i,
                "step": step,
                "result": step_result.get("result", ""),
                "tools_used": step_result.get("tools_used", []),
            }

            steps_completed.append(step_record)

            update_task(
                task_id,
                steps_completed=list(steps_completed),
            )

        step_summary = "\n".join(
            f"Step {record['step_index'] + 1} "
            f"({record['step']}): {record['result']}"
            for record in steps_completed
        )

        synth_response = await call_llm(
            messages=[
                {
                    "role": "system",
                    "content": _SYNTHESIZER_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Original request: {task.message}\n\n"
                        f"Step results:\n{step_summary}"
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=800,
        )

        final_result = synth_response.content or step_summary

        update_task(
            task_id,
            status="done",
            result=final_result,
        )

    except Exception as exc:
        update_task(
            task_id,
            status="error",
            error=str(exc),
        )
