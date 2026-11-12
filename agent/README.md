# Coding agent (guide step 3)

**Owner:** Neetu.

The only part that is an AI agent, and the thing being measured. A model gets `task.md`
and five tools (`run`, `read`, `write`, `replace`, `finish`), works inside the sandbox,
and stops when it calls `finish` or hits a step, time or cost limit.

It must be identical for every model: same prompt, same tools, same limits.

Done when:
- [ ] a free model solves `b3f5db3728` through this loop and the grader confirms it
- [ ] each limit (steps, time, cost) ends the attempt with the right reason
- [ ] a broken tool call returns an error to the model instead of crashing
