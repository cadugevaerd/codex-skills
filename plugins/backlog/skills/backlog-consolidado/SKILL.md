---
name: backlog-consolidado
description: Solicita exportação consolidated canônica.
argument-hint: "--db PATH [--code CODE]"
user-invocable: true
disable-model-invocation: false
---
# Consolidated

Execute `backlogctl [--json] export consolidated --db PATH [--code CODE]`. O resultado canônico é `data.backlogs:[{code,name,profile,archived,bound_path,items:[...]}]`, sem lista top-level `data.items`. Export não muta SQLite.