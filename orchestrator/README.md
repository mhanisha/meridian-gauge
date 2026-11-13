# Orchestrator (guide step 4)

**Owner:** Keerthana.

One command that runs every task for every model, in order, and can resume. No AI in it.

```bash
python -m orchestrator config.yaml
```

Done when:
- [ ] one command runs `b3f5db3728` for one model and leaves every expected file
- [ ] stopping halfway and rerunning finishes the rest without redoing work
- [ ] no containers are left running afterwards (`docker ps` is empty)
