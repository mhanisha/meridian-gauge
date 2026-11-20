# Coding agent: test on the 10 easiest xarray tasks

**Status: 2 of 10 tasks run, 2 solved. The other 8 are waiting on the model host's daily
allowance and will be added here when they run.**

## What was tested

- **Tasks:** the 10 xarray tasks that the most models solved in the earlier evaluation
  (solved by 5, 4 or 3 of 5 models, then the 2 highest partial scores among those solved by 2).
- **Model:** `inclusionai/ling-3.2-flash:free` through OpenRouter, at no cost.
- **Limits per task:** 50 steps and 60 minutes. Time spent waiting on rate limits did not
  count towards the 60 minutes for tasks run after that change.
- **Sandbox:** one locked-down container per task (no network, 4 GB, 2 CPUs, non-root), with
  Python 3.13, numpy 2.3, pandas 2.3, dask, scipy and bottleneck.
- **Task text:** the commit's release note. For the three commits without one, it was a
  short description taken from the commit message.
- **Grading:** the test files are reset to the starting commit, then the commit's new tests
  are added. A task is **solved** only if every hidden test passes and no test that passed
  before the change now fails.

Before the model runs, each task's hidden tests were checked twice: all of them fail on the
starting code, and all of them pass with the real change. The hidden-test counts match the
earlier evaluation, except `98cfee5613`. It has 6 here instead of 4, because two dask
variants of one test now run as well.

## Results

| Task | What it asks for | Hidden tests | Result | Steps | Minutes | Tokens |
| --- | --- | --- | --- | --- | --- | --- |
| `b3f5db3728` | Keep lazy data lazy when a Variable is copied | 1/1 | **Solved** | 33 | 4.7 | 518,257 |
| `7e4b43b55d` | `sortby(ascending=False)` should put NaN last | 2/2 | **Solved** | 39 | 37.4 * | 563,556 |
| `ac29443644` | `.str` padding and splitting methods on object-dtype strings | 10 | not run yet | | | |
| `219292f5c8` | `diff` with a large `n`, and correct labels | 2 | not run yet | | | |
| `7cd0f184dc` | `interp` keeps float32 data as float32 | 3 | not run yet | | | |
| `98cfee5613` | `mean` on datetime and timedelta data | 6 | not run yet | | | |
| `6fa6881441` | `str.replace` / `str.contains` with `case=False, regex=False` | 4 | not run yet | | | |
| `d9ef1f0f02` | `assert_equal(check_dim_order=False)` on Datasets | 2 | not run yet | | | |
| `2f6713f568` | Dask rolling reductions declare the right dtype | 25 | not run yet | | | |
| `04c85cc919` | `interp` stops sorting coordinates that are already ordered | 6 | not run yet | | | |

\* Most of the 37 minutes was spent waiting out 82 rate-limit replies from the host. This
task ran before waiting stopped counting towards the time limit.

Neither solved task broke an existing test.

### What the model did

- **`b3f5db3728`:** a one-line fix in `Variable._replace` (`self.data` → `self._data`). It is
  the same line and the same change as the real commit. The real commit also made the same
  kind of change in a few other places that the hidden test does not check.
- **`7e4b43b55d`:** reversed only the non-NaN positions in `Dataset.sortby` when
  `ascending=False`, so NaN stays at the end. It also added a release note.

## What the run changed in the agent

- **Rate limits are waited out.** On a 429, a 5xx, a timeout or a dropped connection, the
  agent waits 5, 10, 20, 40, then 60 seconds (or what the host's `Retry-After` asks) and tries
  again. It gives up after `max_retry_wait_seconds` per model call (default 300). In this run
  that happened 98 times on the first two tasks, and both still finished.
- **Waiting does not use up the model's time.** The 60-minute limit counts only the model's own
  working time.
- **A used-up daily allowance stops the attempt at once.** OpenRouter's `free-models-per-day`
  only resets the next day, so waiting a few minutes cannot help. The first run kept retrying
  it and recorded five tasks as failed that the model never worked on. Those five are left
  out above.

## Why 8 tasks have not run

Without credits, OpenRouter allows about 50 free-model requests a day, and each task here
takes 35 to 40 model calls. Adding about $10 of credit raises the allowance to 1,000 requests
a day while the free models stay free. That is enough to run all 10 tasks in one go.

## Also noticed

- `read` keeps only the last 10,000 characters of a file, which hides most of a large file such
  as `variable.py`. The model worked around it with `grep` and `sed`, but showing the start of
  the file with line numbers would help weaker models.
- The sandbox has no `git`, and the model tried to use it.
