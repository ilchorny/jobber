# Sample: Alex Park

A fully fictional candidate used to demonstrate jobber and to back the test suite. None of the people, companies, products, or publications are real.

Use this folder to try jobber without touching your own data:

```bash
JOBBER_HOME=/tmp/jobber-alex jobber init --library examples/sample/library
JOBBER_HOME=/tmp/jobber-alex jobber apply examples/sample/sample_jd.md
ls /tmp/jobber-alex/applications/
```

`JOBBER_HOME` redirects jobber's local data dir away from your real `~/.jobber/` so the demo is self-contained.
