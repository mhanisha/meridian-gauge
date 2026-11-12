# Model gateway (guide step 2)

**Owner:** Neetu.

The one way every part talks to a model. Hosts that speak the OpenAI-compatible format
(vLLM, RunPod, OpenRouter, Groq, Hugging Face) are switched in `config.yaml`, not in code.
Logs tokens, cost, time and the model that actually answered, and refuses a reply from
the wrong model.

Done when:
- [ ] two different hosts work by changing only the model name
- [ ] every call logs tokens, cost and the model that answered
- [ ] a deliberately wrong model name is caught
