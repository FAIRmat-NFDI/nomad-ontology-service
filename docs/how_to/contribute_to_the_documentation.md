# Contribute to the documentation

This site is built with `mkdocs` + `mkdocs-material`. To preview changes locally:

```sh
uv pip install -e '.[dev]'
mkdocs serve
```

The docs dependencies are part of the `dev` extra. If port 8000 is already taken (e.g. by a running NOMAD), use `mkdocs serve --dev-addr 127.0.0.1:8001`.

Pages follow the [Diátaxis](https://diataxis.fr/) structure already set up in the nav (`mkdocs.yml`): Tutorial (learning-oriented, one worked walkthrough), How-to guides (task-oriented, assumes some familiarity), Explanation (background and design rationale), Reference (dry, structured facts -- config fields, endpoints). When adding a new doc, put it in the section matching its purpose rather than everything piling into How-to.
