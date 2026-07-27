# Profiles e categories

No runtime `backlogctl` 2.0.0 atual, profiles/categories são catálogo fixo; `doctor`, `backlog list` e `backlog show` não expõem comando de descoberta de categories. Use exatamente:

- `general` → `general`, `work`, `personal`
- `software` → `feature`, `bug`, `chore`, `general`
- `operations` → `incident`, `maintenance`, `general`
- `business` → `sales`, `finance`, `general`
- `personal` → `health`, `finance`, `general`

A CLI valida profile/category antes da mutação. Não invente defaults e não prometa `profile list` ou `category list`.