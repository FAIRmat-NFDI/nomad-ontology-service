# Contribute to the documentation

This site is built with `mkdocs` + `mkdocs-material`. To preview changes locally:

```sh
uv pip install -r requirements_docs.txt
mkdocs serve
```

Pages follow the [Diátaxis](https://diataxis.fr/) structure already set up in the nav (`mkdocs.yml`): Tutorial (learning-oriented, one worked walkthrough), How-to guides (task-oriented, assumes some familiarity), Explanation (background and design rationale), Reference (dry, structured facts -- config fields, endpoints). When adding a new doc, put it in the section matching its purpose rather than everything piling into How-to.
