from langgraph.types import Command

APPROVALS = {"yes", "y", "ok"}


async def handle_message(
    agent, thread_id: str, text: str, pending: int
) -> tuple[str, int]:
    config = {"configurable": {"thread_id": thread_id}}

    if pending:
        if text.strip().lower() in APPROVALS:
            decisions = [{"type": "approve"} for _ in range(pending)]
        else:
            decisions = [
                {"type": "reject", "message": f"User declined: {text}"}
                for _ in range(pending)
            ]
        result = await agent.ainvoke(
            Command(resume={"decisions": decisions}), config=config
        )
    else:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": text}]}, config=config
        )

    if interrupts := result.get("__interrupt__"):
        action_requests = interrupts[0].value["action_requests"]
        question = "\n".join(action["description"] for action in action_requests)
        return f"{question}\n\n(yes/no)", len(action_requests)

    return result["messages"][-1].content, 0
